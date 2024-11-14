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
    "Promise",
    "UUIDReference",
    "UnfulfilledPromisesError",
    "YDMDumper",
    "YDMLoader",
    "apply",
    "dump",
    "load",
    # Metadata handling
    "Metadata",
    "ModelMetadata",
    "WriterMetadata",
    "load_with_metadata",
]

import collections
import collections.abc as cabc
import contextlib
import dataclasses
import importlib.metadata as imm
import logging
import operator
import os
import pathlib
import re
import sys
import typing as t

import awesomeversion as av
import typing_extensions as te
import yaml

import capellambse
import capellambse.model as m
from capellambse import helpers
from capellambse.model import NewObject

FileOrPath = str | os.PathLike[t.Any] | t.IO[str]
_FutureAction = dict[str, t.Any]
_OperatorResult = tuple[
    "Promise",
    capellambse.ModelObject | _FutureAction,
]
logger = logging.getLogger(__name__)


class WriterMetadata(t.TypedDict):
    capellambse: str
    generator: te.NotRequired[str]


class ModelMetadata(t.TypedDict):
    url: str
    revision: te.NotRequired[str]
    entrypoint: str


class Metadata(t.TypedDict, total=False):
    written_by: WriterMetadata
    model: ModelMetadata


@t.overload
def dump(
    instructions: cabc.Sequence[cabc.Mapping[str, t.Any]],
    *,
    metadata: Metadata | None = None,
) -> str: ...
@t.overload
def dump(
    instructions: cabc.Sequence[cabc.Mapping[str, t.Any]],
    *,
    metadata: m.MelodyModel,
    generator: str | None = None,
) -> str: ...
def dump(
    instructions: cabc.Sequence[cabc.Mapping[str, t.Any]],
    *,
    metadata: m.MelodyModel | Metadata | None = None,
    generator: str | None = None,
) -> str:
    """Dump an instruction stream to YAML.

    Optionally dump metadata with the instruction stream to YAML.
    """
    if isinstance(metadata, m.MelodyModel):
        res_info = metadata.info.resources["\x00"]
        metadata = {
            "model": {
                "url": res_info.url,
                "revision": res_info.rev_hash,
                "entrypoint": str(metadata.info.entrypoint),
            },
            "written_by": {
                "capellambse": capellambse.__version__.split("+", 1)[0]
            },
        }
        if generator is not None:
            metadata["written_by"]["generator"] = generator

    if not metadata:
        return yaml.dump(instructions, Dumper=YDMDumper)
    return yaml.dump_all([metadata, instructions], Dumper=YDMDumper)


def load(file: FileOrPath) -> list[dict[str, t.Any]]:
    """Load an instruction stream from a YAML file.

    Parameters
    ----------
    file
        An open file-like object containing decl instructions, or a path
        or PathLike pointing to such a file. Files are expected to use
        UTF-8 encoding.
    """
    _, instructions = load_with_metadata(file)
    return instructions


def load_with_metadata(
    file: FileOrPath,
) -> tuple[Metadata, list[dict[str, t.Any]]]:
    """Load an instruction stream and its metadata from a YAML file.

    If the file does not have a metadata section, an empty dict will be
    returned.

    Parameters
    ----------
    file
        An open file-like object containing decl instructions, or a path
        or PathLike pointing to such a file. Files are expected to use
        UTF-8 encoding.

    Returns
    -------
    dict[str, Any]
        The metadata read from the file, or an empty dictionary if the
        file did not contain any metadata.
    list[dict[str, Any]]
        The instruction stream.
    """
    if hasattr(file, "read"):
        file = t.cast(t.IO[str], file)
        ctx: t.ContextManager[t.IO[str]] = contextlib.nullcontext(file)
    else:
        assert not isinstance(file, t.IO)
        ctx = open(file, encoding="utf-8")  # noqa: SIM115

    with ctx as opened_file:
        contents = list(yaml.load_all(opened_file, Loader=YDMLoader))

    if len(contents) == 2:
        return (t.cast(Metadata, contents[0]) or {}, contents[1] or [])
    if len(contents) == 1:
        return ({}, contents[0] or [])
    if len(contents) == 0:
        return ({}, [])
    raise ValueError(
        f"Expected a YAML file with 1 or 2 documents, found {len(contents)}"
    )


