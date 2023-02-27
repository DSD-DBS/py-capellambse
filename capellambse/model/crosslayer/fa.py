# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Implementation of objects and relations for Functional Analysis.

Functional Analysis objects inheritance tree (taxonomy):

.. diagram:: [CDB] FunctionalAnalysis [Taxonomy]

Functional Analysis object-relations map (ontology):

.. diagram:: [CDB] FunctionalAnalysis [Ontology]
"""

from __future__ import annotations

import collections.abc as cabc
import typing as t

from .. import common as c
from .. import modeltypes
from . import capellacommon, capellacore, information, interaction

if t.TYPE_CHECKING:
    from . import cs

XT_COMP_EX_FNC_EX_ALLOC = (
    "org.polarsys.capella.core.data.fa"
    ":ComponentExchangeFunctionalExchangeAllocation"
)
XT_COMP_EX_ALLOC = (
    "org.polarsys.capella.core.data.fa:ComponentExchangeAllocation"
)
XT_FCALLOC = "org.polarsys.capella.core.data.fa:ComponentFunctionalAllocation"


@c.xtype_handler(None)
class ControlNode(c.GenericElement):
    """A node with a specific control-kind."""

    _xmltag = "ownedSequenceNodes"

    kind = c.EnumAttributeProperty(
        "kind", modeltypes.ControlNodeKind, writable=False
    )


@c.xtype_handler(None)
class FunctionRealization(c.GenericElement):
    """A realization that links to a function."""

    _xmltag = "ownedFunctionRealizations"


class AbstractExchange(c.GenericElement):
    """Common code for Exchanges."""

    source = c.AttrProxyAccessor(c.GenericElement, "source")
    target = c.AttrProxyAccessor(c.GenericElement, "target")

    source_port = c.DeprecatedAccessor[c.GenericElement]("source")
    target_port = c.DeprecatedAccessor[c.GenericElement]("target")

    def __dir__(self) -> list[str]:
        attrs = list(super().__dir__())
        attrs.remove("source_port")
        attrs.remove("target_port")
        return attrs


@c.xtype_handler(None)
class AbstractFunction(c.GenericElement):
    """An AbstractFunction."""

    available_in_states = c.AttrProxyAccessor(
        capellacommon.State, "availableInStates", aslist=c.ElementList
    )


@c.xtype_handler(None)
class FunctionPort(c.GenericElement):
    """A function port."""

    owner = c.ParentAccessor(c.GenericElement)
    exchanges: c.Accessor
    state_machines = c.DirectProxyAccessor(
        capellacommon.StateMachine, aslist=c.ElementList
    )


@c.xtype_handler(None)
class FunctionInputPort(FunctionPort):
    """A function input port."""

    _xmltag = "inputs"

    exchange_items = c.AttrProxyAccessor(
        information.ExchangeItem, "incomingExchangeItems", aslist=c.ElementList
    )


@c.xtype_handler(None)
class FunctionOutputPort(FunctionPort):
    """A function output port."""

    _xmltag = "outputs"

    exchange_items = c.AttrProxyAccessor(
        information.ExchangeItem, "outgoingExchangeItems", aslist=c.ElementList
    )


class Function(AbstractFunction):
    """Common Code for Function's."""

    is_leaf = property(lambda self: not self.functions)

    inputs = c.DirectProxyAccessor(FunctionInputPort, aslist=c.ElementList)
    outputs = c.DirectProxyAccessor(FunctionOutputPort, aslist=c.ElementList)

    exchanges: c.Accessor["FunctionalExchange"]
    functions: c.Accessor
    packages: c.Accessor
    related_exchanges: c.Accessor["FunctionalExchange"]


@c.xtype_handler(None)
class FunctionalExchange(AbstractExchange):
    """A functional exchange."""

    _xmltag = "ownedFunctionalExchanges"

    exchange_items = c.AttrProxyAccessor(
        information.ExchangeItem, "exchangedItems", aslist=c.ElementList
    )

    @property
    def owner(self) -> ComponentExchange | None:
        return self.allocating_component_exchange


class FunctionalChainInvolvement(interaction.AbstractInvolvement):
    """Abstract class for FunctionalChainInvolvementLink/Function."""

    _xmltag = "ownedFunctionalChainInvolvements"


@c.xtype_handler(None)
class FunctionalChainInvolvementLink(FunctionalChainInvolvement):
    """An element linking a FunctionalChain to an Exchange."""

    exchanged_items = c.AttrProxyAccessor(
        information.ExchangeItem, "exchangedItems", aslist=c.ElementList
    )
    exchange_context = c.AttrProxyAccessor(
        capellacore.Constraint, "exchangeContext"
    )


