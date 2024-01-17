# SPDX-FileCopyrightText: Copyright DB InfraGO AG
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
XT_CEX_REAL = "org.polarsys.capella.core.data.fa:ComponentExchangeRealization"
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

    kind = c.EnumAttributeProperty(
        "kind", modeltypes.FunctionKind, default="FUNCTION"
    )

    is_leaf = property(lambda self: not self.functions)

    inputs = c.DirectProxyAccessor(FunctionInputPort, aslist=c.ElementList)
    outputs = c.DirectProxyAccessor(FunctionOutputPort, aslist=c.ElementList)

    exchanges: c.Accessor["FunctionalExchange"]
    functions: c.Accessor
    packages: c.Accessor
    related_exchanges: c.Accessor["FunctionalExchange"]

    realized_functions = c.LinkAccessor[AbstractFunction](
        "ownedFunctionRealizations",
        FunctionRealization,
        aslist=c.MixedElementList,
        attr="targetElement",
    )
    realizing_functions = c.ReferenceSearchingAccessor[AbstractFunction](
        (), "realized_functions", aslist=c.MixedElementList
    )


@c.xtype_handler(None)
class FunctionalExchange(AbstractExchange):
    """A functional exchange."""

    _xmltag = "ownedFunctionalExchanges"

    exchange_items = c.AttrProxyAccessor(
        information.ExchangeItem, "exchangedItems", aslist=c.ElementList
    )

    realized_functional_exchanges = c.LinkAccessor["FunctionalExchange"](
        "ownedFunctionalExchangeRealizations",
        "org.polarsys.capella.core.data.fa:FunctionalExchangeRealization",
        aslist=c.ElementList,
        attr="targetElement",
        backattr="sourceElement",
    )
    realizing_functional_exchanges: c.Accessor["FunctionalExchange"]

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
class FunctionalChainReference(FunctionalChainInvolvement):
    """An element linking two related functional chains together."""


@c.xtype_handler(None)
class FunctionalChain(c.GenericElement):
    """A functional chain."""

    _xmltag = "ownedFunctionalChains"

    kind = c.EnumAttributeProperty(
        "kind", modeltypes.FunctionalChainKind, default="SIMPLE"
    )

    involvements = c.DirectProxyAccessor(
        c.GenericElement,
        (
            FunctionalChainInvolvementFunction,
            FunctionalChainInvolvementLink,
            FunctionalChainReference,
        ),
        aslist=c.ElementList,
    )
    involved_functions = c.LinkAccessor[AbstractFunction](
        "ownedFunctionalChainInvolvements",
        FunctionalChainInvolvementFunction,
        aslist=c.MixedElementList,
        attr="involved",
    )
    involved_links = c.LinkAccessor[AbstractExchange](
        "ownedFunctionalChainInvolvements",
        FunctionalChainInvolvementLink,
        aslist=c.MixedElementList,
        attr="involved",
    )
    involved_chains = c.LinkAccessor["FunctionalChain"](
        "ownedFunctionalChainInvolvements",
        "org.polarsys.capella.core.data.fa:FunctionalChainReference",
        attr="involved",
        aslist=c.ElementList,
    )
    involving_chains: c.Accessor["FunctionalChain"]

    realized_chains = c.LinkAccessor["FunctionalChain"](
        "ownedFunctionalChainRealizations",
        "org.polarsys.capella.core.data.fa:FunctionalChainRealization",
        attr="targetElement",
        backattr="sourceElement",
        aslist=c.ElementList,
    )
    realizing_chains: c.Accessor["FunctionalChain"]

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

    kind = c.EnumAttributeProperty(
        "kind", modeltypes.ComponentExchangeKind, default="UNSET"
    )

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
    def allocating_physical_path(self) -> cs.PhysicalPath | None:
        import warnings

        warnings.warn(
            (
                "allocating_physical_path is deprecated; use"
                " allocating_physical_paths instead, which supports multiple"
                " allocations"
            ),
            DeprecationWarning,
        )

        alloc = self.allocating_physical_paths
        if len(alloc) > 1:
            raise RuntimeError(
                "Multiple allocations; use allocating_physical_paths"
            )
        if not alloc:
            return None
        return alloc[0]

    @property
    def owner(self) -> cs.PhysicalLink | None:
        return self.allocating_physical_link

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
    ComponentExchange,
    "realized_component_exchanges",
    c.LinkAccessor[ComponentExchange](
        "ownedComponentExchangeRealizations",
        XT_CEX_REAL,
        aslist=c.ElementList,
        attr="targetElement",
        backattr="sourceElement",
    ),
)
c.set_accessor(
    ComponentExchange,
    "realizing_component_exchanges",
    c.ReferenceSearchingAccessor(
        ComponentExchange, "realized_component_exchanges", aslist=c.ElementList
    ),
)
c.set_accessor(
    FunctionalExchange,
    "allocating_component_exchange",
    c.ReferenceSearchingAccessor(
        ComponentExchange, "allocated_functional_exchanges"
    ),
)
c.set_accessor(
    FunctionalExchange,
    "realizing_functional_exchanges",
    c.ReferenceSearchingAccessor(
        FunctionalExchange,
        "realized_functional_exchanges",
        aslist=c.ElementList,
    ),
)
c.set_accessor(
    FunctionalExchange,
    "involving_functional_chains",
    c.ReferenceSearchingAccessor(FunctionalChain, "involved_links"),
)

c.set_accessor(
    FunctionalChain,
    "involving_chains",
    c.ReferenceSearchingAccessor(
        FunctionalChain, "involved_chains", aslist=c.ElementList
    ),
)
c.set_accessor(
    FunctionalChain,
    "realizing_chains",
    c.ReferenceSearchingAccessor(
        FunctionalChain, "realized_chains", aslist=c.ElementList
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
