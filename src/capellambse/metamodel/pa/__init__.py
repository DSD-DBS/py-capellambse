# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Tools for the Physical Architecture layer."""

from __future__ import annotations

import enum
import sys
import typing as t

import capellambse.model as m

from .. import capellacommon, cs, fa, information
from .. import namespaces as ns

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

NS = ns.PA


@m.stringy_enum
@enum.unique
class PhysicalComponentKind(enum.Enum):
    """Categories of physical components.

    Allows to categorize a physical component, with respect to real life
    physical entities.
    """

    UNSET = "UNSET"
    """The physical component kind is not specified."""
    HARDWARE = "HARDWARE"
    """The physical component is a hardware resource."""
    HARDWARE_COMPUTER = "HARDWARE_COMPUTER"
    """The physical component is a computing resource."""
    SOFTWARE = "SOFTWARE"
    """The physical component is a software entity."""
    SOFTWARE_DEPLOYMENT_UNIT = "SOFTWARE_DEPLOYMENT_UNIT"
    """The physical component is a software deployment unit."""
    SOFTWARE_EXECUTION_UNIT = "SOFTWARE_EXECUTION_UNIT"
    """The physical component is a software execution unit."""
    SOFTWARE_APPLICATION = "SOFTWARE_APPLICATION"
    """The physical component is a software application."""
    FIRMWARE = "FIRMWARE"
    """The physical component is a firmware part."""
    PERSON = "PERSON"
    """The physical component is a person."""
    FACILITIES = "FACILITIES"
    """The physical component refers to Facilities."""
    DATA = "DATA"
    """The physical component represents a set of data."""
    MATERIALS = "MATERIALS"
    """The physical component represents a bunch of materials."""
    SERVICES = "SERVICES"
    """The physical component represents a set of services."""
    PROCESSES = "PROCESSES"
    """The physical component represents a set of processes."""


@m.stringy_enum
@enum.unique
class PhysicalComponentNature(enum.Enum):
    """The nature of a physical component."""

    UNSET = "UNSET"
    """The physical component nature is not specified."""
    BEHAVIOR = "BEHAVIOR"
    """The physical component nature is behavioral.

    This typically means a piece of software.
    """
    NODE = "NODE"
    """The physical component is a host for behavioral components.

    This typically means a computing resource.
    """


class PhysicalArchitecturePkg(cs.BlockArchitecturePkg):
    packages = m.Containment["PhysicalArchitecturePkg"](
        "ownedPhysicalArchitecturePkgs", (NS, "PhysicalArchitecturePkg")
    )
    architectures = m.Containment["PhysicalArchitecture"](
        "ownedPhysicalArchitectures", (NS, "PhysicalArchitecture")
    )


class PhysicalArchitecture(cs.ComponentArchitecture):
    component_pkg = m.Single["PhysicalComponentPkg"](
        m.Containment(
            "ownedPhysicalComponentPkg", (NS, "PhysicalComponentPkg")
        ),
        enforce=True,
    )
    deployments = m.Containment["cs.AbstractDeploymentLink"](
        "ownedDeployments", (ns.CS, "AbstractDeploymentLink")
    )
    logical_architecture_realizations = m.Containment[
        "LogicalArchitectureRealization"
    ](
        "ownedLogicalArchitectureRealizations",
        (NS, "LogicalArchitectureRealization"),
    )
    realized_logical_architectures = m.Allocation["la.LogicalArchitecture"](
        "ownedLogicalArchitectureRealizations",
        (NS, "LogicalArchitectureRealization"),
        (ns.LA, "LogicalArchitecture"),
        attr="sourceElement",
        backattr="targetElement",
    )

    @property
    def root_function(self) -> PhysicalFunction:
        """Returns the first function in the function_pkg."""
        pkg = self.function_pkg
        assert pkg is not None
        if not pkg.functions:
            raise RuntimeError(f"Package {pkg._short_repr_()} is empty")
        return pkg.functions[0]

    @property
    def root_component(self) -> PhysicalComponent:
        if self.component_pkg is None:
            raise m.BrokenModelError("No root PhysicalComponentPkg found")
        return self.component_pkg.components.by_is_actor(False, single=True)

    @property
    def all_functions(self) -> m.ElementList[PhysicalFunction]:  # type: ignore[override]
        return self._model.search((NS, "PhysicalFunction"), below=self)

    @property
    def all_components(self) -> m.ElementList[PhysicalComponent]:
        return self._model.search((NS, "PhysicalComponent"), below=self)

    @property
    def all_actors(self) -> m.ElementList[PhysicalComponent]:
        return self._model.search((NS, "PhysicalComponent")).by_is_actor(True)

    @property
    def all_function_exchanges(self) -> m.ElementList[fa.FunctionalExchange]:
        return self._model.search((ns.FA, "FunctionalExchange"), below=self)

    @property
    def all_physical_paths(self) -> m.ElementList[cs.PhysicalPath]:
        return self._model.search((ns.CS, "PhysicalPath"), below=self)

    @property
    def all_component_exchanges(self) -> m.ElementList[fa.ComponentExchange]:
        return self._model.search((ns.FA, "ComponentExchange"), below=self)

    @property
    def all_physical_exchanges(self) -> m.ElementList[fa.FunctionalExchange]:
        return self._model.search((ns.FA, "FunctionalExchange"), below=self)

    @property
    def all_physical_links(self) -> m.ElementList[cs.PhysicalLink]:
        return self._model.search((ns.CS, "PhysicalLink"), below=self)

    @property
    def all_functional_chains(self) -> m.ElementList[fa.FunctionalChain]:
        return self._model.search((ns.FA, "FunctionalChain"), below=self)

    diagrams = m.DiagramAccessor(
        "Physical Architecture", cacheattr="_MelodyModel__diagram_cache"
    )

    if not t.TYPE_CHECKING:
        component_package = m.DeprecatedAccessor("component_pkg")


