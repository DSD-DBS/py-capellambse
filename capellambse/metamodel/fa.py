# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Implementation of objects and relations for Functional Analysis.

Functional Analysis objects inheritance tree (taxonomy):

.. diagram:: [CDB] FunctionalAnalysis [Taxonomy]

Functional Analysis object-relations map (ontology):

.. diagram:: [CDB] FunctionalAnalysis [Ontology]
"""

from __future__ import annotations

import capellambse.model as m

from . import capellacommon, capellacore, information, interaction, modeltypes


class ComponentExchangeAllocation(m.ModelElement): ...


class ComponentExchangeFunctionalExchangeAllocation(m.ModelElement): ...


class ComponentFunctionalAllocation(m.ModelElement): ...


@m.xtype_handler(None)
class ExchangeCategory(m.ModelElement):
    _xmltag = "ownedCategories"

    exchanges: m.AttrProxyAccessor[FunctionalExchange]


@m.xtype_handler(None)
class ComponentExchangeCategory(m.ModelElement):
    _xmltag = "ownedComponentExchangeCategories"

    exchanges: m.AttrProxyAccessor[ComponentExchange]


@m.xtype_handler(None)
class ControlNode(m.ModelElement):
    """A node with a specific control-kind."""

    _xmltag = "ownedSequenceNodes"

    kind = m.EnumPOD("kind", modeltypes.ControlNodeKind, writable=False)


@m.xtype_handler(None)
class FunctionRealization(m.ModelElement):
    """A realization that links to a function."""

    _xmltag = "ownedFunctionRealizations"


class AbstractExchange(m.ModelElement):
    """Common code for Exchanges."""

    source = m.AttrProxyAccessor(m.ModelElement, "source")
    target = m.AttrProxyAccessor(m.ModelElement, "target")


@m.xtype_handler(None)
class AbstractFunction(m.ModelElement):
    """An AbstractFunction."""

    available_in_states = m.AttrProxyAccessor(
        capellacommon.State, "availableInStates", aslist=m.ElementList
    )


@m.xtype_handler(None)
class FunctionPort(m.ModelElement):
    """A function port."""

    owner = m.ParentAccessor(m.ModelElement)
    exchanges: m.Accessor
    state_machines = m.DirectProxyAccessor(
        capellacommon.StateMachine, aslist=m.ElementList
    )


@m.xtype_handler(None)
class FunctionInputPort(FunctionPort):
    """A function input port."""

    _xmltag = "inputs"

    exchange_items = m.AttrProxyAccessor(
        information.ExchangeItem, "incomingExchangeItems", aslist=m.ElementList
    )


@m.xtype_handler(None)
class FunctionOutputPort(FunctionPort):
    """A function output port."""

    _xmltag = "outputs"

    exchange_items = m.AttrProxyAccessor(
        information.ExchangeItem, "outgoingExchangeItems", aslist=m.ElementList
    )


class Function(AbstractFunction):
    """Common Code for Function's."""

    _xmltag = "ownedFunctions"

    kind = m.EnumPOD("kind", modeltypes.FunctionKind, default="FUNCTION")

    is_leaf = property(lambda self: not self.functions)

    inputs = m.DirectProxyAccessor(FunctionInputPort, aslist=m.ElementList)
    outputs = m.DirectProxyAccessor(FunctionOutputPort, aslist=m.ElementList)

    exchanges: m.Accessor[FunctionalExchange]
    functions: m.Accessor
    packages: m.Accessor
    related_exchanges: m.Accessor[FunctionalExchange]

    realized_functions = m.LinkAccessor[AbstractFunction](
        "ownedFunctionRealizations",
        FunctionRealization,
        aslist=m.MixedElementList,
        attr="targetElement",
    )
    realizing_functions = m.ReferenceSearchingAccessor[AbstractFunction](
        (), "realized_functions", aslist=m.MixedElementList
    )


