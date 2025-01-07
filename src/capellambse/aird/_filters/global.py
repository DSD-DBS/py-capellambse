# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Global filter implementations."""

from __future__ import annotations

import contextlib

import lxml.etree

import capellambse.loader
from capellambse import diagram, helpers

from . import FilterArguments, composite, global_filter

XT_CEX_FEX_ALLOCATION = (
    "org.polarsys.capella.core.data.fa"
    ":ComponentExchangeFunctionalExchangeAllocation"
)
EXCHANGES_WITH_ROLES = frozenset(
    {"Aggregation", "Association", "Composition", "Generalization"}
)


@global_filter("hide.association.labels.filter")
def hide_association_labels(
    args: FilterArguments, flt: lxml.etree._Element
) -> None:
    """Hide names of roles on an exchange."""
    del flt

    classes = EXCHANGES_WITH_ROLES
    for obj in args.target_diagram:
        if not isinstance(obj, diagram.Edge) or obj.styleclass not in classes:
            continue
        for label in obj.labels:
            label.hidden = True


@global_filter("hide.role.names.filter")
def hide_role_names(args: FilterArguments, flt: lxml.etree._Element) -> None:
    """Hide names of roles on an exchange."""
    del flt

    classes = EXCHANGES_WITH_ROLES
    for obj in args.target_diagram:
        if not isinstance(obj, diagram.Edge):
            continue

        if len(obj.labels) > 1 and obj.styleclass in classes:
            obj.labels = obj.labels[:1]


@global_filter("show.functional.exchanges.exchange.items.filter")
def show_name_and_exchangeitems_fex(
    args: FilterArguments, flt: lxml.etree._Element
) -> None:
    """Change FEX labels to show Name and ExchangeItems."""
    del flt
    for obj in args.target_diagram:
        if not isinstance(obj, diagram.Edge):
            continue

        label_box = _get_primary_edge_label(obj, "FunctionalExchange")
        if label_box is None:
            continue

        sort_items = args.params.get("sorted_exchangedItems", False)
        ex_items = _stringify_exchange_items(
            obj, args.melodyloader, sort_items
        )
        if ex_items:
            label_box.label += " " + ex_items


@global_filter("show.exchange.items.filter")
def show_exchangeitems_fex(
    args: FilterArguments, flt: lxml.etree._Element
) -> None:
    """Change FEX labels to only show ExchangeItems."""
    del flt
    for obj in args.target_diagram:
        if not isinstance(obj, diagram.Edge):
            continue

        label_box = _get_primary_edge_label(obj, "FunctionalExchange")
        if label_box is None:
            continue

        sort_items = args.params.get("sorted_exchangedItems", False)
        exchange_items_label = _stringify_exchange_items(
            obj, args.melodyloader, sort_items
        )
        if exchange_items_label:
            label_box.label = exchange_items_label


@global_filter("Show Exchange Items on Component Exchanges")
def show_exchangeitems_cex(
    args: FilterArguments, flt: lxml.etree._Element
) -> None:
    """Change CEX labels to show ExchangeItems."""
    del flt
    for obj in args.target_diagram:
        if not isinstance(obj, diagram.Edge):
            continue
        label_box = _get_primary_edge_label(obj, "ComponentExchange")
        if label_box is None:
            continue

        assert obj.uuid is not None
        elm, items = _get_allocated_exchangeitem_names(
            obj.uuid,
            alloc_attr="convoyedInformations",
            melodyloader=args.melodyloader,
        )
        if elm is None:
            continue
        for fex in elm.iterchildren():
            if helpers.xtype_of(fex) != XT_CEX_FEX_ALLOCATION:
                continue
            items += _get_allocated_exchangeitem_names(
                fex.attrib["targetElement"],
                alloc_attr="exchangedItems",
                melodyloader=args.melodyloader,
            )[1]
        label_box.label = ", ".join(items)


@global_filter(
    "Show Exchange Items on Component Exchange without Functional Exchanges"
)
def show_exchangeitems_cex_no_fex(
    args: FilterArguments, flt: lxml.etree._Element
) -> None:
    """Change CEX labels to show directly allocated ExchangeItems."""
    del flt
    for obj in args.target_diagram:
        if not isinstance(obj, diagram.Edge):
            continue
        label_box = _get_primary_edge_label(obj, "ComponentExchange")
        if label_box is None:
            continue

        assert obj.uuid is not None
        _, items = _get_allocated_exchangeitem_names(
            obj.uuid,
            alloc_attr="convoyedInformations",
            melodyloader=args.melodyloader,
        )
        label_box.label = ", ".join(items)


@global_filter("Hide Component Ports without Exchanges")
def hide_all_empty_ports(
    args: FilterArguments, flt: lxml.etree._Element
) -> None:
    """Hide all ports that do not have edges connected."""
    del flt
    for dgobj in args.target_diagram:
        if isinstance(dgobj, diagram.Box) and dgobj.children:
            composite.hide_empty_ports(
                None, dgobj, classes=composite.PORT_CL_COMPONENT
            )


@global_filter("Hide Allocated Functional Exchanges")
def hide_alloc_func_exch(
    args: FilterArguments, flt: lxml.etree._Element
) -> None:
    """Hide functional exchanges that are allocated to a component exchange."""
    del flt

    component_exchanges = []
    for element in args.target_diagram:
        if not element.hidden and element.styleclass == "ComponentExchange":
            component_exchanges.append(element)

    for cex in component_exchanges:
        assert cex.uuid is not None
        # Find all allocated functional exchanges
        for fex in args.melodyloader[cex.uuid].iterchildren(
            "ownedComponentExchangeFunctionalExchangeAllocations"
        ):
            target = fex.attrib["targetElement"].rsplit("#", 1)[-1]
            with contextlib.suppress(KeyError):
                args.target_diagram[target].hidden = True


def _stringify_exchange_items(
    obj: diagram.DiagramElement,
    melodyloader: capellambse.loader.MelodyLoader,
    sort_items: bool = False,
) -> str:
    assert obj.uuid is not None
    _, items = _get_allocated_exchangeitem_names(
        obj.uuid,
        alloc_attr="exchangedItems",
        melodyloader=melodyloader,
    )
    if items:
        if sort_items:
            items = sorted(items)

        return f"[{', '.join(items)}]"
    return ""


def _get_allocated_exchangeitem_names(
    *try_ids: str,
    alloc_attr: str,
    melodyloader: capellambse.loader.MelodyLoader,
) -> tuple[lxml.etree._Element | None, list[str]]:
    for obj_id in try_ids:
        try:
            elm = melodyloader[obj_id]
        except KeyError:
            pass
        else:
            break
    else:
        return (None, [])

    if elm.tag == "ownedDiagramElements":
        targetlink = next(elm.iterchildren("target"))
        elm = melodyloader[targetlink.attrib["href"]]

    names = []
    for elem in melodyloader.follow_links(
        elm, elm.get(alloc_attr, ""), ignore_broken=True
    ):
        name = elem.get("name")
        if name is not None:
            names.append(name)
    return (elm, names)


def _get_primary_edge_label(
    obj: diagram.Edge, edge_class: str
) -> diagram.Box | None:
    if obj.styleclass != edge_class:
        return None
    if not obj.labels:
        return None
    return obj.labels[0]