class PhysicalFunction(fa.AbstractFunction):
    """A physical function on the Physical Architecture layer."""

    owner = m.Single["PhysicalComponent"](
        m.Backref((NS, "PhysicalComponent"), "allocated_functions")
    )
    realized_logical_functions = m.Alias["la.LogicalFunction"](
        "realized_functions"
    )
    functions = m.Containment["PhysicalFunction"](
        "ownedPhysicalComponents", (NS, "PhysicalComponent")
    )
    packages = m.Containment["PhysicalFunctionPkg"](
        "ownedPhysicalFunctionPkgs", (NS, "PhysicalFunctionPkg")
    )


class PhysicalFunctionPkg(fa.FunctionPkg):
    """A logical component package."""

    _xmltag = "ownedFunctionPkg"

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
    _xmltag = "ownedPhysicalComponents"

    kind = m.EnumPOD("kind", PhysicalComponentKind)
    nature = m.EnumPOD("nature", PhysicalComponentNature)
    deployment_links = m.Containment["cs.AbstractDeploymentLink"](
        "ownedDeploymentLinks", (ns.CS, "AbstractDeploymentLink")
    )

    @property
    def deployed_components(
        self,
    ) -> m.ElementList[PhysicalComponent]:
        return (
            self.parts.map("deployment_links")
            .map("deployed_element")
            .map("type")
        )

    owned_components = m.Containment["PhysicalComponent"](
        "ownedPhysicalComponents", (NS, "PhysicalComponent")
    )
    component_pkgs = m.Containment["PhysicalComponentPkg"](
        "ownedPhysicalComponentPkgs", (NS, "PhysicalComponentPkg")
    )
    deploying_components = m.Backref["PhysicalComponent"](
        (NS, "PhysicalComponent"), "deployed_components"
    )
    allocated_functions = m.Allocation["PhysicalFunction"](
        None, None, (NS, "PhysicalFunction")
    )

    @property
    @deprecated(
        (
            "PhysicalComponent.components is misleadingly named and deprecated;"
            " use 'related_components' instead"
        ),
        category=FutureWarning,
    )
    def components(self) -> m.ElementList[PhysicalComponent]:
        return self.related_components

    @property
    def related_components(self) -> m.ElementList[PhysicalComponent]:
        components = dict.fromkeys(self.deployed_components._elements)
        components.update(dict.fromkeys(self.owned_components._elements))
        return m.ElementList(
            self._model, list(components.keys()), PhysicalComponent
        )

    if not t.TYPE_CHECKING:
        realized_logical_components = m.DeprecatedAccessor(
            "realized_components"
        )


class PhysicalComponentPkg(cs.ComponentPkg, information.AssociationPkg):
    _xmltag = "ownedPhysicalComponentPkg"

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


class LogicalArchitectureRealization(cs.ArchitectureAllocation):
    pass


class LogicalInterfaceRealization(cs.InterfaceAllocation):
    pass


from .. import la  # noqa: F401
from . import deployment as deployment
