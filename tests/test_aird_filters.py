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
"""Tests for aird-filters applied after rendering a diagram"""
import capellambse

COMP_PORT_FILTER_DIAG = "[LAB] Test Component Port Filter"


def test_component_ports_filter_is_applied(
    model: capellambse.MelodyModel,
) -> None:
    diag = model.diagrams.by_name(COMP_PORT_FILTER_DIAG)
    diag = diag.render(None)
    assert all(
        d.hidden
        for d in diag
        if d.port and d.styleclass and d.styleclass.startswith("CP_")
    )
