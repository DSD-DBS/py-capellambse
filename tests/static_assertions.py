# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Static duck-typing assertions checked by mypy."""

from __future__ import annotations

from capellambse import model


def protocol_ModelObject_compliance():
    mobj: model.ModelObject

    mobj = model.ModelElement()  # type: ignore[call-arg]
    mobj = model._descriptors._Specification()  # type: ignore[call-arg]
    mobj = model.diagram.Diagram()

    del mobj
