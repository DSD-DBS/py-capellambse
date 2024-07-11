# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import dataclasses
import pathlib


@dataclasses.dataclass
class ModelInfo:
    branch: str | None = None
    title: str | None = None
    url: str | None = None
    entrypoint: pathlib.PurePosixPath | None = None
    revision: str | None = None
    rev_hash: str | None = None
    capella_version: str | None = None
    viewpoints: dict[str, str] = dataclasses.field(default_factory=dict)