@c.xtype_handler(None)
class FunctionalChainInvolvementFunction(FunctionalChainInvolvement):
    """An element linking a FunctionalChain to a Function."""


@c.xtype_handler(None)
class FunctionalChain(c.GenericElement):
    """A functional chain."""

    _xmltag = "ownedFunctionalChains"

    involvements = c.DirectProxyAccessor(
        c.GenericElement,
        (FunctionalChainInvolvementFunction, FunctionalChainInvolvementLink),
        aslist=c.ElementList,
    )
    involved_functions = c.LinkAccessor[AbstractFunction](
        None,  # FIXME fill in tag
        FunctionalChainInvolvementFunction,
        aslist=c.MixedElementList,
        attr="involved",
    )
    involved_links = c.LinkAccessor[AbstractExchange](
        None,  # FIXME fill in tag
        FunctionalChainInvolvementLink,
        aslist=c.MixedElementList,
        attr="involved",
    )
    control_nodes = c.DirectProxyAccessor(ControlNode, aslist=c.ElementList)

    @property
    def involved(self) -> c.MixedElementList:
        return self.involved_functions + self.involved_links


@c.xtype_handler(None)
class ComponentPort(c.GenericElement):
    """A component port."""

    _xmltag = "ownedFeatures"

    direction = c.EnumAttributeProperty(
        "orientation", modeltypes.FPortDir, writable=False
    )
    owner = c.ParentAccessor(c.GenericElement)
    exchanges: c.Accessor


@c.xtype_handler(None)
class ComponentExchange(AbstractExchange):
    """A functional component exchange."""

    _xmltag = "ownedComponentExchanges"

    allocated_functional_exchanges = c.LinkAccessor[FunctionalExchange](
        None,  # FIXME fill in tag
        XT_COMP_EX_FNC_EX_ALLOC,
        aslist=c.ElementList,
        attr="targetElement",
    )
    allocated_exchange_items = c.AttrProxyAccessor(
        information.ExchangeItem,
        "convoyedInformations",
        aslist=c.ElementList,
    )
    func_exchanges = c.DeprecatedAccessor[FunctionalExchange](
        "allocated_functional_exchanges"
    )

    @property
    def owner(self) -> cs.PhysicalLink | cs.PhysicalPath | None:
        return self.allocating_physical_link or self.allocating_physical_path

    @property
    def exchange_items(
        self,
    ) -> c.ElementList[information.ExchangeItem]:
        items = c.ElementList(self._model, [], information.ExchangeItem)
        items.extend(self.allocated_exchange_items)
        func_exchanges = self.allocated_functional_exchanges
        assert isinstance(func_exchanges, cabc.Iterable)
        for exchange in func_exchanges:
            items += exchange.exchange_items
        return items

    def __dir__(self) -> list[str]:
        attrs = list(super().__dir__())
        attrs.remove("func_exchanges")
        return attrs


for _port, _exchange in [
    (ComponentPort, ComponentExchange),
    (FunctionInputPort, FunctionalExchange),
    (FunctionOutputPort, FunctionalExchange),
]:
    c.set_accessor(
        _port,
        "exchanges",
        c.ReferenceSearchingAccessor(
            _exchange, "source", "target", aslist=c.ElementList
        ),
    )
del _port, _exchange

c.set_accessor(
    FunctionalExchange,
    "allocating_component_exchange",
    c.ReferenceSearchingAccessor(
        ComponentExchange, "allocated_functional_exchanges"
    ),
)

c.set_accessor(
    capellacommon.State,
    "functions",
    c.ReferenceSearchingAccessor(
        AbstractFunction,
        "availableInStates",
        aslist=c.ElementList,
    ),
)

c.set_accessor(
    Function,
    "exchanges",
    c.DirectProxyAccessor(FunctionalExchange, aslist=c.ElementList),
)
c.set_accessor(
    Function,
    "related_exchanges",
    c.ReferenceSearchingAccessor(
        FunctionalExchange,
        "source.owner",
        "target.owner",
        aslist=c.ElementList,
    ),
)
c.set_accessor(
    information.ExchangeItem,
    "exchanges",
    c.ReferenceSearchingAccessor(
        (ComponentExchange, FunctionalExchange),
        "exchange_items",
        "allocated_exchange_items",
        aslist=c.ElementList,
    ),
)
