# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import enum

import capellambse.model as m

from . import namespaces as ns

NS = ns.RE


@m.stringy_enum
@enum.unique
class CatalogElementKind(enum.Enum):
    REC = "REC"
    RPL = "RPL"
    REC_RPL = "REC_RPL"
    GROUPING = "GROUPING"


class ReAbstractElement(m.ModelElement, abstract=True):
    pass


class ReNamedElement(ReAbstractElement, abstract=True):
    name = m.StringPOD("name")


class ReDescriptionElement(ReNamedElement, abstract=True):
    description = m.StringPOD("description")


class ReElementContainer(m.ModelElement, abstract=True):
    elements = m.Containment["CatalogElement"](
        "ownedElements", (NS, "CatalogElement")
    )


class CatalogElementPkg(ReNamedElement, ReElementContainer):
    element_pkgs = m.Containment["CatalogElementPkg"](
        "ownedElementPkgs", (NS, "CatalogElementPkg")
    )


class RecCatalog(CatalogElementPkg):
    compliancy_definition_pkg = m.Containment["CompliancyDefinitionPkg"](
        "ownedCompliancyDefinitionPkg", (NS, "CompliancyDefinitionPkg")
    )


class GroupingElementPkg(CatalogElementPkg):
    pass


class CatalogElementLink(ReAbstractElement):
    source = m.Association["CatalogElement"]((NS, "CatalogElement"), "source")
    target = m.Association["m.ModelElement"](
        (ns.MODELLINGCORE, "ModelElement"), "target"
    )
    origin = m.Association["CatalogElementLink"](
        (NS, "CatalogElementLink"), "origin"
    )
    unsynchronized_features = m.StringPOD("unsynchronizedFeatures")
    is_suffixed = m.BoolPOD("suffixed")


class CatalogElement(ReDescriptionElement, ReElementContainer):
    kind = m.EnumPOD("kind", CatalogElementKind)
    author = m.StringPOD("author")
    environment = m.StringPOD("environment")
    suffix = m.StringPOD("suffix")
    purpose = m.StringPOD("purpose")
    is_read_only = m.BoolPOD("readOnly")
    version = m.StringPOD("version")
    tags = m.StringPOD("tags")
    origin = m.Association["CatalogElement"]((NS, "CatalogElement"), "origin")
    current_compliancy = m.Association["CompliancyDefinition"](
        (NS, "CompliancyDefinition"), "currentCompliancy"
    )
    default_replica_compliancy = m.Association["CompliancyDefinition"](
        (NS, "CompliancyDefinition"), "defaultReplicaCompliancy"
    )
    links = m.Containment["CatalogElementLink"](
        "ownedLinks", (NS, "CatalogElementLink")
    )


class CompliancyDefinitionPkg(ReNamedElement):
    definitions = m.Containment["CompliancyDefinition"](
        "ownedDefinitions", (NS, "CompliancyDefinition")
    )


class CompliancyDefinition(ReDescriptionElement):
    pass
