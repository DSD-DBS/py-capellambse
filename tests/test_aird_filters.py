# Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Tests for aird-filters applied after rendering a diagram"""
import pytest

from capellambse import MelodyModel, aird

COMP_PORT_FILTER_DIAG = "[LAB] Test Component Port Filter"
EX_ITEMS_FILTER_DIAG = "[SDFB] Test ExchangeItem Filter"


def test_component_ports_filter_is_applied(model: MelodyModel) -> None:
    diag = model.diagrams.by_name(COMP_PORT_FILTER_DIAG)
    diag = diag.render(None)
    assert all(
        d.hidden
        for d in diag
        if d.port and d.styleclass and d.styleclass.startswith("CP_")
    )


@pytest.mark.parametrize(
    "sort,keep_name,expected_label",
    [
        pytest.param(
            False, True, "Test fex [ExchangeItem 1, Example]", id="Capella"
        ),
        pytest.param(
            True,
            True,
            "Test fex [Example, ExchangeItem 1]",
            id="with_sorted_items",
        ),
        pytest.param(
            False,
            False,
            "[ExchangeItem 1, Example]",
            id="without_keeping_primary_name",
        ),
    ],
)
def test_fex_exchangeitems_filter_is_applied(
    model_5_2: MelodyModel, sort: bool, keep_name: bool, expected_label: str
) -> None:
    diag = model_5_2.diagrams.by_name(EX_ITEMS_FILTER_DIAG)
    aird.RENDER_PARAMS["sorted_exchangedItems"] = sort
    aird.RENDER_PARAMS["keep_primary_name"] = keep_name

    diag = diag.render(None)
    fex_edge = diag["_yovTvM-ZEeytxdoVf3xHjA"]

    assert len(fex_edge.labels) == 1
    assert fex_edge.labels[0].label == expected_label
