# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

__all__ = [
    "FragmentType",
    "Loader",
    "ModelInfo",
]

import dataclasses
import enum
import pathlib
import typing as t

from capellambse import filehandler

if t.TYPE_CHECKING:
    from . import core

Loader: t.TypeAlias = "core.MelodyLoader"


class FragmentType(enum.Enum):
    """The type of an XML fragment."""

    SEMANTIC = enum.auto()
    VISUAL = enum.auto()
    OTHER = enum.auto()


@dataclasses.dataclass
class ModelInfo:
    url: str | None
    title: str | None
    entrypoint: pathlib.PurePosixPath
    resources: dict[str, filehandler.abc.HandlerInfo]
    capella_version: str
    viewpoints: dict[str, str]
