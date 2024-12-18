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
from . import namespaces as ns

NS = ns.FA


class ComponentExchangeAllocation(m.ModelElement): ...


class ComponentExchangeFunctionalExchangeAllocation(m.ModelElement): ...


class ComponentFunctionalAllocation(m.ModelElement): ...


class ExchangeCategory(m.ModelElement):
    _xmltag = "ownedCategories"

    exchanges: m.Association[FunctionalExchange]


class ComponentExchangeCategory(m.ModelElement):
    _xmltag = "ownedComponentExchangeCategories"

    exchanges: m.Association[ComponentExchange]


class ControlNode(m.ModelElement):
    """A node with a specific control-kind."""

    _xmltag = "ownedSequenceNodes"

    kind = m.EnumPOD("kind", modeltypes.ControlNodeKind, writable=False)


class FunctionRealization(m.ModelElement):
    """A realization that links to a function."""

    _xmltag = "ownedFunctionRealizations"


class AbstractExchange(m.ModelElement):
    """Common code for Exchanges."""

    source = m.Single(m.Association(m.ModelElement, "source"))
    target = m.Single(m.Association(m.ModelElement, "target"))


class AbstractFunction(m.ModelElement):
    """An AbstractFunction."""

    available_in_states = m.Association(
        capellacommon.State, "availableInStates"
    )
    scenarios = m.Backref[interaction.Scenario](
        (), "related_functions", aslist=m.ElementList
    )


class FunctionPort(m.ModelElement):
    """A function port."""

    owner = m.ParentAccessor()
    exchanges: m.Accessor
    state_machines = m.DirectProxyAccessor(
        capellacommon.StateMachine, aslist=m.ElementList
    )


class FunctionInputPort(FunctionPort):
    """A function input port."""

    _xmltag = "inputs"

    exchange_items = m.Association(
        information.ExchangeItem, "incomingExchangeItems"
    )


class FunctionOutputPort(FunctionPort):
    """A function output port."""

    _xmltag = "outputs"

    exchange_items = m.Association(
        information.ExchangeItem, "outgoingExchangeItems"
    )


class Function(AbstractFunction):
    """Common Code for Function's."""

    _xmltag = "ownedFunctions"

    kind = m.EnumPOD("kind", modeltypes.FunctionKind, default="FUNCTION")

    is_leaf = property(lambda self: not self.functions)

    inputs = m.DirectProxyAccessor(FunctionInputPort, aslist=m.ElementList)
    outputs = m.DirectProxyAccessor(FunctionOutputPort, aslist=m.ElementList)

    exchanges: m.Accessor[m.ElementList[FunctionalExchange]]
    functions: m.Accessor
    packages: m.Accessor
    related_exchanges: m.Accessor[m.ElementList[FunctionalExchange]]

    realized_functions = m.Allocation[AbstractFunction](
        "ownedFunctionRealizations",
        FunctionRealization,
        attr="targetElement",
        legacy_by_type=True,
    )
    realizing_functions = m.Backref[AbstractFunction](
        (), "realized_functions", legacy_by_type=True
    )


class FunctionalExchange(AbstractExchange):
    """A functional exchange."""

    _xmltag = "ownedFunctionalExchanges"

    exchange_items = m.Association(information.ExchangeItem, "exchangedItems")

    realized_functional_exchanges = m.Allocation["FunctionalExchange"](
        "ownedFunctionalExchangeRealizations",
        "org.polarsys.capella.core.data.fa:FunctionalExchangeRealization",
        attr="targetElement",
        backattr="sourceElement",
    )
    realizing_functional_exchanges: m.Accessor[
        m.ElementList[FunctionalExchange]
    ]
    categories = m.Backref(ExchangeCategory, "exchanges")

    @property
    def owner(self) -> ComponentExchange | None:
        return self.allocating_component_exchange


class FunctionalChainInvolvement(interaction.AbstractInvolvement):
    """Abstract class for FunctionalChainInvolvementLink/Function."""

    _xmltag = "ownedFunctionalChainInvolvements"


class FunctionalChainInvolvementLink(FunctionalChainInvolvement):
    """An element linking a FunctionalChain to an Exchange."""

    exchanged_items = m.Association(information.ExchangeItem, "exchangedItems")
    exchange_context = m.Single(
        m.Association(capellacore.Constraint, "exchangeContext")
    )


class FunctionalChainInvolvementFunction(FunctionalChainInvolvement):
    """An element linking a FunctionalChain to a Function."""


class FunctionalChainReference(FunctionalChainInvolvement):
    """An element linking two related functional chains together."""


