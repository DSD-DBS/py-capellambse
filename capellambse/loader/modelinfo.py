# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class ModelInfo:
    branch: str | None = None
    title: str | None = None
    url: str | None = None
    revision: str | None = None
    rev_hash: str | None = None
    capella_version: str | None = None
