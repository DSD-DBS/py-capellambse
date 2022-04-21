# Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

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