def apply(
    model: capellambse.MelodyModel,
    file: FileOrPath,
    *,
    strict: bool = False,
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
    strict
        Verify metadata contained in the file against the used model,
        and raise an error if they don't match.

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
    metadata, raw_instructions = load_with_metadata(file)
    instructions = collections.deque(raw_instructions)
    promises = dict[Promise, capellambse.ModelObject]()
    deferred = collections.defaultdict[Promise, list[_FutureAction]](list)

    if strict:
        if not metadata:
            raise ValueError("No metadata found to verify in strict mode")
        _verify_metadata(model, metadata)
    elif metadata:
        try:
            _verify_metadata(model, metadata)
        except ValueError as err:
            logger.warning("Metadata does not match provided model: %s", err)

    while instructions:
        instruction = instructions.popleft()

        parent = instruction.pop("parent")
        if isinstance(parent, Promise | _ObjectFinder):
            try:
                parent = _resolve(promises, model.project, parent)
            except _UnresolvablePromise as p:
                d = {"parent": parent, **instruction}
                deferred[p.args[0]].append(d)
                continue

        if not isinstance(parent, capellambse.model.ModelElement):
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


def _verify_metadata(
    model: capellambse.MelodyModel, metadata: Metadata
) -> None:
    assert metadata

    written_by = metadata.get("written_by", {}).get("capellambse", "")
    if not written_by:
        raise ValueError(
            "Unsupported YAML: Can't find 'written_by:capellambse' in metadata"
        )
    if not _is_pep440(written_by):
        raise ValueError(f"Malformed version number in metadata: {written_by}")

    current = av.AwesomeVersion(
        imm.version("capellambse").partition("+")[0],
        ensure_strategy=av.AwesomeVersionStrategy.PEP440,
    )
    try:
        written_version = av.AwesomeVersion(
            written_by,
            ensure_strategy=av.AwesomeVersionStrategy.PEP440,
        )
        version_matches = current >= written_version
    except Exception as err:
        raise ValueError(
            "Cannot apply decl: Cannot verify required capellambse version:"
            f" {type(err).__name__}: {err}"
        ) from None

    if not version_matches:
        raise ValueError(
            "Cannot apply decl: This capellambse is too old for this YAML:"
            f" Need at least v{written_by}, but have only v{current})"
        )

    model_metadata = metadata.get("model", {})
    res_info = model.info.resources["\x00"]
    url = model_metadata.get("url")
    if url != res_info.url:
        raise ValueError(
            "Cannot apply decl: Model URL mismatch:"
            f" YAML expects {url}, current is {res_info.url}"
        )

    hash = model_metadata.get("revision")
    if hash != res_info.rev_hash:
        raise ValueError(
            "Cannot apply decl: Model version mismatch:"
            f" YAML expects {hash}, current is {res_info.rev_hash}"
        )

    entrypoint = pathlib.PurePosixPath(model_metadata.get("entrypoint", ""))
    if entrypoint != model.info.entrypoint:
        raise ValueError(
            "Cannot apply decl: Model entrypoint mismatch:"
            f" YAML expects {entrypoint}, current is {model.info.entrypoint}"
        )


def _is_pep440(version: str) -> bool:
    """Check if given version aligns with PEP440.

    See Also
    --------
    https://peps.python.org/pep-0440/#appendix-b-parsing-version-strings-with-regular-expressions
    """
    pep440_ptrn = re.compile(
        r"([1-9][0-9]*!)?(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*((a|b|rc)"
        r"(0|[1-9][0-9]*))?(\.post(0|[1-9][0-9]*))?(\.dev(0|[1-9][0-9]*))?"
    )
    return pep440_ptrn.fullmatch(version) is not None


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
        if not isinstance(target, m.ElementList) or not isinstance(objs, list):
            delattr(parent, attr)
            continue
        if not isinstance(target, m.ElementListCouplingMixin):
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


def _operate_set(
    promises: dict[Promise, capellambse.ModelObject],
    parent: capellambse.ModelObject,
    modifications: dict[str, t.Any],
) -> cabc.Generator[_OperatorResult, t.Any, None]:
    for attr, value in modifications.items():
        if isinstance(value, list | Promise | _ObjectFinder):
            try:
                value = _resolve(promises, parent, value)
            except _UnresolvablePromise as p:
                yield p.args[0], {"parent": parent, "set": {attr: value}}
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
            if isinstance(find_args, dict):
                find_args = FindBy(find_args)
            assert isinstance(find_args, FindBy)

            try:
                candidate = _resolve_findby(promises, parent, attr, find_args)
            except _NoObjectFoundError:
                candidate = None
            except _UnresolvablePromise as p:
                yield p.args[0], {"parent": parent, "sync": {attr: [obj]}}
                continue

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
                    find_args.attributes
                    | obj.pop("set", {})
                    | obj.pop("extend", {})
                )
                if "promise_id" in obj:
                    newobj_props["promise_id"] = obj.pop("promise_id")
                yield from _create_complex_objects(
                    promises, parent, attr, [newobj_props]
                )
                if "sync" in obj:
                    yield from _operate_sync(promises, parent, {attr: [obj]})


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
    elif isinstance(value, FindBy):
        return _resolve_findby(promises, parent, None, value)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            newv = _resolve(promises, parent, v)
            if newv is not v:
                value[i] = newv
    return value


