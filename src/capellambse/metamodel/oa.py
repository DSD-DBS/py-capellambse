# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Tools for the Operational Analysis layer."""

from __future__ import annotations

import sys
import typing as t
import warnings

import capellambse.model as m

from . import (
    activity,
    capellacommon,
    capellacore,
    cs,
    fa,
    information,
    interaction,
    modellingcore,
)
from . import namespaces as ns

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

NS = ns.OA


class OperationalAnalysis(cs.BlockArchitecture):
    """Provides access to the OperationalAnalysis layer of the model."""

    role_pkg = m.Containment["RolePkg"]("ownedRolePkg", (NS, "RolePkg"))
    entity_pkg = m.Single["EntityPkg"](
        m.Containment("ownedEntityPkg", (NS, "EntityPkg"))
    )
    concept_pkg = m.Containment["ConceptPkg"](
        "ownedConceptPkg", (NS, "ConceptPkg")
    )

    activity_pkg = m.Alias["OperationalActivityPkg"]("function_pkg")

    @property
    def all_activities(self) -> m.ElementList[OperationalActivity]:
        return self._model.search((NS, "OperationalActivity"), below=self)

    @property
    def all_processes(self) -> m.ElementList[OperationalProcess]:
        return self._model.search((NS, "OperationalProcess"), below=self)

    @property
    def all_actors(self) -> m.ElementList[Entity]:
        return self._model.search((NS, "Entity")).by_is_actor(True)

    @property
    def all_entities(self) -> m.ElementList[Entity]:
        return self._model.search((NS, "Entity"), below=self)

    @property
    def all_activity_exchanges(self) -> m.ElementList[fa.FunctionalExchange]:
        return self._model.search((ns.FA, "FunctionalExchange"), below=self)

    @property
    def all_entity_exchanges(self) -> m.ElementList[CommunicationMean]:
        return self._model.search((NS, "CommunicationMean"), below=self)

    @property
    def all_operational_processes(self) -> m.ElementList[OperationalProcess]:
        return self._model.search(OperationalProcess, below=self)

    @property
    @deprecated(
        (
            "OperationalActivity.root_activity can only handle a single"
            " OperationalActivity, use .activity_pkg.activities directly instead"
        ),
        category=FutureWarning,
    )
    def root_activity(self) -> OperationalActivity:
        pkg = self.activity_pkg
        if pkg is None:
            raise m.BrokenModelError(
                "OperationalAnalysis has no root ActivityPkg"
            )
        assert isinstance(pkg, OperationalActivityPkg)
        candidates = pkg.activities
        if len(candidates) < 1:
            raise m.BrokenModelError(
                "ActivityPkg does not contain any Activities"
            )
        if len(candidates) > 1:
            raise RuntimeError(
                "Expected 1 object for OperationalAnalysis.root_activity,"
                f" got {len(candidates)}"
            )
        return candidates[0]

    @property
    @deprecated(
        (
            "OperationalActivity.root_entity can only handle a single"
            " Entity, use .entity_pkg.entities directly instead"
        ),
        category=FutureWarning,
    )
    def root_entity(self) -> Entity:
        pkg = self.entity_pkg
        if pkg is None:
            raise m.BrokenModelError(
                "OperationalAnalysis has no root EntityPkg"
            )
        candidates = pkg.entities
        if len(candidates) < 1:
            raise m.BrokenModelError("Root EntityPkg is empty")
        if len(candidates) > 1:
            raise RuntimeError(
                "Expected 1 object for OperationalAnalysis.root_entity,"
                f" got {len(candidates)}"
            )
        return candidates[0]

    diagrams = m.DiagramAccessor(
        "Operational Analysis", cacheattr="_MelodyModel__diagram_cache"
    )

    if not t.TYPE_CHECKING:
        entity_package = m.DeprecatedAccessor("entity_pkg")
        activity_package = m.DeprecatedAccessor("activity_pkg")
        capability_package = m.DeprecatedAccessor("capability_pkg")


class OperationalScenario(capellacore.NamedElement, abstract=True):
    context = m.StringPOD("context")
    objective = m.StringPOD("objective")


class OperationalActivityPkg(fa.FunctionPkg):
    _xmltag = "ownedFunctionPkg"

    activities = m.Containment["OperationalActivity"](
        "ownedOperationalActivities", (NS, "OperationalActivity")
    )
    packages = m.Containment["OperationalActivityPkg"](
        "ownedOperationalActivityPkgs", (NS, "OperationalActivityPkg")
    )
    owner = m.Single["Entity"](m.Backref((NS, "Entity"), "activities"))


