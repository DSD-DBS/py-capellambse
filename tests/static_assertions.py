# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=unused-variable
"""Static duck-typing assertions checked by mypy."""
from __future__ import annotations

from capellambse import model


def protocol_ModelObject_compliance():
    mobj: model.common.ModelObject

    mobj = model.GenericElement()  # type: ignore[call-arg]
    mobj = model.MelodyModel()  # type: ignore[call-arg]
    mobj = model.common.accessors._Specification()  # type: ignore[call-arg]
