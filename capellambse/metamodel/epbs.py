# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Tools for the EPBS layer."""
from __future__ import annotations

import typing as t

from capellambse import modelv2 as m

from . import capellacommon, cs, modeltypes
from . import namespaces as ns

if t.TYPE_CHECKING:
    from . import la, pa

NS = ns.EPBS


class EPBSArchitecturePkg(cs.BlockArchitecturePkg):
    architectures = m.Containment["EPBSArchitecture"](
        "ownedEPBSArchitectures", (NS, "EPBSArchitecture")
    )


class EPBSArchitecture(cs.ComponentArchitecture):
    configuration_item_pkg = m.Single["ConfigurationItemPkg"](
        m.Containment(
            "ownedConfigurationItemPkg", (NS, "ConfigurationItemPkg")
        ),
        enforce="max",
    )
    capability_pkg = m.Single(
        m.Containment["la.CapabilityRealizationPkg"](
            "ownedAbstractCapabilityPkg", (ns.LA, "CapabilityRealizationPkg")
        ),
        enforce="max",
    )
    realized_physical_architecture = m.Single(
        m.Allocation["pa.PhysicalArchitecture"](
            (NS, "PhysicalArchitectureRealization"),
            (
                "ownedPhysicalArchitectureRealizations",
                "targetElement",
                "sourceElement",
            ),
            (ns.PA, "PhysicalArchitecture"),
        ),
        enforce="max",
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
    kind = m.EnumPOD("kind", modeltypes.ConfigurationItemKind)
    configuration_items = m.Containment["ConfigurationItem"](
        "ownedConfigurationItems", (NS, "ConfigurationItem")
    )
    configuration_item_pkgs = m.Containment["ConfigurationItemPkg"](
        "ownedConfigurationItemPkgs", (NS, "ConfigurationItemPkg")
    )
    realized_physical_artifacts = m.Allocation["cs.AbstractPhysicalArtifact"](
        (NS, "PhysicalArtifactRealization"),
        (
            "ownedPhysicalArtifactRealizations",
            "targetElement",
            "sourceElement",
        ),
        (ns.CS, "AbstractPhysicalArtifact"),
    )