class OperationalActivity(fa.AbstractFunction):
    _xmltag = "ownedOperationalActivities"

    packages = m.Containment["OperationalActivityPkg"](
        "ownedOperationalActivityPkgs", (NS, "OperationalActivityPkg")
    )
    activities = m.Alias["m.ElementList[OperationalActivity]"]("functions")
    inputs = m.Backref["fa.FunctionalExchange"](  # type: ignore[assignment]
        (ns.FA, "FunctionalExchange"), "target"
    )
    outputs = m.Backref["fa.FunctionalExchange"](  # type: ignore[assignment]
        (ns.FA, "FunctionalExchange"), "source"
    )
    realizing_system_functions = m.Backref["sa.SystemFunction"](
        (ns.SA, "SystemFunction"), "realized_operational_activities"
    )

    owner = m.Single["Entity"](m.Backref((NS, "Entity"), "activities"))

    related_exchanges = m.Backref[fa.FunctionalExchange](
        (ns.FA, "FunctionalExchange"), "source", "target"
    )


class OperationalProcess(fa.FunctionalChain):
    pass


class Swimlane(capellacore.NamedElement, activity.ActivityPartition):
    pass


class OperationalCapabilityPkg(capellacommon.AbstractCapabilityPkg):
    _xmltag = "ownedAbstractCapabilityPkg"

    capabilities = m.Containment["OperationalCapability"](
        "ownedOperationalCapabilities", (NS, "OperationalCapability")
    )
    packages = m.Containment["OperationalCapabilityPkg"](
        "ownedOperationalCapabilityPkgs", (NS, "OperationalCapabilityPkg")
    )
    capability_configurations = m.Containment["CapabilityConfiguration"](
        "ownedCapabilityConfigurations", (NS, "CapabilityConfiguration")
    )
    concept_compliances = m.Containment["ConceptCompliance"](
        "ownedConceptCompliances", (NS, "ConceptCompliance")
    )
    complies_with_concepts = m.Allocation["Concept"](
        "ownedConceptCompliances",
        (NS, "ConceptCompliance"),
        (NS, "Concept"),
        attr="complyWithConcept",
        backattr="compliantCapability",
    )


class OperationalCapability(
    interaction.AbstractCapability, capellacore.Namespace
):
    """A capability in the OperationalAnalysis layer."""

    _xmltag = "ownedOperationalCapabilities"

    compliances = m.Association["ConceptCompliance"](
        (NS, "ConceptCompliance"), "compliances"
    )
    configurations = m.Association["CapabilityConfiguration"](
        (NS, "CapabilityConfiguration"), "configurations"
    )
    entity_involvements = m.Containment[
        "EntityOperationalCapabilityInvolvement"
    ](
        "ownedEntityOperationalCapabilityInvolvements",
        (NS, "EntityOperationalCapabilityInvolvement"),
    )
    involved_entities = m.Allocation["Entity"](
        "ownedEntityOperationalCapabilityInvolvements",
        (NS, "EntityOperationalCapabilityInvolvement"),
        (NS, "Entity"),
        attr="involved",
        legacy_by_type=True,
    )
    involved_activities = m.Alias["m.ElementList[OperationalActivity]"](
        "involved_functions"
    )
    involved_processes = m.Alias["m.ElementList[OperationalProcess]"](
        "involved_chains"
    )
    owned_processes = m.Alias["m.ElementList[OperationalProcess]"](
        "functional_chains"
    )


class ActivityAllocation(capellacore.Allocation):
    pass


class RolePkg(capellacore.Structure):
    packages = m.Containment["RolePkg"]("ownedRolePkgs", (NS, "RolePkg"))
    roles = m.Containment["Role"]("ownedRoles", (NS, "Role"))


class Role(information.AbstractInstance):
    assembly_usages = m.Containment["RoleAssemblyUsage"](
        "ownedRoleAssemblyUsages", (NS, "RoleAssemblyUsage")
    )
    activity_allocations = m.Containment["ActivityAllocation"](
        "ownedActivityAllocations", (NS, "ActivityAllocation")
    )


class RoleAssemblyUsage(capellacore.NamedElement):
    child = m.Association["Role"]((NS, "Role"), "child")


class RoleAllocation(capellacore.Allocation):
    pass


class EntityPkg(cs.ComponentPkg):
    _xmltag = "ownedEntityPkg"

    entities = m.Containment["Entity"]("ownedEntities", (NS, "Entity"))
    packages = m.Containment["EntityPkg"]("ownedEntityPkgs", (NS, "EntityPkg"))
    locations = m.Containment["Location"]("ownedLocations", (NS, "Location"))
    communication_means = m.Alias["m.ElementList[CommunicationMean]"](
        "exchanges"
    )


class AbstractConceptItem(cs.Component, abstract=True):
    composing_links = m.Association["ItemInConcept"](
        (NS, "ItemInConcept"), "composingLinks"
    )


