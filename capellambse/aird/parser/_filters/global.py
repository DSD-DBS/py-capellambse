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
"""Global filter implementations."""
from __future__ import annotations

import lxml.etree

import capellambse.loader
from capellambse import aird, helpers

from . import composite, global_filter

XT_CEX_FEX_ALLOCATION = "org.polarsys.capella.core.data.fa:ComponentExchangeFunctionalExchangeAllocation"


@global_filter("Show ExchangeItems")
def show_exchangeitems_fex(
    target_diagram: aird.Diagram,
    diagram_root: lxml.etree._Element,
    flt: lxml.etree._Element,
    melodyloader: capellambse.loader.MelodyLoader,
) -> None:
    """Change FEX labels to show ExchangeItems."""
    del diagram_root, flt
    for obj in target_diagram:
        if (
            obj.label
            and obj.styleclass == "FunctionalExchange"
            and isinstance(obj, aird.Edge)
        ):
            assert isinstance(obj, aird.Edge)  # redundant, needed for mypy
            assert obj.uuid is not None
            _, items = _get_allocated_exchangeitem_names(
                obj.uuid,
                alloc_attr="exchangedItems",
                melodyloader=melodyloader,
            )
            if items:
                obj.label.label = f"[{', '.join(sorted(items))}]"
            else:
                obj.label.label = ""


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
        if (
            obj.label
            and obj.styleclass == "ComponentExchange"
            and isinstance(obj, aird.Edge)
        ):
            assert isinstance(obj, aird.Edge)  # redundant, needed for mypy
            assert obj.uuid is not None
            elm, items = _get_allocated_exchangeitem_names(
                obj.uuid,
                alloc_attr="convoyedInformations",
                melodyloader=melodyloader,
            )
            if elm is not None:
                for fex in elm.iterchildren():
                    if helpers.xtype_of(fex) != XT_CEX_FEX_ALLOCATION:
                        continue
                    items += _get_allocated_exchangeitem_names(
                        fex.attrib["targetElement"],
                        alloc_attr="exchangedItems",
                        melodyloader=melodyloader,
                    )[1]
            obj.label.label = ", ".join(items)


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
        if (
            obj.label
            and obj.styleclass == "ComponentExchange"
            and isinstance(obj, aird.Edge)
        ):
            assert isinstance(obj, aird.Edge)  # redundant, needed for mypy
            assert obj.uuid is not None
            _, items = _get_allocated_exchangeitem_names(
                obj.uuid,
                alloc_attr="convoyedInformations",
                melodyloader=melodyloader,
            )
            obj.label.label = ", ".join(items)


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

    exchange_items = elm.get(alloc_attr, "").split()
    names = []
    next_xtype = None
    for item in exchange_items:
        if "#" not in item:
            next_xtype = item
            continue

        elem = melodyloader[f"{next_xtype} {item}" if next_xtype else item]
        name = elem.get("name")
        if name is not None:
            names.append(name)
        next_xtype = None
    return (elm, names)
