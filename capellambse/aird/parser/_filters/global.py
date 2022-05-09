# Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Global filter implementations."""
from __future__ import annotations

import lxml.etree

import capellambse.loader
from capellambse import aird, helpers

from . import composite, global_filter

XT_CEX_FEX_ALLOCATION = "org.polarsys.capella.core.data.fa:ComponentExchangeFunctionalExchangeAllocation"


@global_filter("show.functional.exchanges.exchange.items.filter")
def show_exchangeitems_fex(
    target_diagram: aird.Diagram,
    diagram_root: lxml.etree._Element,
    flt: lxml.etree._Element,
    melodyloader: capellambse.loader.MelodyLoader,
) -> None:
    """Change FEX labels to show ExchangeItems."""
    del diagram_root, flt
    for obj in target_diagram:
        if not isinstance(obj, aird.Edge):
            continue
        label = _get_primary_edge_label(obj, "FunctionalExchange")
        if label is None:
            continue

        assert obj.uuid is not None
        _, items = _get_allocated_exchangeitem_names(
            obj.uuid,
            alloc_attr="exchangedItems",
            melodyloader=melodyloader,
        )
        assert isinstance(label.label, str)
        if items:
            if aird.RENDER_PARAMS["sorted_exchangedItems"]:
                items = sorted(items)

            itemss = f" [{', '.join(items)}]"
            if aird.RENDER_PARAMS["keep_primary_name"]:
                label.label += itemss
            else:
                label.label = itemss.lstrip()


@global_filter("Show Exchange Items on Component Exchanges")
def show_exchangeitems_cex(
    target_diagram: aird.Diagram,
    diagram_root: lxml.etree._Element,
    flt: lxml.etree._Element,
    melodyloader: capellambse.loader.MelodyLoader,
) -> None:
    """Change CEX labels to show ExchangeItems."""
    del diagram_root, flt
    for obj in target_diagram:
        if not isinstance(obj, aird.Edge):
            continue
        label = _get_primary_edge_label(obj, "ComponentExchange")
        if label is None:
            continue

        assert obj.uuid is not None
        elm, items = _get_allocated_exchangeitem_names(
            obj.uuid,
            alloc_attr="convoyedInformations",
            melodyloader=melodyloader,
        )
        if elm is None:
            continue
        for fex in elm.iterchildren():
            if helpers.xtype_of(fex) != XT_CEX_FEX_ALLOCATION:
                continue
            items += _get_allocated_exchangeitem_names(
                fex.attrib["targetElement"],
                alloc_attr="exchangedItems",
                melodyloader=melodyloader,
            )[1]
        label.label = ", ".join(items)


@global_filter(
    "Show Exchange Items on Component Exchange without Functional Exchanges"
)
def show_exchangeitems_cex_no_fex(
    target_diagram: aird.Diagram,
    diagram_root: lxml.etree._Element,
    flt: lxml.etree._Element,
    melodyloader: capellambse.loader.MelodyLoader,
) -> None:
    """Change CEX labels to show directly allocated ExchangeItems."""
    del diagram_root, flt
    for obj in target_diagram:
        if not isinstance(obj, aird.Edge):
            continue
        label = _get_primary_edge_label(obj, "ComponentExchange")
        if label is None:
            continue

        assert obj.uuid is not None
        _, items = _get_allocated_exchangeitem_names(
            obj.uuid,
            alloc_attr="convoyedInformations",
            melodyloader=melodyloader,
        )
        label.label = ", ".join(items)


@global_filter("Hide Component Ports without Exchanges")
def hide_all_empty_ports(
    target_diagram: aird.Diagram,
    diagram_root: lxml.etree._Element,
    flt: lxml.etree._Element,
    melodyloader: capellambse.loader.MelodyLoader,
) -> None:
    """Hide all ports that do not have edges connected."""
    del diagram_root, flt, melodyloader
    for dgobj in target_diagram:
        if isinstance(dgobj, aird.Box) and dgobj.children:
            composite.hide_empty_ports(
                None, dgobj, classes=composite.PORT_CL_COMPONENT
            )


@global_filter("Hide Allocated Functional Exchanges")
def hide_alloc_func_exch(
    target_diagram: aird.Diagram,
    diagram_root: lxml.etree._Element,
    flt: lxml.etree._Element,
    melodyloader: capellambse.loader.MelodyLoader,
) -> None:
    """Hide functional exchanges that are allocated to a component exchange."""
    del diagram_root, flt

    component_exchanges = []
    for element in target_diagram:
        if not element.hidden and element.styleclass == "ComponentExchange":
            component_exchanges.append(element)

    for cex in component_exchanges:
        assert cex.uuid is not None
        # Find all allocated functional exchanges
        for fex in melodyloader[cex.uuid].iterchildren(
            "ownedComponentExchangeFunctionalExchangeAllocations"
        ):
            fex = fex.attrib["targetElement"].split("#")[-1]
            try:
                target_diagram[fex].hidden = True
            except KeyError:
                pass  # not in this diagram


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

    # XXX: candidate_name = elm.get("name") This is already what we need!
    if elm.tag == "ownedDiagramElements":
        targetlink = next(elm.iterchildren("target"))
        elm = melodyloader[targetlink.get("href")]

    names = []
    for elem in melodyloader.follow_links(elm, elm.get(alloc_attr, "")):
        if elem is None:
            continue

        name = elem.get("name")
        if name is not None:
            names.append(name)
    return (elm, names)


def _get_primary_edge_label(
    obj: aird.Edge, edge_class: str
) -> aird.Box | None:
    if obj.styleclass != edge_class:
        return None
    if not obj.labels:
        return None
    label = obj.labels[0]
    assert isinstance(label, aird.Box)
    return label