def _resolve_findby(
    promises: dict[Promise, capellambse.ModelObject],
    parent: capellambse.ModelObject,
    attr: str | None,
    value: FindBy,
) -> capellambse.ModelObject:
    attrs = dict(value.attributes)
    typehint = attrs.pop("_type", None)
    if not isinstance(typehint, str | type(None)):
        raise TypeError(
            f"Expected a string for !find {{_type: ...}},"
            f" got {type(typehint)}: {typehint!r}"
        )
    if typehint is None:
        wanted_types: tuple[type[t.Any], ...] = ()
    else:
        wanted_types = m.find_wrapper(typehint)
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
        candidates = parent._model.search(*wanted_types)

    if attrs:
        for k, v in attrs.items():
            if isinstance(v, list | Promise | _ObjectFinder):
                attrs[k] = _resolve(promises, parent, v)

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
    if not isinstance(target, m.ElementList):
        raise TypeError(
            "Cannot create object:"
            f" {type(parent).__name__}.{attr} is not a list"
        )
    if not isinstance(target, m.ElementListCouplingMixin):
        raise TypeError(
            "Cannot create object:"
            f" {type(parent).__name__}.{attr} is not model-coupled"
        )
    for child in objs:
        if isinstance(
            child,
            m.ModelElement | list | Promise | _ObjectFinder,
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
            assert not isinstance(child, Promise)  # mypy false-positive
            yield from _create_complex_object(
                promises, parent, attr, target, child
            )


def _create_complex_object(
    promises: dict[Promise, capellambse.ModelObject],
    parent: capellambse.ModelObject,
    attr: str,
    target: m.ElementListCouplingMixin,
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
    assert isinstance(target, m.ElementListCouplingMixin)
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


_ObjectFinder: t.TypeAlias = UUIDReference | FindBy


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
        if data._type_hint:
            attrs["_type"] = data._type_hint
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
            raise ValueError(f"Malformed UUID: {data}")
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
    @click.option("-s", "--strict/--relaxed", is_flag=True, default=False)
    @click.argument("file", type=click.File("r"))
    def _main(
        model: capellambse.MelodyModel,
        file: t.IO[str],
        strict: bool,
    ) -> None:
        """Apply a declarative modelling YAML file to a model."""
        apply(model, file, strict=strict)
        model.save()


if __name__ == "__main__":
    _main()
