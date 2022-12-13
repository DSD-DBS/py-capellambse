# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Tests for aird-filters applied after rendering a diagram."""
import pytest

import capellambse
from capellambse import diagram
from capellambse import model as model_

COMP_PORT_FILTER_DIAG = "[LAB] Test Component Port Filter"
EX_ITEMS_FILTER_DIAG = "[SDFB] Test ExchangeItem Filter"
DEFAULT_ACTIVATED_FILTERS = frozenset(
    {
        "ModelExtensionFilter",
        "hide.overlappedfunctional.chains.label.filter",
        "hide.overlappedfunctional.chains.icon.filter",
    }
)
EX_ITEMS_FILTER = "show.exchange.items.filter"
NAME_AND_EX_ITEMS_FILTER = "show.functional.exchanges.exchange.items.filter"


def test_diagram_has_activated_filters(
    model_5_2: capellambse.MelodyModel,
) -> None:
    diag: model_.diagram.Diagram = model_5_2.diagrams.by_name(
        EX_ITEMS_FILTER_DIAG
    )

    assert diag.filters == DEFAULT_ACTIVATED_FILTERS


def test_add_activated_filter_to_diagram(
    model_5_2: capellambse.MelodyModel,
) -> None:
    diag: model_.diagram.Diagram = model_5_2.diagrams.by_name(
        EX_ITEMS_FILTER_DIAG
    )

    diag.filters.add(EX_ITEMS_FILTER)

    assert EX_ITEMS_FILTER in diag.filters


@pytest.mark.parametrize("filter_name", DEFAULT_ACTIVATED_FILTERS)
def test_remove_activated_filter_on_diagram(
    model_5_2: capellambse.MelodyModel, filter_name: str
) -> None:
    diag: model_.diagram.Diagram = model_5_2.diagrams.by_name(
        EX_ITEMS_FILTER_DIAG
    )

    diag.filters.remove(filter_name)

    assert diag.filters == DEFAULT_ACTIVATED_FILTERS - {filter_name}


def test_remove_activated_filter_fails_if_not_active(
    model_5_2: capellambse.MelodyModel,
) -> None:
    diag: model_.diagram.Diagram = model_5_2.diagrams.by_name(
        EX_ITEMS_FILTER_DIAG
    )

    with pytest.raises(KeyError):
        diag.filters.remove(EX_ITEMS_FILTER)


def test_component_ports_filter_is_applied(
    model: capellambse.MelodyModel,
) -> None:
    diag: model_.diagram.Diagram = model.diagrams.by_name(
        COMP_PORT_FILTER_DIAG
    )

    rendered = diag.render(None)

    assert all(
        d.hidden
        for d in rendered
        if d.port and d.styleclass and d.styleclass.startswith("CP_")
    )


def test_fex_exchangeitems_filter_is_applied(
    model_5_2: capellambse.MelodyModel,
) -> None:
    diag: model_.diagram.Diagram = model_5_2.diagrams.by_name(
        EX_ITEMS_FILTER_DIAG
    )

    diag.filters.add(EX_ITEMS_FILTER)
    rendered = diag.render(None, sorted_exchangedItems=False)
    fex_edge = next(
        ex for ex in rendered if ex.styleclass == "FunctionalExchange"
    )

    assert isinstance(fex_edge, diagram.Edge)
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
    model_5_2: capellambse.MelodyModel, sort: bool, expected_label: str
) -> None:
    diag: model_.diagram.Diagram = model_5_2.diagrams.by_name(
        EX_ITEMS_FILTER_DIAG
    )

    diag.filters.add(NAME_AND_EX_ITEMS_FILTER)
    rendered = diag.render(None, sorted_exchangedItems=sort)
    fex_edge = rendered["_yovTvM-ZEeytxdoVf3xHjA"]

    assert isinstance(fex_edge, diagram.Edge)
    assert len(fex_edge.labels) == 1
    assert fex_edge.labels[0].label == expected_label
