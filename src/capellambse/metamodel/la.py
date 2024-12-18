# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Tools for the Logical Architecture layer.

.. diagram:: [CDB] LA ORM
"""

from __future__ import annotations

from capellambse import model as m

from . import capellacommon, capellacore, cs, fa, interaction, sa
from . import namespaces as ns

NS = ns.LA


class LogicalFunction(fa.Function):
    """A logical function on the Logical Architecture layer."""

    realized_system_functions = m.TypecastAccessor(
        sa.SystemFunction, "realized_functions"
    )
    owner: m.Single[LogicalComponent]


class LogicalFunctionPkg(m.ModelElement):
    """A logical function package."""

    _xmltag = "ownedFunctionPkg"

    functions = m.Containment("ownedLogicalFunctions", LogicalFunction)

    packages: m.Accessor
    categories = m.DirectProxyAccessor(
        fa.ExchangeCategory, aslist=m.ElementList
    )


class LogicalComponent(cs.Component):
    """A logical component on the Logical Architecture layer."""

    _xmltag = "ownedLogicalComponents"

    allocated_functions = m.Allocation[LogicalFunction](
        "ownedFunctionalAllocation",
        fa.ComponentFunctionalAllocation,
        attr="targetElement",
        backattr="sourceElement",
    )
    realized_system_components = m.TypecastAccessor(
        sa.SystemComponent,
        "realized_components",
    )

    components: m.Accessor


class LogicalComponentPkg(m.ModelElement):
    """A logical component package."""

    _xmltag = "ownedLogicalComponentPkg"

    components = m.DirectProxyAccessor(LogicalComponent, aslist=m.ElementList)
    state_machines = m.DirectProxyAccessor(
        capellacommon.StateMachine, aslist=m.ElementList
    )
    exchanges = m.DirectProxyAccessor(
        fa.ComponentExchange, aslist=m.ElementList
    )

    packages: m.Accessor
    exchange_categories = m.DirectProxyAccessor(
        fa.ComponentExchangeCategory, aslist=m.ElementList
    )


class CapabilityRealization(m.ModelElement):
    """A capability."""

    _xmltag = "ownedCapabilityRealizations"

    owned_chains = m.DirectProxyAccessor(
        fa.FunctionalChain, aslist=m.ElementList
    )
    involved_functions = m.Allocation[LogicalFunction](
        "ownedAbstractFunctionAbstractCapabilityInvolvements",
        interaction.AbstractFunctionAbstractCapabilityInvolvement,
        attr="involved",
    )
    involved_chains = m.Allocation[fa.FunctionalChain](
        "ownedFunctionalChainAbstractCapabilityInvolvements",
        interaction.FunctionalChainAbstractCapabilityInvolvement,
        attr="involved",
    )
    involved_components = m.Allocation[LogicalComponent](
        "ownedCapabilityRealizationInvolvements",
        capellacommon.CapabilityRealizationInvolvement,
        attr="involved",
        legacy_by_type=True,
    )
    realized_capabilities = m.Allocation[sa.Capability](
        "ownedAbstractCapabilityRealizations",
        interaction.AbstractCapabilityRealization,
        attr="targetElement",
    )

    postcondition = m.Single(
        m.Association(capellacore.Constraint, "postCondition")
    )
    precondition = m.Single(
        m.Association(capellacore.Constraint, "preCondition")
    )
    scenarios = m.DirectProxyAccessor(
        interaction.Scenario, aslist=m.ElementList
    )
    states = m.Association(capellacommon.State, "availableInStates")

    packages: m.Accessor


class CapabilityRealizationPkg(m.ModelElement):
    """A capability package that can hold capabilities."""

    _xmltag = "ownedAbstractCapabilityPkg"

    capabilities = m.DirectProxyAccessor(
        CapabilityRealization, aslist=m.ElementList
    )

    packages: m.Accessor


class LogicalArchitecture(cs.ComponentArchitecture):
    """Provides access to the LogicalArchitecture layer of the model."""

    root_component = m.AttributeMatcherAccessor(
        LogicalComponent,
        attributes={"is_actor": False},
        rootelem=LogicalComponentPkg,
    )
    root_function = m.DirectProxyAccessor(
        LogicalFunction, rootelem=LogicalFunctionPkg
    )

    function_package = m.DirectProxyAccessor(LogicalFunctionPkg)
    component_package = m.DirectProxyAccessor(LogicalComponentPkg)
    capability_package = m.DirectProxyAccessor(CapabilityRealizationPkg)

    all_functions = m.DeepProxyAccessor(
        LogicalFunction,
        aslist=m.ElementList,
        rootelem=LogicalFunctionPkg,
    )
    all_capabilities = m.DeepProxyAccessor(
        CapabilityRealization, aslist=m.ElementList
    )
    all_components = (
        m.DeepProxyAccessor(  # maybe this should exclude .is_actor
            LogicalComponent, aslist=m.ElementList
        )
    )
    all_actors = property(
        lambda self: self._model.search(LogicalComponent).by_is_actor(True)
    )
    all_functional_chains = property(
        lambda self: self._model.search(fa.FunctionalChain, below=self)
    )

    actor_exchanges = m.DirectProxyAccessor(
        fa.ComponentExchange,
        aslist=m.ElementList,
        rootelem=LogicalComponentPkg,
    )
    component_exchanges = m.DeepProxyAccessor(
        fa.ComponentExchange,
        aslist=m.ElementList,
        rootelem=[LogicalComponentPkg, LogicalComponent],
    )

    all_function_exchanges = m.DeepProxyAccessor(
        fa.FunctionalExchange,
        aslist=m.ElementList,
        rootelem=[LogicalFunctionPkg, LogicalFunction],
    )
    all_component_exchanges = m.DeepProxyAccessor(
        fa.ComponentExchange, aslist=m.ElementList
    )

    diagrams = m.DiagramAccessor(
        "Logical Architecture", cacheattr="_MelodyModel__diagram_cache"
    )


sa.Capability.realizing_capabilities = m.Backref(
    CapabilityRealization, "realized_capabilities"
)
sa.SystemComponent.realizing_logical_components = m.Backref(
    LogicalComponent, "realized_components"
)
sa.SystemFunction.realizing_logical_functions = m.Backref(
    LogicalFunction, "realized_system_functions"
)
LogicalFunction.owner = m.Single(
    m.Backref(LogicalComponent, "allocated_functions")
)
LogicalFunction.packages = m.DirectProxyAccessor(
    LogicalFunctionPkg, aslist=m.ElementList
)
LogicalFunction.involved_in = m.Backref(
    CapabilityRealization, "involved_functions"
)
LogicalComponent.components = m.DirectProxyAccessor(
    LogicalComponent, aslist=m.ElementList
)
LogicalComponentPkg.packages = m.DirectProxyAccessor(
    LogicalComponentPkg, aslist=m.ElementList
)
LogicalFunction.functions = m.DirectProxyAccessor(
    LogicalFunction, aslist=m.ElementList
)
LogicalFunctionPkg.packages = m.DirectProxyAccessor(
    LogicalFunctionPkg, aslist=m.ElementList
)
