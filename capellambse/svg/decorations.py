# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""The decoration factories for svg elements."""

from __future__ import annotations

import collections.abc as cabc
import dataclasses
import logging
import re

logger = logging.getLogger(__name__)

icon_size = 20
"""Default icon size."""
icon_padding = 1
"""Default icon padding (left/right side)."""
feature_space = 24
"""Default margins/padding (top/bot and left/right) for feature text."""
max_label_width = 1500
"""Maximum width for a label."""
min_symbol_width = 200
"""Minimum width (available horizontal space) for a symbol."""

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
needs_feature_line = {
    "BooleanType",
    "Class",
    "PrimitiveClass",
    "Enumeration",
    "NumericType",
    "PhysicalQuantity",
    "StringType",
}
always_top_label = needs_feature_line | {
    "Note",
    "RepresentationLink",
    "OperationalActivity",
    "PhysicalBehaviorComponent",
    "PhysicalBehaviorHumanComponent",
    "PhysicalBehaviorActor",
    "PhysicalBehaviorHumanActor",
    "PhysicalNodeComponent",
    "PhysicalNodeHumanComponent",
    "PhysicalNodeActor",
    "PhysicalNodeHumanActor",
}


@dataclasses.dataclass
class MarkerFactory:
    function: cabc.Callable
    dependencies: tuple[str, ...]


class MarkerFactories(dict[str, MarkerFactory]):
    def __call__(
        self,
        func: cabc.Callable | None = None,
        dependencies: cabc.Iterable[str] = (),
    ) -> cabc.Callable:
        def decorator(func: cabc.Callable) -> cabc.Callable:
            symbol_name = re.sub(
                "(?:^|_)([a-z])",
                lambda m: m.group(1).capitalize(),
                func.__name__,
            )
            if not symbol_name.endswith("Mark"):
                raise RuntimeError(f"Invalid marker name: {symbol_name}")
            self[symbol_name] = MarkerFactory(func, tuple(dependencies))
            return func

        if func is None:
            return decorator
        return decorator(func)


marker_factories = MarkerFactories()
