# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
"""Property Value Management extension for |project|."""
from __future__ import annotations

from . import _config, _objects
from ._config import *
from ._objects import *


def init() -> None:
    """Initialize the PVMT extension for |project|.

    Automatically called by |project|.
    """
    # pylint: disable=redefined-outer-name # false-positive
    import capellambse
    import capellambse.model.common as c

    c.set_accessor(
        c.GenericElement, "pvmt", c.AlternateAccessor(_objects.ObjectPVMT)
    )
    c.set_accessor(
        capellambse.MelodyModel, "pvmt", _config.PVMTConfigurationAccessor()
    )
