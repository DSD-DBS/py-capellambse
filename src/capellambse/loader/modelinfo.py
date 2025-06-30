# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import warnings

from ._typing import ModelInfo as ModelInfo

warnings.warn(
    f"{__name__} is deprecated, import ModelInfo from capellambse.loader directly instead",
    stacklevel=2,
)