@m.xtype_handler(None)
class FunctionalExchange(AbstractExchange):
    """A functional exchange."""

    _xmltag = "ownedFunctionalExchanges"

    exchange_items = m.AttrProxyAccessor(
        information.ExchangeItem, "exchangedItems", aslist=m.ElementList
    )

    realized_functional_exchanges = m.LinkAccessor["FunctionalExchange"](
        "ownedFunctionalExchangeRealizations",
        "org.polarsys.capella.core.data.fa:FunctionalExchangeRealization",
        aslist=m.ElementList,
        attr="targetElement",
        backattr="sourceElement",
    )
    realizing_functional_exchanges: m.Accessor[FunctionalExchange]
    categories = m.ReferenceSearchingAccessor(ExchangeCategory, "exchanges")

    @property
    def owner(self) -> ComponentExchange | None:
        return self.allocating_component_exchange


class FunctionalChainInvolvement(interaction.AbstractInvolvement):
    """Abstract class for FunctionalChainInvolvementLink/Function."""

    _xmltag = "ownedFunctionalChainInvolvements"


@m.xtype_handler(None)
class FunctionalChainInvolvementLink(FunctionalChainInvolvement):
    """An element linking a FunctionalChain to an Exchange."""

    exchanged_items = m.AttrProxyAccessor(
        information.ExchangeItem, "exchangedItems", aslist=m.ElementList
    )
    exchange_context = m.AttrProxyAccessor(
        capellacore.Constraint, "exchangeContext"
    )


@m.xtype_handler(None)
class FunctionalChainInvolvementFunction(FunctionalChainInvolvement):
    """An element linking a FunctionalChain to a Function."""


@m.xtype_handler(None)
class FunctionalChainReference(FunctionalChainInvolvement):
    """An element linking two related functional chains together."""


@m.xtype_handler(None)
class FunctionalChain(m.ModelElement):
    """A functional chain."""

    _xmltag = "ownedFunctionalChains"

    kind = m.EnumPOD("kind", modeltypes.FunctionalChainKind, default="SIMPLE")

    involvements = m.DirectProxyAccessor(
        m.ModelElement,
        (
            FunctionalChainInvolvementFunction,
            FunctionalChainInvolvementLink,
            FunctionalChainReference,
        ),
        aslist=m.ElementList,
    )
    involved_functions = m.LinkAccessor[AbstractFunction](
        "ownedFunctionalChainInvolvements",
        FunctionalChainInvolvementFunction,
        aslist=m.MixedElementList,
        attr="involved",
    )
    involved_links = m.LinkAccessor[AbstractExchange](
        "ownedFunctionalChainInvolvements",
        FunctionalChainInvolvementLink,
        aslist=m.MixedElementList,
        attr="involved",
    )
    involved_chains = m.LinkAccessor["FunctionalChain"](
        "ownedFunctionalChainInvolvements",
        "org.polarsys.capella.core.data.fa:FunctionalChainReference",
        attr="involved",
        aslist=m.ElementList,
    )
    involving_chains: m.Accessor[FunctionalChain]

    realized_chains = m.LinkAccessor["FunctionalChain"](
        "ownedFunctionalChainRealizations",
        "org.polarsys.capella.core.data.fa:FunctionalChainRealization",
        attr="targetElement",
        backattr="sourceElement",
        aslist=m.ElementList,
    )
    realizing_chains: m.Accessor[FunctionalChain]

    control_nodes = m.DirectProxyAccessor(ControlNode, aslist=m.ElementList)

    @property
    def involved(self) -> m.MixedElementList:
        return self.involved_functions + self.involved_links


@m.xtype_handler(None)
class ComponentPort(m.ModelElement):
    """A component port."""

    _xmltag = "ownedFeatures"

    direction = m.EnumPOD("orientation", modeltypes.OrientationPortKind)
    owner = m.ParentAccessor(m.ModelElement)
    exchanges: m.Accessor
    provided_interfaces = m.AttrProxyAccessor(
        m.ModelElement, "providedInterfaces", aslist=m.ElementList
    )
    required_interfaces = m.AttrProxyAccessor(
        m.ModelElement, "requiredInterfaces", aslist=m.ElementList
    )


