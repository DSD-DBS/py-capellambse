# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import dataclasses
import pathlib
import typing as t

if t.TYPE_CHECKING:
    from capellambse import filehandler


@dataclasses.dataclass
class ModelInfo:
    url: str | None
    title: str | None
    entrypoint: pathlib.PurePosixPath
    resources: dict[str, filehandler.abc.HandlerInfo]
    capella_version: str
    viewpoints: dict[str, str]
