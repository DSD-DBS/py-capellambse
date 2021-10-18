# Copyright 2021 DB Netz AG
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Composite filter implementations."""
from __future__ import annotations

import collections.abc as cabc
import functools
import typing as t

from capellambse import aird

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
    dgobject: aird.DiagramElement,
    *,
    classes: cabc.Container[str],
) -> None:
    """Hide child ports without context.

    This filter utilizes the fact that boxes track all connected edges
    as their "context".  As ports do not have children, their context
    can only be the edge(s) that connect directly to them.
    """
    del ebd
    assert isinstance(dgobject, aird.Box)

    for child in dgobject.children:
        if child.port and child.styleclass in classes and not child.context:
            child.hidden = True


phase2_composite_filter("Hide Component Ports without Exchanges")(
    functools.partial(hide_empty_ports, classes=PORT_CL_COMPONENT)
)
phase2_composite_filter("Hide Function Ports without Exchanges")(
    functools.partial(hide_empty_ports, classes=PORT_CL_FUNCTION)
)
