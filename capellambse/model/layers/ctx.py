# Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Tools for the System Analysis layer.

This is normally the place to declare data used in the model for e.g.
functions, actors etc. which is best presented in a glossary document.

.. diagram:: [CDB] SA ORM
"""
import operator

from .. import common as c
from .. import crosslayer, diagram
from ..crosslayer import capellacommon, capellacore, cs, fa, interaction
from . import oa

XT_ARCH = "org.polarsys.capella.core.data.ctx:SystemAnalysis"


@c.xtype_handler(XT_ARCH)
class SystemFunction(fa.Function):
    """A system function."""

    _xmltag = "ownedFunctions"

    realized_operational_activities = c.ProxyAccessor(
        oa.OperationalActivity,
        fa.FunctionRealization,
        aslist=c.ElementList,
        follow="targetElement",
    )

    owner: c.Accessor


@c.xtype_handler(XT_ARCH)
class SystemFunctionPkg(c.GenericElement):
    """A function package that can hold functions."""

    _xmltag = "ownedFunctionPkg"

    functions = c.ProxyAccessor(SystemFunction, aslist=c.ElementList)
    packages: c.Accessor


@c.xtype_handler(XT_ARCH)
class SystemComponent(cs.Component):
    """A system component."""

    _xmltag = "ownedSystemComponents"

    allocated_functions = c.ProxyAccessor(
        SystemFunction,
        fa.XT_FCALLOC,
        follow="targetElement",
        aslist=c.ElementList,
    )
    realized_operational_entities = c.ProxyAccessor(
        oa.Entity,
        cs.ComponentRealization,
        aslist=c.ElementList,
        follow="targetElement",
    )


@c.xtype_handler(XT_ARCH)
class SystemComponentPkg(c.GenericElement):
    """A system component package."""

    _xmltag = "ownedSystemComponentPkg"

    components = c.ProxyAccessor(SystemComponent, aslist=c.ElementList)
    state_machines = c.ProxyAccessor(
        capellacommon.StateMachine, aslist=c.ElementList
    )

    packages: c.Accessor


@c.xtype_handler(XT_ARCH)
class CapabilityInvolvement(interaction.AbstractInvolvement):
    """A CapabilityInvolvement."""


@c.xtype_handler(XT_ARCH)
class Capability(c.GenericElement):
    """A capability."""

    _xmltag = "ownedCapabilities"

    extends = c.ProxyAccessor(
        interaction.AbstractCapabilityExtend, aslist=c.ElementList
    )
    includes = c.ProxyAccessor(
        interaction.AbstractCapabilityInclude, aslist=c.ElementList
    )
    generalizes = c.ProxyAccessor(
        interaction.AbstractCapabilityGeneralization, aslist=c.ElementList
    )
    owned_chains = c.ProxyAccessor(fa.FunctionalChain, aslist=c.ElementList)
    involved_functions = c.ProxyAccessor(
        SystemFunction,
        interaction.XT_CAP2ACT,
        aslist=c.ElementList,
        follow="involved",
    )
    involved_chains = c.ProxyAccessor(
        fa.FunctionalChain,
        interaction.XT_CAP2PROC,
        aslist=c.ElementList,
        follow="involved",
    )
    involved_components = c.ProxyAccessor(
        SystemComponent,
        xtypes=CapabilityInvolvement,
        follow="involved",
        aslist=c.MixedElementList,
    )
    component_involvements = c.ProxyAccessor(
        CapabilityInvolvement, aslist=c.ElementList
    )
    realized_capabilities = c.ProxyAccessor(
        oa.OperationalCapability,
        interaction.XT_CAP_REAL,
        follow="targetElement",
        aslist=c.ElementList,
    )

    postcondition = c.AttrProxyAccessor(
        capellacore.Constraint, "postCondition"
    )
    precondition = c.AttrProxyAccessor(capellacore.Constraint, "preCondition")
    scenarios = c.ProxyAccessor(interaction.Scenario, aslist=c.ElementList)
    states = c.AttrProxyAccessor(
        capellacommon.State, "availableInStates", aslist=c.ElementList
    )

    packages: c.Accessor


@c.xtype_handler(XT_ARCH)
class MissionInvolvement(interaction.AbstractInvolvement):
    """A MissionInvolvement."""

    _xmltag = "ownedMissionInvolvements"


@c.xtype_handler(XT_ARCH)
class CapabilityExploitation(c.GenericElement):
    """A CapabilityExploitation."""

    _xmltag = "ownedCapabilityExploitations"

    capability = c.AttrProxyAccessor(Capability, "capability")

    @property
    def name(self) -> str:  # type: ignore
        return f"[{self.__class__.__name__}] to {self.capability.name} ({self.capability.uuid})"


@c.xtype_handler(XT_ARCH)
class Mission(c.GenericElement):
    """A mission."""

    _xmltag = "ownedMissions"

    involvements = c.ProxyAccessor(MissionInvolvement, aslist=c.ElementList)
    exploits = c.ProxyAccessor(
        Capability,
        xtypes=CapabilityExploitation,
        follow="capability",
        aslist=c.ElementList,
    )
    exploitations = c.ProxyAccessor(
        CapabilityExploitation, aslist=c.ElementList
    )


@c.xtype_handler(XT_ARCH)
class MissionPkg(c.GenericElement):
    """A system mission package that can hold missions."""

    _xmltag = "ownedMissionPkg"

    missions = c.ProxyAccessor(Mission, aslist=c.ElementList)
    packages: c.Accessor


@c.xtype_handler(XT_ARCH)
class CapabilityPkg(c.GenericElement):
    """A capability package that can hold capabilities."""

    _xmltag = "ownedAbstractCapabilityPkg"

    capabilities = c.ProxyAccessor(Capability, aslist=c.ElementList)

    packages: c.Accessor


@c.xtype_handler(None)
class SystemAnalysis(crosslayer.BaseArchitectureLayer):
    """Provides access to the SystemAnalysis layer of the model."""

    root_component = c.AttributeMatcherAccessor(
        SystemComponent,
        attributes={"is_actor": False},
        rootelem=SystemComponentPkg,
    )
    root_function = c.ProxyAccessor(SystemFunction, rootelem=SystemFunctionPkg)

    function_package = c.ProxyAccessor(SystemFunctionPkg)
    capability_package = c.ProxyAccessor(CapabilityPkg)
    component_package = c.ProxyAccessor(SystemComponentPkg)
    mission_package = c.ProxyAccessor(MissionPkg)

    all_functions = c.ProxyAccessor(
        SystemFunction, deep=True, aslist=c.ElementList
    )
    all_capabilities = c.ProxyAccessor(
        Capability, deep=True, aslist=c.ElementList
    )
    all_components = c.ProxyAccessor(
        SystemComponent, deep=True, aslist=c.ElementList
    )
    all_actors = property(
        lambda self: self._model.search(SystemComponent).by_is_actor(True)
    )
    all_missions = c.ProxyAccessor(Mission, deep=True, aslist=c.ElementList)

    actor_exchanges = c.ProxyAccessor(
        fa.ComponentExchange,
        aslist=c.ElementList,
        rootelem=SystemComponentPkg,
    )
    component_exchanges = c.ProxyAccessor(
        fa.ComponentExchange,
        aslist=c.ElementList,
        rootelem=[SystemComponentPkg, SystemComponent],
        deep=True,
    )

    all_capability_exploitations = c.ProxyAccessor(
        CapabilityExploitation,
        aslist=c.ElementList,
        deep=True,
    )
    all_function_exchanges = c.ProxyAccessor(
        fa.FunctionalExchange,
        aslist=c.ElementList,
        rootelem=[SystemFunctionPkg, SystemFunction],
        deep=True,
    )
    all_component_exchanges = c.ProxyAccessor(
        fa.ComponentExchange,
        aslist=c.ElementList,
        deep=True,
    )

    diagrams = diagram.DiagramAccessor(
        "System Analysis", cacheattr="_MelodyModel__diagram_cache"
    )  # type: ignore[assignment]


c.set_accessor(
    SystemFunction,
    "owner",
    c.CustomAccessor(
        SystemComponent,
        operator.attrgetter("_model.sa.all_components"),
        matchtransform=operator.attrgetter("allocated_functions"),
    ),
)
c.set_accessor(
    SystemFunction,
    "packages",
    c.ProxyAccessor(
        SystemFunctionPkg,
        aslist=c.ElementList,
    ),
)
c.set_accessor(
    oa.OperationalCapability,
    "realizing_capabilities",
    c.CustomAccessor(
        Capability,
        operator.attrgetter("_model.sa.all_capabilities"),
        matchtransform=operator.attrgetter("realized_capabilities"),
        aslist=c.ElementList,
    ),
)
c.set_accessor(
    Capability,
    "incoming_exploitations",
    c.ReferenceSearchingAccessor(
        CapabilityExploitation, "capability", aslist=c.ElementList
    ),
)
c.set_accessor(
    oa.Entity,
    "realizing_system_components",
    c.CustomAccessor(
        SystemComponent,
        operator.attrgetter("_model.sa.all_components"),
        matchtransform=operator.attrgetter("realized_operational_entities"),
        aslist=c.ElementList,
    ),
)
c.set_accessor(
    oa.OperationalActivity,
    "realizing_system_functions",
    c.CustomAccessor(
        SystemFunction,
        operator.attrgetter("_model.sa.all_functions"),
        matchtransform=operator.attrgetter("realized_operational_activities"),
        aslist=c.ElementList,
    ),
)
c.set_self_references(
    (MissionPkg, "packages"),
    (SystemComponentPkg, "packages"),
    (SystemFunction, "functions"),
    (SystemFunctionPkg, "packages"),
)
