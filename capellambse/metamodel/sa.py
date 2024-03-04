# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import typing as t

from capellambse import model as m

from . import capellacommon, capellacore, cs, fa, interaction
from . import namespaces as ns

if t.TYPE_CHECKING:
    from . import oa

NS = ns.SA


class SystemAnalysis(cs.ComponentArchitecture):
    """The System Analysis layer."""

    component_pkg = m.Single(
        m.Containment["SystemComponentPkg"](
            "ownedSystemComponentPkg", (NS, "SystemComponentPkg")
        ),
        enforce="max",
    )
    mission_pkg = m.Single(
        m.Containment["MissionPkg"]("ownedMissionPkg", (NS, "MissionPkg")),
        enforce="max",
    )
    realized_operational_architecture = m.Single(
        m.Allocation["oa.OperationalAnalysis"](
            (NS, "OperationalAnalysisRealization"),
            (
                "ownedOperationalAnalysisRealizations",
                "targetElement",
                "sourceElement",
            ),
            (ns.OA, "OperationalAnalysis"),
        ),
        enforce="max",
    )


class SystemFunction(fa.AbstractFunction):
    """A system function."""

    packages = m.Containment["SystemFunctionPkg"](
        "ownedSystemFunctionPkgs", (NS, "SystemFunctionPkg")
    )
    functions = m.TypeFilter["SystemFunction"](  # type: ignore[assignment]
        None, (NS, "SystemFunction")
    )
    realized_functions = m.TypeFilter[  # type: ignore[assignment]
        "oa.OperationalActivity"
    ](None, (ns.OA, "OperationalActivity"))
    realized_operational_activities = m.Shortcut["oa.OperationalActivity"](
        "realized_functions"
    )


class SystemFunctionPkg(fa.FunctionPkg):
    """A function package that can hold functions."""

    functions = m.Containment["SystemFunction"](
        "ownedSystemFunctions", (NS, "SystemFunction")
    )
    packages = m.Containment["SystemFunctionPkg"](
        "ownedSystemFunctionPkgs", (NS, "SystemFunctionPkg")
    )


class SystemCommunicationsHook(capellacore.NamedElement):
    communication = m.Single(
        m.Association["SystemCommunication"](
            "communication", (NS, "SystemCommunication")
        ),
        enforce="max",
    )
    type = m.Single(
        m.Association["cs.Component"](None, (ns.CS, "Component")),
        enforce="max",
    )


class SystemCommunication(capellacore.Relationship):
    # FIXME limit to exactly 2
    ends = m.Containment["SystemCommunicationsHook"](
        "ends", (NS, "SystemCommunicationsHook")
    )


class Mission(capellacore.NamedElement, capellacore.InvolverElement):
    """A mission."""

    involved_components = m.Allocation["SystemComponent"](
        (NS, "MissionInvolvement"),
        ("ownedMissionInvolvements", "involved"),
        (NS, "SystemComponent"),
    )
    exploited_capabilities = m.Allocation["Capability"](
        (NS, "CapabilityExploitation"),
        ("ownedCapabilityExploitations", "capability"),
        (NS, "Capability"),
    )


class MissionPkg(capellacore.Structure):
    """A mission package."""

    packages = m.Containment["MissionPkg"](
        "ownedMissionPkgs", (NS, "MissionPkg")
    )
    missions = m.Containment["Mission"]("ownedMissions", (NS, "Mission"))


class Capability(interaction.AbstractCapability):
    """A capability."""

    involved_components = m.Allocation["SystemComponent"](
        (NS, "CapabilityInvolvement"),
        ("ownedCapabilityInvolvements", "involved"),
        (NS, "SystemComponent"),
    )
    realized_capabilities = m.TypeFilter[  # type: ignore[assignment]
        "oa.OperationalCapability"
    ](None, (ns.OA, "OperationalCapability"))

    extended_by = m.Backref["Capability"](
        (ns.INTERACTION, "AbstractCapabilityExtend"), lookup="extended"
    )
    included_by = m.Backref["Capability"](
        (ns.INTERACTION, "AbstractCapabilityInclude"), lookup="included"
    )
    owned_chains = m.Containment["fa.FunctionalChain"](
        "ownedFunctionalChains", (ns.FA, "FunctionalChain")
    )


class CapabilityPkg(capellacommon.AbstractCapabilityPkg):
    """A capability package."""

    capabilities = m.Containment["Capability"](
        "ownedCapabilities", (NS, "Capability")
    )
    packages = m.Containment["CapabilityPkg"](
        "ownedCapabilityPkgs", (NS, "CapabilityPkg")
    )


class SystemComponentPkg(cs.ComponentPkg):
    """A system component package."""

    components = m.Containment["SystemComponent"](
        "ownedSystemComponents", (NS, "SystemComponent")
    )
    packages = m.Containment["SystemComponentPkg"](
        "ownedSystemComponentPkgs", (NS, "SystemComponentPkg")
    )


class SystemComponent(cs.Component, capellacore.InvolvedElement):
    """A system component."""

    is_data_component = m.BoolPOD("dataComponent")

    components = m.Containment["SystemComponent"](
        "ownedSystemComponents", (NS, "SystemComponent")
    )
    packages = m.Containment["SystemComponentPkg"](
        "ownedSystemComponentPkgs", (NS, "SystemComponentPkg")
    )
    data_type = m.Association["capellacore.Classifier"](
        "dataType", (ns.CAPELLACORE, "Classifier")
    )
    realized_components = m.TypeFilter[  # type: ignore[assignment]
        "oa.Entity"
    ](None, (ns.OA, "Entity"))
    realized_entities = m.Shortcut["oa.Entity"]("realized_components")
    allocated_functions = m.TypeFilter[  # type: ignore[assignment]
        "SystemFunction"
    ](None, (NS, "SystemFunction"))
