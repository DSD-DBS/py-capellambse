# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Tools for the EPBS layer."""

from __future__ import annotations

import enum
import typing as t

import capellambse.model as m

from . import capellacommon, capellacore, cs
from . import namespaces as ns

if t.TYPE_CHECKING:
    from . import la, pa  # noqa: F401

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
    capability_pkg = (  # TODO not in metamodel?
        m.Single["la.CapabilityRealizationPkg"](
            m.Containment(
                "ownedAbstractCapabilityPkg",
                (ns.LA, "CapabilityRealizationPkg"),
            )
        )
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


class ConfigurationItemPkg(cs.ComponentPkg):
    configuration_items = m.Containment["ConfigurationItem"](
        "ownedConfigurationItems", (NS, "ConfigurationItem")
    )
    configuration_item_pkgs = m.Containment["ConfigurationItemPkg"](
        "ownedConfigurationItemPkgs", (NS, "ConfigurationItemPkg")
    )


class ConfigurationItem(
    capellacommon.CapabilityRealizationInvolvedElement,
    cs.Component,
):
    identifier = m.StringPOD("itemIdentifier")
    kind = m.EnumPOD("kind", ConfigurationItemKind)
    configuration_items = m.Containment["ConfigurationItem"](
        "ownedConfigurationItems", (NS, "ConfigurationItem")
    )
    configuration_item_pkgs = m.Containment["ConfigurationItemPkg"](
        "ownedConfigurationItemPkgs", (NS, "ConfigurationItemPkg")
    )
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
