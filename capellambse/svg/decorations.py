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
"""The decoration factories for svg elements."""
from __future__ import annotations

import collections.abc as cabc
import logging
import re
import typing as t

logger = logging.getLogger(__name__)

icon_size = 20
icon_padding = 2
feature_space = 24

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
# TODO: Instead of dirty-patching either rename FunctionalExchange in OA-Layer as
# ActivityExchange/OperationalExchange
DiagramClass = str
FaultyClass = str
PatchClass = str

needs_patch: dict[DiagramClass, dict[FaultyClass, PatchClass]] = {
    "Operational Entity Blank": {"FunctionalExchange": "OperationalExchange"}
}
always_top_label = {"Note", "Class", "Enumeration"}
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
