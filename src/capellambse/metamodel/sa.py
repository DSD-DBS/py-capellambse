# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Tools for the System Analysis layer.

This is normally the place to declare data used in the model for e.g.
functions, actors etc. which is best presented in a glossary document.

.. diagram:: [CDB] SA ORM
"""

import capellambse.model as m

from . import capellacommon, capellacore, cs, fa, interaction, oa
from . import namespaces as ns

NS = ns.SA


class SystemFunction(fa.Function):
    """A system function."""

    realized_operational_activities = m.TypecastAccessor(
        oa.OperationalActivity, "realized_functions"
    )

    owner: m.Accessor


class SystemFunctionPkg(m.ModelElement):
    """A function package that can hold functions."""

    _xmltag = "ownedFunctionPkg"

    functions = m.Containment("ownedSystemFunctions", SystemFunction)
    packages: m.Accessor
    categories = m.DirectProxyAccessor(
        fa.ExchangeCategory, aslist=m.ElementList
    )


class SystemComponent(cs.Component):
    """A system component."""

    _xmltag = "ownedSystemComponents"

    allocated_functions = m.Allocation[SystemFunction](
        "ownedFunctionalAllocation",
        fa.ComponentFunctionalAllocation,
        attr="targetElement",
        backattr="sourceElement",
    )
    realized_entities = m.TypecastAccessor(
        oa.Entity,
        "realized_components",
    )
    realized_operational_entities = m.TypecastAccessor(
        oa.Entity,
        "realized_components",
    )


class SystemComponentPkg(m.ModelElement):
    """A system component package."""

    _xmltag = "ownedSystemComponentPkg"

    components = m.DirectProxyAccessor(SystemComponent, aslist=m.ElementList)
    state_machines = m.DirectProxyAccessor(
        capellacommon.StateMachine, aslist=m.ElementList
    )

    packages: m.Accessor
    exchange_categories = m.DirectProxyAccessor(
        fa.ComponentExchangeCategory, aslist=m.ElementList
    )


class CapabilityInvolvement(interaction.AbstractInvolvement):
    """A CapabilityInvolvement."""


class Capability(m.ModelElement):
    """A capability."""

    _xmltag = "ownedCapabilities"

    extends = m.DirectProxyAccessor(
        interaction.AbstractCapabilityExtend, aslist=m.ElementList
    )
    extended_by = m.Backref(interaction.AbstractCapabilityExtend, "target")
    includes = m.DirectProxyAccessor(
        interaction.AbstractCapabilityInclude, aslist=m.ElementList
    )
    included_by = m.Backref(interaction.AbstractCapabilityInclude, "target")
    generalizes = m.DirectProxyAccessor(
        interaction.AbstractCapabilityGeneralization, aslist=m.ElementList
    )
    generalized_by = m.Backref(
        interaction.AbstractCapabilityGeneralization, "target"
    )
    owned_chains = m.DirectProxyAccessor(
        fa.FunctionalChain, aslist=m.ElementList
    )
    involved_functions = m.Allocation[SystemFunction](
        "ownedAbstractFunctionAbstractCapabilityInvolvements",
        interaction.AbstractFunctionAbstractCapabilityInvolvement,
        attr="involved",
    )
    involved_chains = m.Allocation[fa.FunctionalChain](
        "ownedFunctionalChainAbstractCapabilityInvolvements",
        interaction.FunctionalChainAbstractCapabilityInvolvement,
        attr="involved",
    )
    involved_components = m.Allocation[SystemComponent](
        "ownedCapabilityInvolvements",
        CapabilityInvolvement,
        attr="involved",
        legacy_by_type=True,
    )
    component_involvements = m.DirectProxyAccessor(
        CapabilityInvolvement, aslist=m.ElementList
    )
    realized_capabilities = m.Allocation[oa.OperationalCapability](
        None,  # FIXME fill in tag
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


class MissionInvolvement(interaction.AbstractInvolvement):
    """A MissionInvolvement."""

    _xmltag = "ownedMissionInvolvements"


class CapabilityExploitation(m.ModelElement):
    """A CapabilityExploitation."""

    _xmltag = "ownedCapabilityExploitations"

    capability = m.Single(m.Association(Capability, "capability"))

    @property
    def name(self) -> str:  # type: ignore[override]
        """Return the name."""
        direction = ""
        if self.capability is not None:
            direction = f" to {self.capability.name} ({self.capability.uuid})"

        return f"[{self.__class__.__name__}]{direction}"


class Mission(m.ModelElement):
    """A mission."""

    _xmltag = "ownedMissions"

    involvements = m.DirectProxyAccessor(
        MissionInvolvement, aslist=m.ElementList
    )
    incoming_involvements = m.Backref(MissionInvolvement, "target")
    exploits = m.Allocation[Capability](
        None,  # FIXME fill in tag
        CapabilityExploitation,
        attr="capability",
    )
    exploitations = m.DirectProxyAccessor(
        CapabilityExploitation, aslist=m.ElementList
    )


class MissionPkg(m.ModelElement):
    """A system mission package that can hold missions."""

    _xmltag = "ownedMissionPkg"

    missions = m.DirectProxyAccessor(Mission, aslist=m.ElementList)
    packages: m.Accessor


class CapabilityPkg(m.ModelElement):
    """A capability package that can hold capabilities."""

    _xmltag = "ownedAbstractCapabilityPkg"

    capabilities = m.DirectProxyAccessor(Capability, aslist=m.ElementList)

    packages: m.Accessor


class SystemAnalysis(cs.ComponentArchitecture):
    """Provides access to the SystemAnalysis layer of the model."""

    root_component = m.AttributeMatcherAccessor(
        SystemComponent,
        attributes={"is_actor": False},
        rootelem=SystemComponentPkg,
    )
    root_function = m.DirectProxyAccessor(
        SystemFunction, rootelem=SystemFunctionPkg
    )

    function_package = m.DirectProxyAccessor(SystemFunctionPkg)
    capability_package = m.DirectProxyAccessor(CapabilityPkg)
    component_package = m.DirectProxyAccessor(SystemComponentPkg)
    mission_package = m.DirectProxyAccessor(MissionPkg)

    all_functions = m.DeepProxyAccessor(SystemFunction, aslist=m.ElementList)
    all_capabilities = m.DeepProxyAccessor(Capability, aslist=m.ElementList)
    all_components = m.DeepProxyAccessor(SystemComponent, aslist=m.ElementList)
    all_actors = property(
        lambda self: self._model.search(SystemComponent).by_is_actor(True)
    )
    all_missions = m.DeepProxyAccessor(Mission, aslist=m.ElementList)
    all_functional_chains = property(
        lambda self: self._model.search(fa.FunctionalChain, below=self)
    )

    actor_exchanges = m.DirectProxyAccessor(
        fa.ComponentExchange,
        aslist=m.ElementList,
        rootelem=SystemComponentPkg,
    )
    component_exchanges = m.DeepProxyAccessor(
        fa.ComponentExchange,
        aslist=m.ElementList,
        rootelem=[SystemComponentPkg, SystemComponent],
    )

    all_capability_exploitations = m.DeepProxyAccessor(
        CapabilityExploitation, aslist=m.ElementList
    )
    all_function_exchanges = m.DeepProxyAccessor(
        fa.FunctionalExchange,
        aslist=m.ElementList,
        rootelem=[SystemFunctionPkg, SystemFunction],
    )
    all_component_exchanges = m.DeepProxyAccessor(
        fa.ComponentExchange, aslist=m.ElementList
    )

    diagrams = m.DiagramAccessor(
        "System Analysis", cacheattr="_MelodyModel__diagram_cache"
    )


SystemFunction.owner = m.Single(
    m.Backref(SystemComponent, "allocated_functions")
)
SystemFunction.packages = m.DirectProxyAccessor(
    SystemFunctionPkg, aslist=m.ElementList
)
oa.OperationalCapability.realizing_capabilities = m.Backref(
    Capability, "realized_capabilities"
)
Capability.incoming_exploitations = m.Backref(
    CapabilityExploitation, "capability"
)
oa.Entity.realizing_system_components = m.Backref(
    SystemComponent, "realized_operational_entities"
)
oa.OperationalActivity.realizing_system_functions = m.Backref(
    SystemFunction, "realized_operational_activities"
)
SystemFunction.involved_in = m.Backref(Capability, "involved_functions")
MissionPkg.packages = m.DirectProxyAccessor(MissionPkg, aslist=m.ElementList)
SystemComponent.components = m.DirectProxyAccessor(
    SystemComponent, aslist=m.ElementList
)
SystemComponentPkg.packages = m.DirectProxyAccessor(
    SystemComponentPkg, aslist=m.ElementList
)
SystemFunction.functions = m.DirectProxyAccessor(
    SystemFunction, aslist=m.ElementList
)
SystemFunctionPkg.packages = m.DirectProxyAccessor(
    SystemFunctionPkg, aslist=m.ElementList
)
