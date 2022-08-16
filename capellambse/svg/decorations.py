# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""The decoration factories for svg elements."""
from __future__ import annotations

import collections.abc as cabc
import logging
import re
import typing as t

logger = logging.getLogger(__name__)

icon_size = 20
"""Default icon size."""
icon_padding = 2
"""Default icon padding (left/right side)."""
feature_space = 24
"""Default margins/padding (top/bot and left/right) for feature text."""

function_ports = {"FIP", "FOP"}
directed_component_ports = {"CP_IN", "CP_OUT"}
component_ports = directed_component_ports | {"PP", "CP_INOUT", "CP_UNSET"}
all_ports = function_ports | component_ports
all_directed_ports = directed_component_ports | function_ports
start_aligned = {
    "LogicalComponent",
    "LogicalActor",
    "LogicalHumanActor",
    "LogicalHumanComponent",
}
only_icons = {"Requirement"}
DiagramClass = str
FaultyClass = str
PatchClass = str
always_top_label = {
    "Class",
    "Enumeration",
    "Note",
    "OperationalActivity",
    "PhysicalComponent",
}
needs_feature_line = {"Class", "Enumeration"}


class DecoFactories(t.Dict[str, cabc.Callable]):
    def __call__(self, func: cabc.Callable) -> cabc.Callable:
        symbol_name = re.sub(
            "(?:^|_)([a-z])",
            lambda m: m.group(1).capitalize(),
            func.__name__,
        )
        self[symbol_name] = func
        return func

    def __missing__(self, class_: str) -> cabc.Callable:
        logger.error("%s wasn't found in factories.", class_)
        assert "ErrorSymbol" in self
        return self["ErrorSymbol"]


deco_factories = DecoFactories()
