# Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Tests for aird-filters applied after rendering a diagram"""
import pytest

from capellambse import MelodyModel, aird

COMP_PORT_FILTER_DIAG = "[LAB] Test Component Port Filter"
EX_ITEMS_FILTER_DIAG = "[SDFB] Test ExchangeItem Filter"
STD_ACTIVATED_FLTERS = [
    "ModelExtensionFilter",
    "hide.overlappedfunctional.chains.label.filter",
    "hide.overlappedfunctional.chains.icon.filter",
]
EX_ITEMS_FLTER = "show.exchange.items.filter"
NAME_AND_EX_ITEMS_FILTER = "show.functional.exchanges.exchange.items.filter"


def test_diagram_has_activated_filters(model_5_2: MelodyModel) -> None:
    diag = model_5_2.diagrams.by_name(EX_ITEMS_FILTER_DIAG)

    assert diag.activated_filters == STD_ACTIVATED_FLTERS


def test_add_activated_filter_to_diagram(model_5_2: MelodyModel) -> None:
    diag = model_5_2.diagrams.by_name(EX_ITEMS_FILTER_DIAG)

    diag.add_activated_filter(EX_ITEMS_FLTER)

    assert diag.activated_filters == STD_ACTIVATED_FLTERS + [EX_ITEMS_FLTER]


def test_remove_activated_filter_on_diagram(model_5_2: MelodyModel) -> None:
    diag = model_5_2.diagrams.by_name(EX_ITEMS_FILTER_DIAG)

    diag.remove_activated_filter(STD_ACTIVATED_FLTERS[0])

    assert diag.activated_filters == STD_ACTIVATED_FLTERS[1:]


def test_remove_activated_filter_fails(model_5_2: MelodyModel) -> None:
    diag = model_5_2.diagrams.by_name(EX_ITEMS_FILTER_DIAG)

    with pytest.raises(ValueError):
        diag.remove_activated_filter(EX_ITEMS_FLTER)


def test_component_ports_filter_is_applied(model: MelodyModel) -> None:
    diag = model.diagrams.by_name(COMP_PORT_FILTER_DIAG)
    diag = diag.render(None)
    assert all(
        d.hidden
        for d in diag
        if d.port and d.styleclass and d.styleclass.startswith("CP_")
    )


def test_fex_exchangeitems_filter_is_applied(model_5_2: MelodyModel) -> None:
    diag = model_5_2.diagrams.by_name(EX_ITEMS_FILTER_DIAG)
    aird.RENDER_PARAMS["sorted_exchangedItems"] = False

    diag.add_activated_filter(EX_ITEMS_FLTER)
    diag = diag.render(None)
    fex_edge = diag["_yovTvM-ZEeytxdoVf3xHjA"]

    assert len(fex_edge.labels) == 1
    assert fex_edge.labels[0].label == "[ExchangeItem 1, Example]"


@pytest.mark.parametrize(
    "sort,expected_label",
    [
        pytest.param(
            False,
            "Test fex [ExchangeItem 1, Example]",
            id="Keep Capella order",
        ),
        pytest.param(
            True,
            "Test fex [Example, ExchangeItem 1]",
            id="With sorted ExchangeItems",
        ),
    ],
)
def test_fex_exchangeitems_filter_with_name_is_applied(
    model_5_2: MelodyModel, sort: bool, expected_label: str
) -> None:
    diag = model_5_2.diagrams.by_name(EX_ITEMS_FILTER_DIAG)
    aird.RENDER_PARAMS["sorted_exchangedItems"] = sort

    diag.add_activated_filter(NAME_AND_EX_ITEMS_FILTER)
    diag = diag.render(None)
    fex_edge = diag["_yovTvM-ZEeytxdoVf3xHjA"]

    assert len(fex_edge.labels) == 1
    assert fex_edge.labels[0].label == expected_label
