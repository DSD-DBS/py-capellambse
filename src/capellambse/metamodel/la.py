# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Tools for the Logical Architecture layer.

.. diagram:: [CDB] LA ORM
"""

from __future__ import annotations

from capellambse import model as m

from . import capellacommon, capellacore, cs, fa, interaction, sa


@m.xtype_handler(None)
class LogicalFunction(fa.Function):
    """A logical function on the Logical Architecture layer."""

    realized_system_functions = m.TypecastAccessor(
        sa.SystemFunction, "realized_functions"
    )
    owner: m.Accessor[LogicalComponent]


@m.xtype_handler(None)
class LogicalFunctionPkg(m.ModelElement):
    """A logical function package."""

    _xmltag = "ownedFunctionPkg"

    functions = m.Containment(
        "ownedLogicalFunctions", LogicalFunction, aslist=m.ElementList
    )

    packages: m.Accessor
    categories = m.DirectProxyAccessor(
        fa.ExchangeCategory, aslist=m.ElementList
    )


@m.xtype_handler(None)
class LogicalComponent(cs.Component):
    """A logical component on the Logical Architecture layer."""

    _xmltag = "ownedLogicalComponents"

    allocated_functions = m.Allocation[LogicalFunction](
        "ownedFunctionalAllocation",
        fa.ComponentFunctionalAllocation,
        aslist=m.ElementList,
        attr="targetElement",
        backattr="sourceElement",
    )
    realized_system_components = m.TypecastAccessor(
        sa.SystemComponent,
        "realized_components",
    )

    components: m.Accessor


@m.xtype_handler(None)
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


@m.xtype_handler(None)
class CapabilityRealization(m.ModelElement):
    """A capability."""

    _xmltag = "ownedCapabilityRealizations"

    owned_chains = m.DirectProxyAccessor(
        fa.FunctionalChain, aslist=m.ElementList
    )
    involved_functions = m.Allocation[LogicalFunction](
        "ownedAbstractFunctionAbstractCapabilityInvolvements",
        interaction.AbstractFunctionAbstractCapabilityInvolvement,
        aslist=m.ElementList,
        attr="involved",
    )
    involved_chains = m.Allocation[fa.FunctionalChain](
        "ownedFunctionalChainAbstractCapabilityInvolvements",
        interaction.FunctionalChainAbstractCapabilityInvolvement,
        aslist=m.ElementList,
        attr="involved",
    )
    involved_components = m.Allocation[LogicalComponent](
        "ownedCapabilityRealizationInvolvements",
        capellacommon.CapabilityRealizationInvolvement,
        aslist=m.MixedElementList,
        attr="involved",
    )
    realized_capabilities = m.Allocation[sa.Capability](
        "ownedAbstractCapabilityRealizations",
        interaction.AbstractCapabilityRealization,
        aslist=m.ElementList,
        attr="targetElement",
    )

    postcondition = m.Association(capellacore.Constraint, "postCondition")
    precondition = m.Association(capellacore.Constraint, "preCondition")
    scenarios = m.DirectProxyAccessor(
        interaction.Scenario, aslist=m.ElementList
    )
    states = m.Association(
        capellacommon.State, "availableInStates", aslist=m.ElementList
    )

    packages: m.Accessor


@m.xtype_handler(None)
class CapabilityRealizationPkg(m.ModelElement):
    """A capability package that can hold capabilities."""

    _xmltag = "ownedAbstractCapabilityPkg"

    capabilities = m.DirectProxyAccessor(
        CapabilityRealization, aslist=m.ElementList
    )

    packages: m.Accessor


@m.xtype_handler(None)
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
    all_components = (  # maybe this should exclude .is_actor
        m.DeepProxyAccessor(LogicalComponent, aslist=m.ElementList)
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


m.set_accessor(
    sa.Capability,
    "realizing_capabilities",
    m.Backref(
        CapabilityRealization, "realized_capabilities", aslist=m.ElementList
    ),
)
m.set_accessor(
    sa.SystemComponent,
    "realizing_logical_components",
    m.Backref(LogicalComponent, "realized_components", aslist=m.ElementList),
)
m.set_accessor(
    sa.SystemFunction,
    "realizing_logical_functions",
    m.Backref(
        LogicalFunction, "realized_system_functions", aslist=m.ElementList
    ),
)
m.set_accessor(
    LogicalFunction,
    "owner",
    m.Backref(LogicalComponent, "allocated_functions"),
)
m.set_accessor(
    LogicalFunction,
    "packages",
    m.DirectProxyAccessor(
        LogicalFunctionPkg,
        aslist=m.ElementList,
    ),
)
m.set_accessor(
    LogicalFunction,
    "involved_in",
    m.Backref(
        CapabilityRealization, "involved_functions", aslist=m.ElementList
    ),
)
m.set_self_references(
    (LogicalComponent, "components"),
    (LogicalComponentPkg, "packages"),
    (LogicalFunction, "functions"),
    (LogicalFunctionPkg, "packages"),
)
