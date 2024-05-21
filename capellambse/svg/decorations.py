# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""The decoration factories for svg elements."""
from __future__ import annotations

import collections.abc as cabc
import dataclasses
import logging
import re

from capellambse.diagram import _icons

logger = logging.getLogger(__name__)

icon_size = 20
"""Default icon size."""
icon_padding = 2
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
class DecoFactory:
    function: cabc.Callable
    dependencies: tuple[str, ...]


class DecoFactories(
    cabc.Mapping[str, DecoFactory | _icons._FactoryDefinition]
):
    def __init__(self) -> None:
        self.__markers: dict[str, DecoFactory] = {}

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
            self.__markers[symbol_name] = DecoFactory(
                func, tuple(dependencies)
            )
            return func

        if func is None:
            return decorator
        return decorator(func)

    def __iter__(self) -> cabc.Iterator[str]:
        yield from _icons._FACTORIES
        yield from self.__markers

    def __len__(self) -> int:
        return len(_icons._FACTORIES) + len(self.__markers)

    def __getitem__(self, k: str) -> DecoFactory | _icons._FactoryDefinition:
        if k.endswith("Symbol"):
            try:
                return _icons._FACTORIES[k]
            except KeyError:
                pass

        elif k.endswith("Mark"):
            try:
                return self.__markers[k]
            except KeyError:
                pass

        logger.warning("Unknown symbol requested: %s", k)
        return _icons._FACTORIES["ErrorSymbol"]

    def __contains__(self, o: object) -> bool:
        return o in _icons._FACTORIES or o in self.__markers


deco_factories = DecoFactories()
