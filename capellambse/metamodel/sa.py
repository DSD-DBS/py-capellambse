# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Tools for the System Analysis layer.

This is normally the place to declare data used in the model for e.g.
functions, actors etc. which is best presented in a glossary document.
"""

from __future__ import annotations

import typing as t

import capellambse.model as m

from . import capellacommon, capellacore, cs, fa, interaction
from . import namespaces as ns
from . import oa

if t.TYPE_CHECKING:
    from . import la  # noqa: F401

NS = ns.SA


class SystemAnalysis(cs.ComponentArchitecture):
    """Provides access to the SystemAnalysis layer of the model."""

    component_pkg = m.Containment["SystemComponentPkg"](
        "ownedSystemComponentPkg", (NS, "SystemComponentPkg")
    )
    component_package = m.DeprecatedAccessor["SystemComponentPkg"](
        "component_pkg"
    )
    mission_pkg = m.Containment["MissionPkg"](
        "ownedMissionPkg", (NS, "MissionPkg")
    )
    mission_package = m.DeprecatedAccessor["MissionPkg"]("mission_pkg")

    realized_operational_analysis = m.Allocation["oa.OperationalAnalysis"](
        "ownedOperationalAnalysisRealizations",
        (NS, "OperationalAnalysisRealization"),
        (ns.OA, "OperationalAnalysis"),
        attr="targetElement",
        backattr="sourceElement",
    )

    @property
    def root_component(self) -> SystemComponent:
        return self.component_pkg.by_is_actor(False, single=True)

    @property
    def all_components(self) -> m.ElementList[SystemComponent]:
        return self._model.search((NS, "SystemComponent"), below=self)

    @property
    def all_actors(self) -> m.ElementList[SystemComponent]:
        return self.all_components.by_is_actor(True)

    @property
    def all_missions(self) -> m.ElementList[Mission]:
        return self._model.search((NS, ", aslist=m.ElementList)"), below=self)

    @property
    def all_actor_exchanges(self) -> m.ElementList[fa.ComponentExchange]:
        return self._model.search(
            (ns.FA, "ComponentExchange"), below=self
        ).filter(
            lambda e: (
                (e.source is not None and e.source.is_actor)
                or (e.target is not None and e.target.is_actor)
            )
        )

    @property
    def all_capability_exploitations(
        self,
    ) -> m.ElementList[CapabilityExploitation]:
        return self._model.search((NS, "CapabilityExploitation"), below=self)

    @property
    def all_component_exchanges(self) -> m.ElementList[fa.ComponentExchange]:
        return self._model.search((ns.FA, "ComponentExchange"), below=self)

    diagrams = m.DiagramAccessor(
        "System Analysis", cacheattr="_MelodyModel__diagram_cache"
    )


class SystemFunction(fa.AbstractFunction):
    packages = m.Containment["SystemFunctionPkg"](
        "ownedSystemFunctionPkgs", (NS, "SystemFunctionPkg")
    )
    realized_operational_activities = m.Alias["oa.OperationalActivity"](
        "realized_functions"
    )
    owner = m.Single["SystemComponent"](
        m.Backref((NS, "SystemComponent"), "allocated_functions")
    )
    realizing_logical_functions = m.Backref["la.LogicalFunction"](
        (ns.LA, "LogicalFunction"), "realized_system_functions"
    )
    involved_in = m.Backref["Capability"](
        (NS, "Capability"), "involved_functions"
    )


class SystemFunctionPkg(fa.FunctionPkg):
    """A function package that can hold functions."""

    _xmltag = "ownedFunctionPkg"

    functions = m.Containment["SystemFunction"](
        "ownedSystemFunctions", (NS, "SystemFunction")
    )
    packages = m.Containment["SystemFunctionPkg"](
        "ownedSystemFunctionPkgs", (NS, "SystemFunctionPkg")
    )


class SystemCommunicationHook(capellacore.NamedElement):
    communication = m.Association["SystemCommunication"](
        (NS, "SystemCommunication"), "communication"
    )
    type = m.Association["cs.Component"]((ns.CS, "Component"), "type")


class SystemCommunication(capellacore.Relationship):
    ends = m.Containment["SystemCommunicationHook"](
        "ends", (NS, "SystemCommunicationHook")
    )


class CapabilityInvolvement(capellacore.Involvement):
    pass


class MissionInvolvement(capellacore.Involvement):
    _xmltag = "ownedMissionInvolvements"


class Mission(capellacore.NamedElement, capellacore.InvolverElement):
    """A mission."""

    _xmltag = "ownedMissions"

    involvements = m.Containment["MissionInvolvement"](
        "ownedMissionInvolvements", (NS, "MissionInvolvement")
    )
    incoming_involvements = m.Backref(MissionInvolvement, "target")
    capability_exploitations = m.Containment["CapabilityExploitation"](
        "ownedCapabilityExploitations", (NS, "CapabilityExploitation")
    )
    exploits = m.Allocation["Capability"](
        "ownedCapabilityExploitations",
        (NS, "CapabilityExploitation"),
        (NS, "Capability"),
        attr="capability",
    )


class MissionPkg(capellacore.Structure):
    """A system mission package that can hold missions."""

    _xmltag = "ownedMissionPkg"

    packages = m.Containment["MissionPkg"](
        "ownedMissionPkgs", (NS, "MissionPkg")
    )
    missions = m.Containment["Mission"]("ownedMissions", (NS, "Mission"))


class Capability(interaction.AbstractCapability):
    _xmltag = "ownedCapabilities"

    owned_chains = m.DeprecatedAccessor["fa.FunctionalChain"](
        "functional_chains"
    )
    involvements = m.Containment["CapabilityInvolvement"](
        "ownedCapabilityInvolvements", (NS, "CapabilityInvolvement")
    )
    component_involvements = m.DeprecatedAccessor["CapabilityInvolvement"](
        "involvements"
    )
    involved_components = m.Allocation["SystemComponent"](
        "ownedCapabilityInvolvements",
        (NS, "CapabilityInvolvement"),
        (NS, "SystemComponent"),
        attr="involved",
    )
    incoming_exploitations = m.Backref["CapabilityExploitation"](
        (NS, "CapabilityExploitation"), "capability"
    )


class CapabilityExploitation(capellacore.Relationship):
    _xmltag = "ownedCapabilityExploitations"

    capability = m.Single["Capability"](
        m.Association((NS, "Capability"), "capability")
    )

    @property
    def name(self) -> str:  # type: ignore[override]
        """Return the name."""
        direction = ""
        if self.capability is not None:
            direction = f" to {self.capability.name} ({self.capability.uuid})"

        return f"[{self.__class__.__name__}]{direction}"


class CapabilityPkg(capellacommon.AbstractCapabilityPkg):
    _xmltag = "ownedAbstractCapabilityPkg"

    capabilities = m.Containment["Capability"](
        "ownedCapabilities", (NS, "Capability")
    )
    packages = m.Containment["CapabilityPkg"](
        "ownedCapabilityPkgs", (NS, "CapabilityPkg")
    )


class OperationalAnalysisRealization(cs.ArchitectureAllocation):
    pass


class SystemComponentPkg(cs.ComponentPkg):
    _xmltag = "ownedSystemComponentPkg"

    components = m.Containment["SystemComponent"](
        "ownedSystemComponents", (NS, "SystemComponent")
    )
    packages = m.Containment["SystemComponentPkg"](
        "ownedSystemComponentPkgs", (NS, "SystemComponentPkg")
    )


class SystemComponent(cs.Component, capellacore.InvolvedElement):
    _xmltag = "ownedSystemComponents"

    components = m.Containment["SystemComponent"](
        "ownedSystemComponents", (NS, "SystemComponent")
    )
    packages = m.Containment["SystemComponentPkg"](
        "ownedSystemComponentPkgs", (NS, "SystemComponentPkg")
    )
    is_data_component = m.BoolPOD("dataComponent")
    data_type = m.Single["capellacore.Classifier"](
        m.Association((ns.CAPELLACORE, "Classifier"), "dataType")
    )
    allocated_functions = m.Allocation[SystemFunction](
        "ownedFunctionalAllocation",
        fa.ComponentFunctionalAllocation,
        attr="targetElement",
        backattr="sourceElement",
    )
    realized_entities = m.Alias["oa.Entity"]("realized_components")
    realized_operational_entities = m.Alias["oa.Entity"]("realized_components")
    realizing_logical_components = m.Backref["la.LogicalComponent"](
        (ns.LA, "LogicalComponent"), "realized_components"
    )