class FunctionalChain(m.ModelElement):
    """A functional chain."""

    _xmltag = "ownedFunctionalChains"

    kind = m.EnumPOD("kind", modeltypes.FunctionalChainKind, default="SIMPLE")
    precondition = m.Single(
        m.Association(capellacore.Constraint, "preCondition")
    )
    postcondition = m.Single(
        m.Association(capellacore.Constraint, "postCondition")
    )

    involvements = m.DirectProxyAccessor(
        m.ModelElement,
        (
            FunctionalChainInvolvementFunction,
            FunctionalChainInvolvementLink,
            FunctionalChainReference,
        ),
        aslist=m.ElementList,
    )
    involved_functions = m.Allocation[AbstractFunction](
        "ownedFunctionalChainInvolvements",
        FunctionalChainInvolvementFunction,
        attr="involved",
        legacy_by_type=True,
    )
    involved_links = m.Allocation[AbstractExchange](
        "ownedFunctionalChainInvolvements",
        FunctionalChainInvolvementLink,
        attr="involved",
        legacy_by_type=True,
    )
    involved_chains = m.Allocation["FunctionalChain"](
        "ownedFunctionalChainInvolvements",
        "org.polarsys.capella.core.data.fa:FunctionalChainReference",
        attr="involved",
    )
    involving_chains: m.Accessor[m.ElementList[FunctionalChain]]

    realized_chains = m.Allocation["FunctionalChain"](
        "ownedFunctionalChainRealizations",
        "org.polarsys.capella.core.data.fa:FunctionalChainRealization",
        attr="targetElement",
        backattr="sourceElement",
    )
    realizing_chains: m.Accessor[m.ElementList[FunctionalChain]]

    control_nodes = m.DirectProxyAccessor(ControlNode, aslist=m.ElementList)

    @property
    def involved(self) -> m.ElementList[AbstractFunction]:
        return m.ElementList(
            self._model,
            self.involved_functions._elements + self.involved_links._elements,
            legacy_by_type=True,
        )


class ComponentPort(m.ModelElement):
    """A component port."""

    _xmltag = "ownedFeatures"

    direction = m.EnumPOD("orientation", modeltypes.OrientationPortKind)
    owner = m.ParentAccessor()
    exchanges: m.Accessor
    provided_interfaces = m.Association(m.ModelElement, "providedInterfaces")
    required_interfaces = m.Association(m.ModelElement, "requiredInterfaces")


class ComponentExchange(AbstractExchange):
    """A functional component exchange."""

    _xmltag = "ownedComponentExchanges"

    kind = m.EnumPOD("kind", modeltypes.ComponentExchangeKind, default="UNSET")

    allocated_functional_exchanges = m.Allocation[FunctionalExchange](
        "ownedComponentExchangeFunctionalExchangeAllocations",
        ComponentExchangeFunctionalExchangeAllocation,
        attr="targetElement",
    )
    allocated_exchange_items = m.Association(
        information.ExchangeItem, "convoyedInformations"
    )
    categories = m.Backref(
        ComponentExchangeCategory, "exchanges", aslist=m.ElementList
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
    _port.exchanges = m.Backref(_exchange, "source", "target")
del _port, _exchange

ComponentExchange.realized_component_exchanges = m.Allocation[
    ComponentExchange
](
    "ownedComponentExchangeRealizations",
    "org.polarsys.capella.core.data.fa:ComponentExchangeRealization",
    attr="targetElement",
    backattr="sourceElement",
)
ComponentExchange.realizing_component_exchanges = m.Backref(
    ComponentExchange, "realized_component_exchanges"
)
FunctionalExchange.allocating_component_exchange = m.Single(
    m.Backref(ComponentExchange, "allocated_functional_exchanges")
)
FunctionalExchange.realizing_functional_exchanges = m.Backref(
    FunctionalExchange, "realized_functional_exchanges"
)
FunctionalExchange.involving_functional_chains = m.Backref(
    FunctionalChain, "involved_links"
)

FunctionalChain.involving_chains = m.Backref(
    FunctionalChain, "involved_chains"
)
FunctionalChain.realizing_chains = m.Backref(
    FunctionalChain, "realized_chains"
)

Function.exchanges = m.DirectProxyAccessor(
    FunctionalExchange, aslist=m.ElementList
)
Function.related_exchanges = m.Backref(
    FunctionalExchange, "source.owner", "target.owner"
)
information.ExchangeItem.exchanges = m.Backref(
    (ComponentExchange, FunctionalExchange),
    "exchange_items",
    "allocated_exchange_items",
)
ExchangeCategory.exchanges = m.Association(
    FunctionalExchange, "exchanges", aslist=m.ElementList
)
ComponentExchangeCategory.exchanges = m.Association(
    ComponentExchange, "exchanges", aslist=m.ElementList
)


from . import cs
