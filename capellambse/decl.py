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
    "YDMDumper",
    "YDMLoader",
    "dump",
    "load",
]

import collections.abc as cabc
import contextlib
import dataclasses
import os
import typing as t

import yaml

from capellambse import helpers

FileOrPath = t.Union[t.IO[str], str, os.PathLike[t.Any]]


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


@dataclasses.dataclass(frozen=True)
class Promise:
    """References a model object that will be created later."""

    identifier: str


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
