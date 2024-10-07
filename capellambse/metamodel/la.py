# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Tools for the Logical Architecture layer.

.. diagram:: [CDB] LA ORM
"""

from __future__ import annotations

import typing as t

import capellambse.model as m

from . import capellacommon, cs, fa, interaction
from . import namespaces as ns
from . import sa

if t.TYPE_CHECKING:
    from . import pa  # noqa: F401

NS = ns.LA


class LogicalArchitecturePkg(cs.BlockArchitecturePkg):
    architectures = m.Containment["LogicalArchitecture"](
        "ownedLogicalArchitectures", (NS, "LogicalArchitecture")
    )


class LogicalArchitecture(cs.ComponentArchitecture):
    component_pkg = m.Single["LogicalComponentPkg"](
        m.Containment("ownedLogicalComponentPkg", (NS, "LogicalComponentPkg"))
    )
    component_package = m.DeprecatedAccessor["LogicalComponentPkg"](
        "component_pkg"
    )
    realized_system_analysis = m.Allocation["sa.SystemAnalysis"](
        "ownedSystemAnalysisRealizations",
        (NS, "SystemAnalysisRealization"),
        (ns.SA, "SystemAnalysis"),
        attr="targetElement",
        backattr="sourceElement",
    )

    @property
    def root_component(self) -> LogicalComponent:
        assert self.component_pkg is not None
        return self.component_pkg.components.by_is_actor(False, single=True)

    @property
    def all_components(self) -> m.ElementList[LogicalComponent]:
        return self._model.search((NS, "LogicalComponent"), below=self)

    @property
    def all_actors(self) -> m.ElementList[LogicalComponent]:
        return self._model.search(LogicalComponent).by_is_actor(True)

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
    def all_component_exchanges(self) -> m.ElementList[fa.ComponentExchange]:
        return self._model.search((ns.FA, "ComponentExchange"), below=self)

    diagrams = m.DiagramAccessor(
        "Logical Architecture", cacheattr="_MelodyModel__diagram_cache"
    )


class LogicalFunction(fa.AbstractFunction):
    functions = m.Containment["LogicalFunction"](
        "ownedFunctions", (NS, "LogicalFunction")
    )
    packages = m.Containment["LogicalFunctionPkg"](
        "ownedLogicalFunctionPkgs", (NS, "LogicalFunctionPkg")
    )
    realized_system_functions = m.DeprecatedAccessor["sa.SystemFunction"](
        "realized_functions"
    )
    owner = m.Single["LogicalComponent"](
        m.Backref((NS, "LogicalComponent"), "allocated_functions")
    )
    involved_in = m.Backref["CapabilityRealization"](
        (NS, "CapabilityRealization"), "involved_functions"
    )
    realizing_physical_functions = m.Backref["pa.PhysicalFunction"](
        (ns.PA, "PhysicalFunction"), "realized_logical_functions"
    )


class LogicalFunctionPkg(fa.FunctionPkg):
    _xmltag = "ownedFunctionPkg"

    functions = m.Containment["LogicalFunction"](
        "ownedLogicalFunctions", (NS, "LogicalFunction")
    )
    packages = m.Containment["LogicalFunctionPkg"](
        "ownedLogicalFunctionPkgs", (NS, "LogicalFunctionPkg")
    )


class LogicalComponent(
    cs.Component, capellacommon.CapabilityRealizationInvolvedElement
):
    _xmltag = "ownedLogicalComponents"

    components = m.Containment["LogicalComponent"](
        "ownedLogicalComponents", (NS, "LogicalComponent")
    )
    architectures = m.Containment["LogicalArchitecture"](
        "ownedLogicalArchitectures", (NS, "LogicalArchitecture")
    )
    packages = m.Containment["LogicalComponentPkg"](
        "ownedLogicalComponentPkgs", (NS, "LogicalComponentPkg")
    )
    realized_system_components = m.DeprecatedAccessor["sa.SystemComponent"](
        "realized_components"
    )
    realizing_physical_components = m.Backref["pa.PhysicalComponent"](
        (ns.PA, "PhysicalComponent"), "realized_logical_components"
    )


class LogicalComponentPkg(cs.ComponentPkg):
    _xmltag = "ownedLogicalComponentPkg"

    components = m.Containment["LogicalComponent"](
        "ownedLogicalComponents", (NS, "LogicalComponent")
    )
    packages = m.Containment["LogicalComponentPkg"](
        "ownedLogicalComponentPkgs", (NS, "LogicalComponentPkg")
    )


class CapabilityRealization(interaction.AbstractCapability):
    _xmltag = "ownedCapabilityRealizations"

    owned_chains = m.DirectProxyAccessor(
        fa.FunctionalChain, aslist=m.ElementList
    )
    involved_functions = m.Allocation[LogicalFunction](  # TODO
        "ownedAbstractFunctionAbstractCapabilityInvolvements",
        interaction.AbstractFunctionAbstractCapabilityInvolvement,
        attr="involved",
    )
    involved_chains = m.Allocation[fa.FunctionalChain](  # TODO
        "ownedFunctionalChainAbstractCapabilityInvolvements",
        interaction.FunctionalChainAbstractCapabilityInvolvement,
        attr="involved",
    )
    involved_elements = m.Allocation[
        "capellacommon.CapabilityRealizationInvolvedElement"
    ](
        "ownedCapabilityRealizationInvolvements",
        (ns.CAPELLACOMMON, "CapabilityRealizationInvolvement"),
        (ns.CAPELLACOMMON, "CapabilityRealizationInvolvedElement"),
        attr="involved",
    )
    realized_capabilities = m.Allocation[sa.Capability](  # TODO
        "ownedAbstractCapabilityRealizations",
        interaction.AbstractCapabilityRealization,
        attr="targetElement",
    )

    packages: m.Accessor  # TODO


class CapabilityRealizationPkg(capellacommon.AbstractCapabilityPkg):
    """A capability package that can hold capabilities."""

    _xmltag = "ownedAbstractCapabilityPkg"

    capabilities = m.Containment["CapabilityRealization"](
        "ownedCapabilityRealizations", (NS, "CapabilityRealization")
    )
    packages = m.Containment["CapabilityRealizationPkg"](
        "ownedCapabilityRealizationPkgs", (NS, "CapabilityRealizationPkg")
    )


class SystemAnalysisRealization(cs.ArchitectureAllocation):
    pass


class ContextInterfaceRealization(cs.InterfaceAllocation):
    pass
