# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Tools for the System Analysis layer.

This is normally the place to declare data used in the model for e.g.
functions, actors etc. which is best presented in a glossary document.
"""

from __future__ import annotations

import sys
import typing as t

import capellambse.model as m

from . import capellacommon, capellacore, cs, fa, interaction
from . import namespaces as ns

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

NS = ns.SA


class SystemAnalysis(cs.ComponentArchitecture):
    component_pkg = m.Single["SystemComponentPkg"](
        m.Containment("ownedSystemComponentPkg", (NS, "SystemComponentPkg"))
    )
    mission_pkg = m.Containment["MissionPkg"](
        "ownedMissionPkg", (NS, "MissionPkg")
    )
    operational_analysis_realizations = m.Containment[
        "OperationalAnalysisRealization"
    ](
        "ownedOperationalAnalysisRealizations",
        (NS, "OperationalAnalysisRealization"),
    )
    realized_operational_analysis = m.Allocation["oa.OperationalAnalysis"](
        "ownedOperationalAnalysisRealizations",
        (NS, "OperationalAnalysisRealization"),
        (ns.OA, "OperationalAnalysis"),
        attr="targetElement",
        backattr="sourceElement",
    )

    @property
    def root_function(self) -> SystemFunction:
        """Returns the first function in the function_pkg."""
        pkg = self.function_pkg
        assert pkg is not None
        if not pkg.functions:
            raise RuntimeError(f"Package {pkg._short_repr_()} is empty")
        return pkg.functions[0]

    @property
    def root_component(self) -> SystemComponent:
        if self.component_pkg is None:
            raise m.BrokenModelError("No root SystemComponentPkg found")
        return self.component_pkg.components.by_is_actor(False, single=True)

    @property
    def all_components(self) -> m.ElementList[SystemComponent]:
        return self._model.search((NS, "SystemComponent"), below=self)

    @property
    def all_actors(self) -> m.ElementList[SystemComponent]:
        return self.all_components.by_is_actor(True)

    @property
    def all_missions(self) -> m.ElementList[Mission]:
        return self._model.search((NS, "Mission"), below=self)

    @property
    def all_actor_exchanges(self) -> m.ElementList[fa.ComponentExchange]:
        return self._model.search(
            (ns.FA, "ComponentExchange"), below=self
        ).filter(
            lambda e: (
                (
                    e.source is not None
                    and e.source.parent is not None
                    and e.source.parent.is_actor
                )
                or (
                    e.target is not None
                    and e.target.parent is not None
                    and e.target.parent.is_actor
                )
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

    if not t.TYPE_CHECKING:
        component_package = m.DeprecatedAccessor("component_pkg")
        mission_package = m.DeprecatedAccessor("mission_pkg")
        actor_exchanges = m.DeprecatedAccessor("all_actor_exchanges")


class SystemFunction(fa.AbstractFunction):
    packages = m.Containment["SystemFunctionPkg"](
        "ownedSystemFunctionPkgs", (NS, "SystemFunctionPkg")
    )
    realized_operational_activities = m.Alias[
        "m.ElementList[oa.OperationalActivity]"
    ]("realized_functions")
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
    _xmltag = "ownedMissions"

    involvements = m.Containment["MissionInvolvement"](
        "ownedMissionInvolvements", (NS, "MissionInvolvement")
    )
    incoming_involvements = m.Backref["MissionInvolvement"](
        (NS, "MissionInvolvement"), "target"
    )
    capability_exploitations = m.Containment["CapabilityExploitation"](
        "ownedCapabilityExploitations", (NS, "CapabilityExploitation")
    )
    exploits = m.Allocation["Capability"](
        "ownedCapabilityExploitations",
        (NS, "CapabilityExploitation"),
        (NS, "Capability"),
        attr="capability",
    )

    if not t.TYPE_CHECKING:
        exploitations = m.DeprecatedAccessor("capability_exploitations")


class MissionPkg(capellacore.Structure):
    _xmltag = "ownedMissionPkg"

    packages = m.Containment["MissionPkg"](
        "ownedMissionPkgs", (NS, "MissionPkg")
    )
    missions = m.Containment["Mission"]("ownedMissions", (NS, "Mission"))


class Capability(interaction.AbstractCapability):
    _xmltag = "ownedCapabilities"

    involvements = m.Containment["CapabilityInvolvement"](
        "ownedCapabilityInvolvements", (NS, "CapabilityInvolvement")
    )
    involved_components = m.Allocation["SystemComponent"](
        "ownedCapabilityInvolvements",
        (NS, "CapabilityInvolvement"),
        (NS, "SystemComponent"),
        attr="involved",
        legacy_by_type=True,
    )
    incoming_exploitations = m.Backref["CapabilityExploitation"](
        (NS, "CapabilityExploitation"), "capability"
    )

    if not t.TYPE_CHECKING:
        component_involvements = m.DeprecatedAccessor("involvements")
        owned_chains = m.DeprecatedAccessor("functional_chains")


class CapabilityExploitation(capellacore.Relationship):
    _xmltag = "ownedCapabilityExploitations"

    capability = m.Single["Capability"](
        m.Association((NS, "Capability"), "capability")
    )

    @property
    @deprecated("Synthetic names are deprecated", category=FutureWarning)
    def name(self) -> str:
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
    allocated_functions = m.Allocation["SystemFunction"](
        None, None, (NS, "SystemFunction")
    )
    realized_entities = m.Alias["m.ElementList[oa.Entity]"](
        "realized_components"
    )
    realized_operational_entities = m.Alias["m.ElementList[oa.Entity]"](
        "realized_components"
    )
    realizing_logical_components = m.Backref["la.LogicalComponent"](
        (ns.LA, "LogicalComponent"), "realized_components"
    )


from . import la, oa  # noqa: F401
