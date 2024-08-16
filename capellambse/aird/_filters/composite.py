# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Composite filter implementations."""

from __future__ import annotations

import collections.abc as cabc
import functools
import typing as t

from capellambse import diagram

from .. import _semantic
from . import phase2_composite_filter


def _lookup_styleclasses(*styleclasses: str) -> frozenset[str]:
    returnclasses = set()
    for styleclass in styleclasses:
        new_styleclass, _ = _semantic.STYLECLASS_LOOKUP[styleclass]
        if new_styleclass:
            returnclasses.add(styleclass)
    return frozenset(returnclasses)


PORT_CL_COMPONENT = _lookup_styleclasses("ComponentPort")
PORT_CL_FUNCTION = _lookup_styleclasses(
    "FunctionInputPort", "FunctionOutputPort"
)


def hide_empty_ports(
    ebd: t.Any | None,
    dgobject: diagram.DiagramElement,
    *,
    classes: cabc.Container[str],
) -> None:
    """Hide child ports without context.

    This filter utilizes the fact that boxes track all connected edges
    as their "context". As ports do not have children, their context can
    only be the edge(s) that connect directly to them.
    """
    del ebd
    assert isinstance(dgobject, diagram.Box)

    for child in dgobject.children:
        if child.port and child.styleclass in classes and not child.context:
            child.hidden = True


phase2_composite_filter("Hide Component Ports without Exchanges")(
    functools.partial(hide_empty_ports, classes=PORT_CL_COMPONENT)
)
phase2_composite_filter("Hide Function Ports without Exchanges")(
    functools.partial(hide_empty_ports, classes=PORT_CL_FUNCTION)
)