class Entity(
    AbstractConceptItem,
    modellingcore.InformationsExchanger,
    capellacore.InvolvedElement,
):
    """An Entity in the OperationalAnalysis layer."""

    _xmltag = "ownedEntities"

    organisational_unit_memberships = m.Association[
        "OrganisationalUnitComposition"
    ]((NS, "OrganisationalUnitComposition"), "organisationalUnitMemberships")
    actual_location = m.Association["Location"](
        (NS, "Location"), "actualLocation"
    )
    entities = m.Containment["Entity"]("ownedEntities", (NS, "Entity"))
    communication_means = m.Containment["CommunicationMean"](
        "ownedCommunicationMeans", (NS, "CommunicationMean")
    )
    exchanges = m.Alias["m.ElementList[CommunicationMean]"](
        "communication_means"
    )
    activities = m.Allocation["OperationalActivity"](
        "ownedFunctionalAllocation",
        (ns.FA, "ComponentFunctionalAllocation"),
        (NS, "OperationalActivity"),
        attr="targetElement",
        backattr="sourceElement",
    )
    capabilities = m.Backref["OperationalCapability"](
        (NS, "OperationalCapability"), "involved_entities"
    )
    related_exchanges = m.Backref["CommunicationMean"](
        (NS, "CommunicationMean"), "source", "target"
    )
    realizing_system_components = m.Backref["sa.SystemComponent"](
        (ns.SA, "SystemComponent"), "realized_operational_entities"
    )

    @property
    def inputs(self) -> m.ElementList[CommunicationMean]:
        return self._model.search((NS, "CommunicationMean")).by_target(self)

    @property
    def outputs(self) -> m.ElementList[CommunicationMean]:
        return self._model.search((NS, "CommunicationMean")).by_source(self)


class ConceptPkg(capellacore.Structure):
    packages = m.Containment["ConceptPkg"](
        "ownedConceptPkgs", (NS, "ConceptPkg")
    )
    concepts = m.Containment["Concept"]("ownedConcepts", (NS, "Concept"))


class Concept(capellacore.NamedElement):
    compliances = m.Association["ConceptCompliance"](
        (NS, "ConceptCompliance"), "compliances"
    )
    composite_links = m.Containment["ItemInConcept"](
        "compositeLinks", (NS, "ItemInConcept")
    )


class ConceptCompliance(capellacore.Relationship):
    comply_with_concept = m.Single["Concept"](
        m.Association((NS, "Concept"), "complyWithConcept")
    )
    compliant_capability = m.Single["OperationalCapability"](
        m.Association((NS, "OperationalCapability"), "compliantCapability")
    )


class ItemInConcept(capellacore.NamedElement):
    concept = m.Single["Concept"](m.Association((NS, "Concept"), "concept"))
    item = m.Single["AbstractConceptItem"](
        m.Association((NS, "AbstractConceptItem"), "item")
    )


class CommunityOfInterest(capellacore.NamedElement):
    community_of_interest_compositions = m.Containment[
        "CommunityOfInterestComposition"
    ](
        "communityOfInterestCompositions",
        (NS, "CommunityOfInterestComposition"),
    )


class CommunityOfInterestComposition(capellacore.NamedElement):
    community_of_interest = m.Association["CommunityOfInterest"](
        (NS, "CommunityOfInterest"), "communityOfInterest"
    )
    interested_organisational_unit = m.Association["OrganisationalUnit"](
        (NS, "OrganisationalUnit"), "interestedOrganisationUnit"
    )


class OrganisationalUnit(capellacore.NamedElement):
    organisational_unit_compositions = m.Containment[
        "OrganisationalUnitComposition"
    ]("organisationalUnitCompositions", (NS, "OrganisationalUnitComposition"))
    community_of_interest_memberships = m.Association[
        "CommunityOfInterestComposition"
    ]((NS, "CommunityOfInterestComposition"), "communityOfInterestMemberships")


class OrganisationalUnitComposition(capellacore.NamedElement):
    organisational_unit = m.Association["OrganisationalUnit"](
        (NS, "OrganisationalUnit"), "organisationalUnit"
    )
    participating_entity = m.Association["Entity"](
        (NS, "Entity"), "participatingEntity"
    )


class Location(AbstractConceptItem):
    location_description = m.StringPOD("locationDescription")
    located_entities = m.Association["Entity"](
        (NS, "Entity"), "locatedEntities"
    )


class CapabilityConfiguration(AbstractConceptItem):
    configured_capability = m.Association["OperationalCapability"](
        (NS, "OperationalCapability"), "configuredCapability"
    )


# NOTE: CommunicationMean should directly inherit from NamedRelationship,
# however this would result in an MRO conflict that cannot be resolved.
# Therefore we only inherit from ComponentExchange, copy the only missing
# definition (naming_rules), and register it as virtual subclass.
class CommunicationMean(fa.ComponentExchange):
    """An operational entity exchange."""

    _xmltag = "ownedComponentExchanges"

    # Taken from NamedRelationship, see note above
    naming_rules = m.Containment["capellacore.NamingRule"](
        "namingRules", (ns.CAPELLACORE, "NamingRule")
    )

    allocated_interactions = m.Alias["m.ElementList[fa.FunctionalExchange]"](
        "allocated_functional_exchanges"
    )


capellacore.NamedRelationship.register(CommunicationMean)


class EntityOperationalCapabilityInvolvement(capellacore.Involvement):
    pass


if not t.TYPE_CHECKING:

    def __getattr__(name):
        if name == "AbstractEntity":
            warnings.warn(
                "AbstractEntity has been merged into Entity",
                DeprecationWarning,
                stacklevel=2,
            )
            return Entity
        raise AttributeError(name)


from . import sa  # noqa: F401
