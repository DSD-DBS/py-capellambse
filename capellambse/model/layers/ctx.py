# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
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

    realized_operational_activities = c.LinkAccessor[oa.OperationalActivity](
        None,  # FIXME fill in tag
        fa.FunctionRealization,
        aslist=c.ElementList,
        attr="targetElement",
    )

    owner: c.Accessor


@c.xtype_handler(XT_ARCH)
class SystemFunctionPkg(c.GenericElement):
    """A function package that can hold functions."""

    _xmltag = "ownedFunctionPkg"

    functions = c.DirectProxyAccessor(SystemFunction, aslist=c.ElementList)
    packages: c.Accessor


@c.xtype_handler(XT_ARCH)
class SystemComponent(cs.Component):
    """A system component."""

    _xmltag = "ownedSystemComponents"

    allocated_functions = c.LinkAccessor[SystemFunction](
        "ownedFunctionalAllocation",
        fa.XT_FCALLOC,
        aslist=c.ElementList,
        attr="targetElement",
    )
    realized_operational_entities = c.LinkAccessor[oa.Entity](
        None,  # FIXME fill in tag
        cs.ComponentRealization,
        aslist=c.ElementList,
        attr="targetElement",
    )


@c.xtype_handler(XT_ARCH)
class SystemComponentPkg(c.GenericElement):
    """A system component package."""

    _xmltag = "ownedSystemComponentPkg"

    components = c.DirectProxyAccessor(SystemComponent, aslist=c.ElementList)
    state_machines = c.DirectProxyAccessor(
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

    extends = c.DirectProxyAccessor(
        interaction.AbstractCapabilityExtend, aslist=c.ElementList
    )
    extended_by = c.ReferenceSearchingAccessor(
        interaction.AbstractCapabilityExtend, "target", aslist=c.ElementList
    )
    includes = c.DirectProxyAccessor(
        interaction.AbstractCapabilityInclude, aslist=c.ElementList
    )
    included_by = c.ReferenceSearchingAccessor(
        interaction.AbstractCapabilityInclude, "target", aslist=c.ElementList
    )
    generalizes = c.DirectProxyAccessor(
        interaction.AbstractCapabilityGeneralization, aslist=c.ElementList
    )
    generalized_by = c.ReferenceSearchingAccessor(
        interaction.AbstractCapabilityGeneralization,
        "target",
        aslist=c.ElementList,
    )
    owned_chains = c.DirectProxyAccessor(
        fa.FunctionalChain, aslist=c.ElementList
    )
    involved_functions = c.LinkAccessor[SystemFunction](
        None,  # FIXME fill in tag
        interaction.XT_CAP2ACT,
        aslist=c.ElementList,
        attr="involved",
    )
    involved_chains = c.LinkAccessor[fa.FunctionalChain](
        None,  # FIXME fill in tag
        interaction.XT_CAP2PROC,
        aslist=c.ElementList,
        attr="involved",
    )
    involved_components = c.LinkAccessor[SystemComponent](
        None,  # FIXME fill in tag
        CapabilityInvolvement,
        aslist=c.MixedElementList,
        attr="involved",
    )
    component_involvements = c.DirectProxyAccessor(
        CapabilityInvolvement, aslist=c.ElementList
    )
    realized_capabilities = c.LinkAccessor[oa.OperationalCapability](
        None,  # FIXME fill in tag
        interaction.XT_CAP_REAL,
        aslist=c.ElementList,
        attr="targetElement",
    )

    postcondition = c.AttrProxyAccessor(
        capellacore.Constraint, "postCondition"
    )
    precondition = c.AttrProxyAccessor(capellacore.Constraint, "preCondition")
    scenarios = c.DirectProxyAccessor(
        interaction.Scenario, aslist=c.ElementList
    )
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
    def name(self) -> str:  # type: ignore[override]
        """Return the name."""
        direction = ""
        if self.capability is not None:
            direction = f" to {self.capability.name} ({self.capability.uuid})"

        return f"[{self.__class__.__name__}]{direction}"


@c.xtype_handler(XT_ARCH)
class Mission(c.GenericElement):
    """A mission."""

    _xmltag = "ownedMissions"

    involvements = c.DirectProxyAccessor(
        MissionInvolvement, aslist=c.ElementList
    )
    incoming_involvements = c.ReferenceSearchingAccessor(
        MissionInvolvement, "target", aslist=c.ElementList
    )
    exploits = c.LinkAccessor[Capability](
        None,  # FIXME fill in tag
        CapabilityExploitation,
        aslist=c.ElementList,
        attr="capability",
    )
    exploitations = c.DirectProxyAccessor(
        CapabilityExploitation, aslist=c.ElementList
    )


@c.xtype_handler(XT_ARCH)
class MissionPkg(c.GenericElement):
    """A system mission package that can hold missions."""

    _xmltag = "ownedMissionPkg"

    missions = c.DirectProxyAccessor(Mission, aslist=c.ElementList)
    packages: c.Accessor


@c.xtype_handler(XT_ARCH)
class CapabilityPkg(c.GenericElement):
    """A capability package that can hold capabilities."""

    _xmltag = "ownedAbstractCapabilityPkg"

    capabilities = c.DirectProxyAccessor(Capability, aslist=c.ElementList)

    packages: c.Accessor


@c.xtype_handler(None)
class SystemAnalysis(crosslayer.BaseArchitectureLayer):
    """Provides access to the SystemAnalysis layer of the model."""

    root_component = c.AttributeMatcherAccessor(
        SystemComponent,
        attributes={"is_actor": False},
        rootelem=SystemComponentPkg,
    )
    root_function = c.DirectProxyAccessor(
        SystemFunction, rootelem=SystemFunctionPkg
    )

    function_package = c.DirectProxyAccessor(SystemFunctionPkg)
    capability_package = c.DirectProxyAccessor(CapabilityPkg)
    component_package = c.DirectProxyAccessor(SystemComponentPkg)
    mission_package = c.DirectProxyAccessor(MissionPkg)

    all_functions = c.DeepProxyAccessor(SystemFunction, aslist=c.ElementList)
    all_capabilities = c.DeepProxyAccessor(Capability, aslist=c.ElementList)
    all_components = c.DeepProxyAccessor(SystemComponent, aslist=c.ElementList)
    all_actors = property(
        lambda self: self._model.search(SystemComponent).by_is_actor(True)
    )
    all_missions = c.DeepProxyAccessor(Mission, aslist=c.ElementList)

    actor_exchanges = c.DirectProxyAccessor(
        fa.ComponentExchange,
        aslist=c.ElementList,
        rootelem=SystemComponentPkg,
    )
    component_exchanges = c.DeepProxyAccessor(
        fa.ComponentExchange,
        aslist=c.ElementList,
        rootelem=[SystemComponentPkg, SystemComponent],
    )

    all_capability_exploitations = c.DeepProxyAccessor(
        CapabilityExploitation, aslist=c.ElementList
    )
    all_function_exchanges = c.DeepProxyAccessor(
        fa.FunctionalExchange,
        aslist=c.ElementList,
        rootelem=[SystemFunctionPkg, SystemFunction],
    )
    all_component_exchanges = c.DeepProxyAccessor(
        fa.ComponentExchange, aslist=c.ElementList
    )

    diagrams = diagram.DiagramAccessor(
        "System Analysis", cacheattr="_MelodyModel__diagram_cache"
    )


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
    c.DirectProxyAccessor(SystemFunctionPkg, aslist=c.ElementList),
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
