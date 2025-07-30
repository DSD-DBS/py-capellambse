# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Tools for the EPBS layer."""

from __future__ import annotations

import enum

import capellambse.model as m

from . import capellacommon, capellacore, cs
from . import namespaces as ns

NS = ns.EPBS


@m.stringy_enum
@enum.unique
class ConfigurationItemKind(enum.Enum):
    UNSET = "Unset"
    COTSCI = "COTSCI"
    """Commercial Off The Shelves Configuration Item."""
    CSCI = "CSCI"
    """Computer Software Configuration Item."""
    HWCI = "HWCI"
    """Hardware Configuration Item."""
    INTERFACE_CI = "InterfaceCI"
    """Interface Configuration Item."""
    NDICI = "NDICI"
    """Non Developmental Configuration Item."""
    PRIME_ITEM_CI = "PrimeItemCI"
    """Prime Item Configuration Item."""
    SYSTEM_CI = "SystemCI"
    """System Configuration Item."""


class EPBSArchitecturePkg(cs.BlockArchitecturePkg):
    architectures = m.Containment["EPBSArchitecture"](
        "ownedEPBSArchitectures", (NS, "EPBSArchitecture")
    )


class EPBSArchitecture(cs.ComponentArchitecture):
    configuration_item_pkg = m.Single["ConfigurationItemPkg"](
        m.Containment(
            "ownedConfigurationItemPkg", (NS, "ConfigurationItemPkg")
        )
    )
    physical_architecture_realizations = m.Containment[
        "PhysicalArchitectureRealization"
    ](
        "ownedPhysicalArchitectureRealizations",
        (NS, "PhysicalArchitectureRealization"),
    )
    realized_physical_architecture = m.Single(
        m.Allocation["pa.PhysicalArchitecture"](
            "ownedPhysicalArchitectureRealizations",
            (NS, "PhysicalArchitectureRealization"),
            (ns.PA, "PhysicalArchitecture"),
            attr="targetElement",
            backattr="sourceElement",
        )
    )

    @property
    def all_configuration_items(self) -> m.ElementList[ConfigurationItem]:
        return self._model.search((NS, "ConfigurationItem"), below=self)

    diagrams = m.DiagramAccessor(
        "EPBS architecture", cacheattr="_MelodyModel__diagram_cache"
    )


class ConfigurationItemPkg(cs.ComponentPkg):
    configuration_items = m.Containment["ConfigurationItem"](
        "ownedConfigurationItems", (NS, "ConfigurationItem")
    )
    configuration_item_pkgs = m.Containment["ConfigurationItemPkg"](
        "ownedConfigurationItemPkgs", (NS, "ConfigurationItemPkg")
    )


class ConfigurationItem(
    capellacommon.CapabilityRealizationInvolvedElement, cs.Component
):
    identifier = m.StringPOD("itemIdentifier")
    kind = m.EnumPOD("kind", ConfigurationItemKind)
    configuration_items = m.Containment["ConfigurationItem"](
        "ownedConfigurationItems", (NS, "ConfigurationItem")
    )
    configuration_item_pkgs = m.Containment["ConfigurationItemPkg"](
        "ownedConfigurationItemPkgs", (NS, "ConfigurationItemPkg")
    )
    physical_artifact_realizations = m.Containment[
        "PhysicalArtifactRealization"
    ]("ownedPhysicalArtifactRealizations", (NS, "PhysicalArtifactRealization"))
    realized_physical_artifacts = m.Allocation["cs.AbstractPhysicalArtifact"](
        "ownedPhysicalArtifactRealizations",
        (NS, "PhysicalArtifactRealization"),
        (ns.CS, "AbstractPhysicalArtifact"),
        attr="targetElement",
        backattr="sourceElement",
    )


class PhysicalArchitectureRealization(cs.ArchitectureAllocation):
    pass


class PhysicalArtifactRealization(capellacore.Allocation):
    pass


from . import la, pa  # noqa: F401