@m.xtype_handler(None)
class ComponentExchange(AbstractExchange):
    """A functional component exchange."""

    _xmltag = "ownedComponentExchanges"

    kind = m.EnumPOD("kind", modeltypes.ComponentExchangeKind, default="UNSET")

    allocated_functional_exchanges = m.LinkAccessor[FunctionalExchange](
        "ownedComponentExchangeFunctionalExchangeAllocations",
        ComponentExchangeFunctionalExchangeAllocation,
        aslist=m.ElementList,
        attr="targetElement",
    )
    allocated_exchange_items = m.AttrProxyAccessor(
        information.ExchangeItem,
        "convoyedInformations",
        aslist=m.ElementList,
    )
    categories = m.ReferenceSearchingAccessor(
        ComponentExchangeCategory, "exchanges"
    )

    @property
    def owner(self) -> cs.PhysicalLink | None:
        return self.allocating_physical_link

    @property
    def exchange_items(self) -> m.ElementList[information.ExchangeItem]:
        return (
            self.allocated_exchange_items
            + self.allocated_functional_exchanges.map("exchange_items")
        )


for _port, _exchange in [
    (ComponentPort, ComponentExchange),
    (FunctionInputPort, FunctionalExchange),
    (FunctionOutputPort, FunctionalExchange),
]:
    m.set_accessor(
        _port,
        "exchanges",
        m.ReferenceSearchingAccessor(
            _exchange, "source", "target", aslist=m.ElementList
        ),
    )
del _port, _exchange

m.set_accessor(
    ComponentExchange,
    "realized_component_exchanges",
    m.LinkAccessor[ComponentExchange](
        "ownedComponentExchangeRealizations",
        "org.polarsys.capella.core.data.fa:ComponentExchangeRealization",
        aslist=m.ElementList,
        attr="targetElement",
        backattr="sourceElement",
    ),
)
m.set_accessor(
    ComponentExchange,
    "realizing_component_exchanges",
    m.ReferenceSearchingAccessor(
        ComponentExchange, "realized_component_exchanges", aslist=m.ElementList
    ),
)
m.set_accessor(
    FunctionalExchange,
    "allocating_component_exchange",
    m.ReferenceSearchingAccessor(
        ComponentExchange, "allocated_functional_exchanges"
    ),
)
m.set_accessor(
    FunctionalExchange,
    "realizing_functional_exchanges",
    m.ReferenceSearchingAccessor(
        FunctionalExchange,
        "realized_functional_exchanges",
        aslist=m.ElementList,
    ),
)
m.set_accessor(
    FunctionalExchange,
    "involving_functional_chains",
    m.ReferenceSearchingAccessor(
        FunctionalChain, "involved_links", aslist=m.ElementList
    ),
)

m.set_accessor(
    FunctionalChain,
    "involving_chains",
    m.ReferenceSearchingAccessor(
        FunctionalChain, "involved_chains", aslist=m.ElementList
    ),
)
m.set_accessor(
    FunctionalChain,
    "realizing_chains",
    m.ReferenceSearchingAccessor(
        FunctionalChain, "realized_chains", aslist=m.ElementList
    ),
)

m.set_accessor(
    Function,
    "exchanges",
    m.DirectProxyAccessor(FunctionalExchange, aslist=m.ElementList),
)
m.set_accessor(
    Function,
    "related_exchanges",
    m.ReferenceSearchingAccessor(
        FunctionalExchange,
        "source.owner",
        "target.owner",
        aslist=m.ElementList,
    ),
)
m.set_accessor(
    information.ExchangeItem,
    "exchanges",
    m.ReferenceSearchingAccessor(
        (ComponentExchange, FunctionalExchange),
        "exchange_items",
        "allocated_exchange_items",
        aslist=m.ElementList,
    ),
)
ExchangeCategory.exchanges = m.AttrProxyAccessor(
    FunctionalExchange, "exchanges", aslist=m.ElementList
)
ComponentExchangeCategory.exchanges = m.AttrProxyAccessor(
    ComponentExchange, "exchanges", aslist=m.ElementList
)


from . import cs
