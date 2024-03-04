# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import typing as t

from capellambse import model as m

from . import capellacommon, cs, fa, information, modeltypes
from . import namespaces as ns

if t.TYPE_CHECKING:
    from . import la

NS = ns.PA


class PhysicalArchitecturePkg(cs.BlockArchitecturePkg):
    packages = m.Containment["PhysicalArchitecturePkg"](
        "ownedPhysicalArchitecturePkgs", (NS, "PhysicalArchitecturePkg")
    )
    architectures = m.Containment["PhysicalArchitecture"](
        "ownedPhysicalArchitectures", (NS, "PhysicalArchitecture")
    )


class PhysicalArchitecture(cs.ComponentArchitecture):
    """The Physical Architecture layer."""

    function_pkg = m.Single["PhysicalFunctionPkg"](
        m.Containment("ownedFunctionPkg", (NS, "PhysicalFunctionPkg")),
        enforce="max",
    )
    capability_pkg = m.Single["la.CapabilityRealizationPkg"](
        m.Containment(
            "ownedAbstractCapabilityPkg", (ns.LA, "CapabilityRealizationPkg")
        ),
        enforce="max",
    )
    component_pkg = m.Single["PhysicalComponentPkg"](
        m.Containment(
            "ownedPhysicalComponentPkg", (NS, "PhysicalComponentPkg")
        ),
        enforce=False,
    )
    deployments = m.Containment["cs.AbstractDeploymentLink"](
        "ownedDeploymentLinks", (ns.CS, "AbstractDeploymentLink")
    )
    realized_logical_architecture = m.Single(
        m.Allocation["la.LogicalArchitecture"](
            (NS, "LogicalArchitectureRealization"),
            (
                "ownedLogicalArchitectureRealizations",
                "targetElement",
                "sourceElement",
            ),
            (ns.LA, "LogicalArchitecture"),
        ),
        enforce=False,
    )

    @property
    def root_component(self) -> PhysicalComponent:
        return self.component_pkg.components.by_is_actor(False, single=True)

    @property
    def root_function(self) -> PhysicalFunction:
        return self.root_component.functions[0]

    @property
    def all_functions(self) -> m.ElementList[PhysicalFunction]:
        return self._model.search((NS, "PhysicalFunction"), below=self)

    @property
    def all_capabilities(self) -> m.ElementList[la.CapabilityRealization]:
        return self._model.search((ns.LA, "CapabilityRealization"), below=self)

    @property
    def all_components(self) -> m.ElementList[PhysicalComponent]:
        all_comps = self._model.search((NS, "PhysicalComponent"), below=self)
        return all_comps.by_is_actor(False)

    @property
    def all_actors(self) -> m.ElementList[PhysicalComponent]:
        all_comps = self._model.search((NS, "PhysicalComponent"), below=self)
        return all_comps.by_is_actor(True)

    @property
    def all_functional_exchanges(self) -> m.ElementList[fa.FunctionalExchange]:
        return self._model.search((ns.FA, "FunctionalExchange"), below=self)

    @property
    def all_physical_paths(self) -> m.ElementList[PhysicalPath]:
        return self._model.search((ns.CS, "PhysicalPath"), below=self)

    @property
    def all_component_exchanges(self) -> m.ElementList[fa.ComponentExchange]:
        return self._model.search(
            (NS, "ComponentExchange"), below=self.component_pkg
        )

    @property
    def all_physical_exchanges(self) -> m.ElementList[PhysicalExchange]:
        return self._model.search(
            (NS, "PhysicalExchange"), below=self.function_pkg
        )

    @property
    def all_physical_links(self) -> m.ElementList[cs.PhysicalLink]:
        return self._model.search((ns.CS, "PhysicalLink"), below=self)

    @property
    def all_functional_chains(self) -> m.ElementList[fa.FunctionalChain]:
        return self._model.search((ns.FA, "FunctionalChain"), below=self)


class PhysicalFunction(fa.AbstractFunction):
    """A physical function."""

    functions = m.Containment["PhysicalFunction"](
        "ownedFunctions", (NS, "PhysicalFunction")
    )
    packages = m.Containment["PhysicalFunctionPkg"](
        "ownedPhysicalFunctionPkgs", (NS, "PhysicalFunctionPkg")
    )


class PhysicalFunctionPkg(fa.FunctionPkg):
    """A package that can hold physical functions."""

    functions = m.Containment["PhysicalFunction"](
        "ownedPhysicalFunctions", (NS, "PhysicalFunction")
    )
    packages = m.Containment["PhysicalFunctionPkg"](
        "ownedPhysicalFunctionPkgs", (NS, "PhysicalFunctionPkg")
    )


class PhysicalComponent(
    cs.AbstractPhysicalArtifact,
    cs.Component,
    capellacommon.CapabilityRealizationInvolvedElement,
    cs.DeployableElement,
    cs.DeploymentTarget,
):
    kind = m.EnumPOD("kind", modeltypes.PhysicalComponentKind)
    nature = m.EnumPOD("nature", modeltypes.PhysicalComponentNature)

    deployment_links = m.Containment["cs.AbstractDeploymentLink"](
        "ownedDeploymentLinks", (ns.CS, "AbstractDeploymentLink")
    )
    components = m.Containment["PhysicalComponent"](
        "ownedPhysicalComponents", (NS, "PhysicalComponent")
    )
    packages = m.Containment["PhysicalComponentPkg"](
        "ownedPhysicalComponentPkgs", (NS, "PhysicalComponentPkg")
    )
    realized_components = m.TypeFilter["la.LogicalComponent"](
        None, (ns.LA, "LogicalComponent")
    )


class PhysicalComponentPkg(m.ModelElement):
    """A package that can hold physical components."""

    components = m.Containment["PhysicalComponent"](
        "ownedPhysicalComponents", (NS, "PhysicalComponent")
    )
    packages = m.Containment["PhysicalComponentPkg"](
        "ownedPhysicalComponentPkgs", (NS, "PhysicalComponentPkg")
    )
    key_parts = m.Containment["information.KeyPart"](
        "ownedKeyParts", (ns.INFORMATION, "KeyPart")
    )
    deployments = m.Containment["cs.AbstractDeploymentLink"](
        "ownedDeployments", (ns.CS, "AbstractDeploymentLink")
    )


class PhysicalNode(PhysicalComponent):
    pass
