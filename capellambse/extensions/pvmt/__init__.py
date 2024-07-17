# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Property Value Management extension for |project|."""
from __future__ import annotations

from ._config import *
from ._objects import *


def init() -> None:
    """Initialize the PVMT extension."""
    # pylint: disable=redefined-outer-name # false-positive
    import capellambse
    import capellambse.model.common as c

    c.set_accessor(
        capellambse.MelodyModel,
        "pvmt",
        PVMTConfigurationAccessor(),
    )
    c.set_accessor(c.GenericElement, "pvmt", c.AlternateAccessor(ObjectPVMT))
