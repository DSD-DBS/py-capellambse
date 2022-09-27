# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Support for YAML-based declarative modelling.

A YAML-based approach to describing how to create and modify
``capellambse`` compatible models.
"""
from __future__ import annotations

__all__ = [
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
import os
import typing as t

import yaml

import capellambse
from capellambse import helpers
from capellambse.model import common

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


def apply(model: capellambse.MelodyModel, file: FileOrPath) -> None:
    """Apply a declarative modelling file to the given model.

    Parameters
    ----------
    model
        The model to apply the instructions to.
    file
        An open file-like object to read YAML instructions from, or a
        path to such a file. Files will be read with UTF-8 encoding.

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
        if isinstance(parent, UUIDReference):
            parent = model.by_uuid(parent.uuid)
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


def _operate_create(
    promises: dict[Promise, capellambse.ModelObject],
    parent: capellambse.ModelObject,
    creations: dict[str, t.Any],
) -> cabc.Generator[_OperatorResult, t.Any, None]:
    for attr, value in creations.items():
        if not isinstance(value, cabc.Iterable):
            raise TypeError("values below `create:*:` must be lists")

        yield from _create_complex_objects(promises, parent, attr, value)


def _operate_delete(
    promises: dict[Promise, capellambse.ModelObject],
    parent: capellambse.ModelObject,
    deletions: dict[str, t.Any],
) -> cabc.Generator[_OperatorResult, t.Any, None]:
    raise NotImplementedError("Deleting objects is not yet implemented")


def _operate_modify(
    promises: dict[Promise, capellambse.ModelObject],
    parent: capellambse.ModelObject,
    modifications: dict[str, t.Any],
) -> cabc.Generator[_OperatorResult, t.Any, None]:
    for attr, value in modifications.items():
        if isinstance(value, (list, Promise, UUIDReference)):
            try:
                value = _resolve(promises, parent, value)
            except _UnresolvablePromise as p:
                yield p.args[0], {"parent": parent, "modify": {attr: value}}
                continue
        setattr(parent, attr, value)


def _resolve(
    promises: dict[Promise, capellambse.ModelObject],
    parent: capellambse.ModelObject,
    value: t.Any,
) -> t.Any:
    if isinstance(value, Promise):
        try:
            return promises[value]
        except KeyError:
            raise _UnresolvablePromise(value) from None
    elif isinstance(value, UUIDReference):
        return parent._model.by_uuid(value.uuid)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            newv = _resolve(promises, parent, v)
            if newv is not v:
                value[i] = newv
    return value


class _UnresolvablePromise(BaseException):
    pass


_OPERATIONS = collections.OrderedDict(
    (
        ("create", _operate_create),
        ("modify", _operate_modify),
        ("delete", _operate_delete),
    )
)


def _create_complex_objects(
    promises: dict[Promise, capellambse.ModelObject],
    parent: capellambse.ModelObject,
    attr: str,
    objs: cabc.Iterable[dict[str, t.Any] | Promise],
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
        if isinstance(child, (list, Promise, UUIDReference)):
            try:
                obj = _resolve(promises, parent, child)
            except _UnresolvablePromise as p:
                yield p.args[0], {"parent": parent, "create": {attr: [child]}}
            else:
                target.append(obj)
        else:
            yield from _create_complex_object(promises, target, child)


def _create_complex_object(
    promises: dict[Promise, capellambse.ModelObject],
    target: common.ElementListCouplingMixin,
    obj_desc: dict[str, t.Any],
) -> cabc.Generator[_OperatorResult, t.Any, None]:
    try:
        promise: str | Promise | None = obj_desc.pop("promise_id")
    except KeyError:
        promise = None

    complex_attrs = {
        k: v
        for k, v in obj_desc.items()
        if isinstance(v, cabc.Iterable) and not isinstance(v, str)
    }
    simple_attrs = {
        k: v for k, v in obj_desc.items() if k not in complex_attrs
    }
    assert isinstance(target, common.ElementListCouplingMixin)
    obj = target.create(**simple_attrs)
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


class YDMDumper(yaml.SafeDumper):
    """A YAML dumper with extensions for declarative modelling."""

    def represent_promise(self, data: t.Any) -> yaml.Node:
        assert isinstance(data, Promise)
        return self.represent_scalar("!promise", data.identifier)

    def represent_uuidref(self, data: t.Any) -> yaml.Node:
        assert isinstance(data, UUIDReference)
        return self.represent_scalar("!uuid", data.uuid)


YDMDumper.add_representer(Promise, YDMDumper.represent_promise)
YDMDumper.add_representer(UUIDReference, YDMDumper.represent_uuidref)


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


YDMLoader.add_constructor("!promise", YDMLoader.construct_promise)
YDMLoader.add_constructor("!uuid", YDMLoader.construct_uuidref)
