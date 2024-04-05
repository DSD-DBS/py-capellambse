# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Support for YAML-based declarative modelling.

A YAML-based approach to describing how to create and modify
``capellambse`` compatible models.

For an in-depth explanation, please refer to the :ref:`full
documentation about declarative modelling <declarative-modelling>`.
"""
from __future__ import annotations

__all__ = [
    "FindBy",
    "NewObject",
    "Promise",
    "UUIDReference",
    "UnfulfilledPromisesError",
    "YDMDumper",
    "YDMLoader",
    "apply",
    "dump",
    "load",
]

import collections
import collections.abc as cabc
import contextlib
import dataclasses
import operator
import os
import sys
import typing as t

import yaml

import capellambse
from capellambse import helpers
from capellambse.model import common
from capellambse.model import new_object as NewObject

FileOrPath = t.Union[t.IO[str], str, os.PathLike[t.Any]]
_FutureAction = dict[str, t.Any]
_OperatorResult = tuple[
    "Promise",
    t.Union[capellambse.ModelObject, _FutureAction],
]


def dump(instructions: cabc.Sequence[cabc.Mapping[str, t.Any]]) -> str:
    """Dump an instruction stream to YAML."""
    return yaml.dump(instructions, Dumper=YDMDumper)


def load(file: FileOrPath) -> list[dict[str, t.Any]]:
    """Load an instruction stream from a YAML file.

    Parameters
    ----------
    file
        An open file-like object, or a path or PathLike pointing to such
        a file. Files are expected to use UTF-8 encoding.
    """
    if hasattr(file, "read"):
        file = t.cast(t.IO[str], file)
        ctx: t.ContextManager[t.IO[str]] = contextlib.nullcontext(file)
    else:
        assert not isinstance(file, t.IO)
        ctx = open(file, encoding="utf-8")

    with ctx as opened_file:
        return yaml.load(opened_file, Loader=YDMLoader)


def apply(
    model: capellambse.MelodyModel, file: FileOrPath
) -> dict[Promise, capellambse.ModelObject]:
    """Apply a declarative modelling file to the given model.

    Parameters
    ----------
    model
        The model to apply the instructions to.
    file
        An open file-like object to read YAML instructions from, or a
        path to such a file. Files will be read with UTF-8 encoding.

        The full format of these files is documented in the
        :ref:`section about declarative modelling
        <declarative-modelling>`.

    Notes
    -----
    This function is not transactional: If an exception occurs during
    this function, the model will be left partially modified, with no
    reliable way to know how much of the YAML input has been consumed.
    It is therefore advised to reload or discard the model immediately
    in these cases, to avoid working with an inconsistent state.

    Even though the YAML layout suggests linear execution from top to
    bottom, the actual order in which modifications are executed is
    implementation defined. This is necessary to support promises with
    ``!promise``, but reorderings are still possible even if no promises
    are used in an input document.
    """
    instructions = collections.deque(load(file))
    promises = dict[Promise, capellambse.ModelObject]()
    deferred = collections.defaultdict[Promise, list[_FutureAction]](list)

    while instructions:
        instruction = instructions.popleft()

        parent = instruction.pop("parent")
        if isinstance(parent, (Promise, _ObjectFinder)):
            try:
                parent = _resolve(promises, model, parent)
            except _UnresolvablePromise as p:
                d = {"parent": parent, **instruction}
                deferred[p.args[0]].append(d)
                continue

        if not isinstance(parent, capellambse.model.GenericElement):
            raise TypeError(
                "Expected a model object as parent, found "
                f"{type(parent).__name__}"
            )

        for op_type, apply_op in _OPERATIONS.items():
            try:
                op = instruction.pop(op_type)
            except KeyError:
                continue
            for promise, outcome in apply_op(promises, parent, op):
                if isinstance(outcome, dict):
                    deferred[promise].append(outcome)
                else:
                    if promise in promises:
                        raise ValueError(
                            f"promise_id defined twice: {promise.identifier}"
                        )
                    promises[promise] = outcome
                    instructions.extend(deferred.pop(promise, ()))
        if instruction:
            keys = ", ".join(instruction)
            raise ValueError(f"Unrecognized keys in instruction: {keys}")
    if deferred:
        raise UnfulfilledPromisesError(frozenset(deferred))
    return promises


def _operate_create(
    promises: dict[Promise, capellambse.ModelObject],
    parent: capellambse.ModelObject,
    creations: dict[str, t.Any],
) -> cabc.Generator[_OperatorResult, t.Any, None]:
    yield from _operate_extend(promises, parent, creations)


def _operate_extend(
    promises: dict[Promise, capellambse.ModelObject],
    parent: capellambse.ModelObject,
    extensions: dict[str, t.Any],
) -> cabc.Generator[_OperatorResult, t.Any, None]:
    for attr, value in extensions.items():
        if not isinstance(value, cabc.Iterable):
            raise TypeError("values below `extend:*:` must be lists")

        yield from _create_complex_objects(promises, parent, attr, value)


def _operate_delete(
    promises: dict[Promise, capellambse.ModelObject],
    parent: capellambse.ModelObject,
    deletions: dict[str, t.Any],
) -> cabc.Iterable[_OperatorResult]:
    del promises

    for attr, objs in deletions.items():
        try:
            target = getattr(parent, attr)
        except AttributeError:
            raise TypeError(
                "Cannot delete object:"
                f" {type(parent).__name__} has no attribute {attr!r}"
            ) from None
        if not isinstance(target, common.ElementList) or not isinstance(
            objs, list
        ):
            delattr(parent, attr)
            continue
        if not isinstance(target, common.ElementListCouplingMixin):
            raise TypeError(
                "Cannot delete object:"
                f" {type(parent).__name__}.{attr} is not model-coupled"
            )
        for obj in objs:
            if isinstance(obj, Promise):
                raise ValueError("Cannot use !promise in `delete:*:`")
            if isinstance(obj, str):
                obj = UUIDReference(helpers.UUIDString(obj))
            obj = _resolve({}, parent, obj)
            try:
                idx = target.index(obj)
            except ValueError:
                if hasattr(parent, "_short_repr_"):
                    p_repr = parent._short_repr_()
                else:
                    p_repr = repr(getattr(parent, "uuid", "<unknown>"))
                raise ValueError(
                    f"No object {obj._short_repr_()} in {attr!r} of {p_repr}"
                ) from None
            del target[idx]

    return ()


def _operate_modify(
    promises: dict[Promise, capellambse.ModelObject],
    parent: capellambse.ModelObject,
    modifications: dict[str, t.Any],
) -> cabc.Generator[_OperatorResult, t.Any, None]:
    import warnings

    warnings.warn("The 'modify' key has been deprecated, use 'set' instead")
    yield from _operate_set(promises, parent, modifications)


def _operate_set(
    promises: dict[Promise, capellambse.ModelObject],
    parent: capellambse.ModelObject,
    modifications: dict[str, t.Any],
) -> cabc.Generator[_OperatorResult, t.Any, None]:
    for attr, value in modifications.items():
        if isinstance(value, (list, Promise, _ObjectFinder)):
            try:
                value = _resolve(promises, parent, value)
            except _UnresolvablePromise as p:
                yield p.args[0], {"parent": parent, "modify": {attr: value}}
                continue

        if isinstance(value, list):
            getattr(parent, attr).clear()
            yield from _create_complex_objects(promises, parent, attr, value)
        elif isinstance(value, dict):
            obj = getattr(parent, attr)
            for k, v in value.items():
                setattr(obj, k, v)
        else:
            setattr(parent, attr, value)


def _operate_sync(
    promises: dict[Promise, capellambse.ModelObject],
    parent: capellambse.ModelObject,
    modifications: dict[str, t.Any],
) -> cabc.Generator[_OperatorResult, t.Any, None]:
    for attr, value in modifications.items():
        if not isinstance(value, cabc.Iterable):
            raise TypeError("values below `extend:*:` must be lists")

        for obj in value:
            try:
                find_args = obj["find"]
            except KeyError:
                raise ValueError(
                    "Expected `find` key in sync object"
                ) from None

            try:
                candidate = _resolve_findby(parent, attr, FindBy(find_args))
            except _NoObjectFoundError:
                candidate = None

            if candidate is not None:
                if sync := obj.pop("sync", None):
                    yield from _operate_sync(promises, candidate, sync)
                if mods := obj.pop("set", None):
                    yield from _operate_set(promises, candidate, mods)
                if ext := obj.pop("extend", None):
                    yield from _operate_extend(promises, candidate, ext)
                promise: str | Promise | None = obj.get("promise_id")
                if promise is not None:
                    if isinstance(promise, str):
                        promise = Promise(promise)
                    yield (promise, candidate)
            else:
                newobj_props = (
                    find_args | obj.pop("set", {}) | obj.pop("extend", {})
                )
                if "promise_id" in obj:
                    newobj_props["promise_id"] = obj.pop("promise_id")
                yield from _create_complex_objects(
                    promises, parent, attr, [newobj_props]
                )
                yield from _operate_sync(promises, parent, {attr: [obj]})


def _resolve(
    promises: dict[Promise, capellambse.ModelObject],
    parent: capellambse.ModelObject | capellambse.MelodyModel,
    value: t.Any,
) -> t.Any:
    if isinstance(value, Promise):
        try:
            return promises[value]
        except KeyError:
            raise _UnresolvablePromise(value) from None
    elif isinstance(value, UUIDReference):
        return parent._model.by_uuid(value.uuid)
    elif isinstance(value, FindBy):
        return _resolve_findby(parent, None, value)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            newv = _resolve(promises, parent, v)
            if newv is not v:
                value[i] = newv
    return value


def _resolve_findby(
    parent: capellambse.ModelObject | capellambse.MelodyModel,
    attr: str | None,
    value: FindBy,
) -> capellambse.ModelObject:
    attrs = dict(value.attributes)
    typehint = attrs.pop("_type", None)
    if not isinstance(typehint, (str, type(None))):
        raise TypeError(
            f"Expected a string for !find {{_type: ...}},"
            f" got {type(typehint)}: {typehint!r}"
        )
    if typehint is None:
        wanted_types: tuple[type[t.Any], ...] = ()
    else:
        wanted_types = common.find_wrapper(typehint)
        if not wanted_types:
            raise ValueError(f"Unknown type: {typehint}")

    if isinstance(parent, capellambse.MelodyModel):
        candidates = parent.search(*wanted_types)
    elif attr is not None:
        candidates = getattr(parent, attr)
        if wanted_types:
            candidates = candidates.filter(
                lambda i: isinstance(i, wanted_types)
            )
    else:
        candidates = parent._model.search()

    if attrs:
        if len(attrs) > 1:
            expected_values = tuple(attrs.values())
        else:
            (expected_values,) = attrs.values()
        getter = operator.attrgetter(*attrs)

        def do_filter(obj):
            try:
                real_values = getter(obj)
            except AttributeError:
                return False
            return real_values == expected_values

        candidates = candidates.filter(do_filter)

    if len(candidates) > 1:
        hint = "(Hint: did you mean '_type' instead of 'type'?)\n" * (
            "type" in value.attributes and "_type" not in value.attributes
        )
        raise ValueError(
            f"Ambiguous match directive: !find {value.attributes!r}\n"
            + hint
            + f"Found {len(candidates)} matches:\n"
            + candidates._short_repr_()
        )
    if not candidates:
        raise _NoObjectFoundError(
            f"No object found for !find {value.attributes!r}"
        )
    return candidates[0]


class _UnresolvablePromise(BaseException):
    pass


class _NoObjectFoundError(ValueError):
    pass


_OPERATIONS = collections.OrderedDict(
    (
        ("create", _operate_create),
        ("extend", _operate_extend),
        ("modify", _operate_modify),
        ("set", _operate_set),
        ("sync", _operate_sync),
        ("delete", _operate_delete),
    )
)


def _create_complex_objects(
    promises: dict[Promise, capellambse.ModelObject],
    parent: capellambse.ModelObject,
    attr: str,
    objs: cabc.Iterable[dict[str, t.Any] | Promise | str],
) -> cabc.Generator[_OperatorResult, t.Any, None]:
    try:
        target = getattr(parent, attr)
    except AttributeError:
        raise TypeError(
            "Cannot create object:"
            f" {type(parent).__name__} has no attribute {attr!r}"
        ) from None
    if not isinstance(target, common.ElementList):
        raise TypeError(
            "Cannot create object:"
            f" {type(parent).__name__}.{attr} is not a list"
        )
    if not isinstance(target, common.ElementListCouplingMixin):
        raise TypeError(
            "Cannot create object:"
            f" {type(parent).__name__}.{attr} is not model-coupled"
        )
    for child in objs:
        if isinstance(
            child, (common.GenericElement, list, Promise, _ObjectFinder)
        ):
            try:
                obj = _resolve(promises, parent, child)
            except _UnresolvablePromise as p:
                yield p.args[0], {"parent": parent, "extend": {attr: [child]}}
            else:
                target.append(obj)
        elif isinstance(child, str):
            target.create_singleattr(child)
        else:
            yield from _create_complex_object(
                promises, parent, attr, target, child
            )


def _create_complex_object(
    promises: dict[Promise, capellambse.ModelObject],
    parent: capellambse.ModelObject,
    attr: str,
    target: common.ElementListCouplingMixin,
    obj_desc: dict[str, t.Any],
) -> cabc.Generator[_OperatorResult, t.Any, None]:
    try:
        promise: str | Promise | None = obj_desc.pop("promise_id")
    except KeyError:
        promise = None

    complex_attrs = dict[str, t.Any]()
    simple_attrs = dict[str, t.Any]()
    type_hint = tuple[str, ...]()
    try:
        for k, v in obj_desc.items():
            if k == "_type":
                type_hint = (v,)
            elif isinstance(v, cabc.Iterable) and not isinstance(v, str):
                complex_attrs[k] = v
            else:
                simple_attrs[k] = _resolve(promises, parent, v)
    except _UnresolvablePromise as p:
        obj_desc["promise_id"] = promise
        yield (p.args[0], {"parent": parent, "extend": {attr: [obj_desc]}})
        return
    assert isinstance(target, common.ElementListCouplingMixin)
    obj = target.create(*type_hint, **simple_attrs)
    if promise is not None:
        if isinstance(promise, str):
            promise = Promise(promise)
        yield (promise, obj)
    for subkey, subval in complex_attrs.items():
        if isinstance(subval, cabc.Iterable):
            yield from _create_complex_objects(promises, obj, subkey, subval)
        else:
            raise TypeError(f"Expected list, got {type(subval).__name__}")


@dataclasses.dataclass(frozen=True)
class Promise:
    """References a model object that will be created later."""

    identifier: str


class UnfulfilledPromisesError(RuntimeError):
    """A promise could not be fulfilled.

    This exception is raised when a promise is referenced via
    ``!promise``, but it is never fulfilled by declaring an object with
    the same ``promise_id``.
    """

    def __str__(self) -> str:
        if (
            len(self.args) == 1
            and isinstance(self.args[0], cabc.Iterable)
            and not isinstance(self.args[0], str)
        ):
            return ", ".join(i.identifier for i in self.args[0])
        return super().__str__()


@dataclasses.dataclass(frozen=True)
class UUIDReference:
    """References a model object by its UUID."""

    uuid: helpers.UUIDString

    def __post_init__(self) -> None:
        if not helpers.is_uuid_string(self.uuid):
            raise ValueError(f"Malformed `!uuid`: {self.uuid!r}")


@dataclasses.dataclass(frozen=True)
class FindBy:
    """Find an object by specific attributes."""

    attributes: cabc.Mapping[str, t.Any]


_ObjectFinder: tuple[type, ...] = (
    UUIDReference,
    FindBy,
)


class YDMDumper(yaml.SafeDumper):
    """A YAML dumper with extensions for declarative modelling."""

    def represent_promise(self, data: t.Any) -> yaml.Node:
        assert isinstance(data, Promise)
        return self.represent_scalar("!promise", data.identifier)

    def represent_uuidref(self, data: t.Any) -> yaml.Node:
        assert isinstance(data, UUIDReference)
        return self.represent_scalar("!uuid", data.uuid)

    def represent_newobj(self, data: t.Any) -> yaml.Node:
        assert isinstance(data, NewObject)
        attrs = dict(data._kw)
        if len(data._type_hint) > 1:
            raise TypeError("Cannot use more than one type hint")
        if len(data._type_hint) == 1:
            attrs["_type"] = data._type_hint[0]
        return self.represent_mapping("!new_object", attrs)

    def represent_findby(self, data: t.Any) -> yaml.Node:
        assert isinstance(data, FindBy)
        attrs = dict(data.attributes)
        return self.represent_mapping("!find", attrs)


YDMDumper.add_representer(Promise, YDMDumper.represent_promise)
YDMDumper.add_representer(UUIDReference, YDMDumper.represent_uuidref)
YDMDumper.add_representer(NewObject, YDMDumper.represent_newobj)
YDMDumper.add_representer(FindBy, YDMDumper.represent_findby)


class YDMLoader(yaml.SafeLoader):
    """A YAML loader with extensions for declarative modelling."""

    def construct_promise(self, node: yaml.Node) -> Promise:
        if not isinstance(node, yaml.ScalarNode):
            raise TypeError("!promise only accepts scalar nodes")
        data = self.construct_scalar(node)
        if not isinstance(data, str):
            raise TypeError("!promise only accepts string scalars")
        return Promise(data)

    def construct_uuidref(self, node: yaml.Node) -> UUIDReference:
        if not isinstance(node, yaml.ScalarNode):
            raise TypeError("!uuid only accepts scalar nodes")
        data = self.construct_scalar(node)
        if not helpers.is_uuid_string(data):
            raise ValueError(f"Not a well-formed UUID string: {data}")
        return UUIDReference(data)

    def construct_newobj(self, node: yaml.Node) -> NewObject:
        if not isinstance(node, yaml.MappingNode):
            raise TypeError("!new_object only accepts mapping nodes")
        data = self.construct_mapping(node)
        try:
            _type = data.pop("_type")
        except KeyError:
            raise ValueError("!new_object requires a _type key") from None
        return NewObject(_type, **t.cast(t.Any, data))

    def construct_findby(self, node: yaml.Node) -> FindBy:
        if not isinstance(node, yaml.MappingNode):
            raise TypeError("!find only accepts mapping nodes")
        data = self.construct_mapping(node)
        return FindBy(t.cast(t.Any, data))


YDMLoader.add_constructor("!promise", YDMLoader.construct_promise)
YDMLoader.add_constructor("!uuid", YDMLoader.construct_uuidref)
YDMLoader.add_constructor("!new_object", YDMLoader.construct_newobj)
YDMLoader.add_constructor("!find", YDMLoader.construct_findby)


try:
    import click
except ImportError:

    def _main() -> None:
        """Display a dependency error."""
        print("Error: Please install 'click' and retry", file=sys.stderr)
        raise SystemExit(1)

else:

    @click.command()
    @click.option("-m", "--model", type=capellambse.ModelCLI(), required=True)
    @click.argument("file", type=click.File("r"))
    def _main(model: capellambse.MelodyModel, file: t.IO[str]) -> None:
        """Apply a declarative modelling YAML file to a model."""
        apply(model, file)
        model.save()


if __name__ == "__main__":
    _main()
