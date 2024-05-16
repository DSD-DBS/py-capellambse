# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""The operational analysis module."""
from __future__ import annotations

from capellambse import modelv2 as m

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

NS = ns.OA


class OperationalAnalysis(cs.BlockArchitecture):
    role_pkg = m.Single(
        m.Containment["RolePkg"]("ownedRolePkg", (NS, "RolePkg")),
        enforce="max",
    )
    entity_pkg = m.Single(
        m.Containment["EntityPkg"]("ownedEntityPkg", (NS, "EntityPkg")),
        enforce="max",
    )
    concept_pkg = m.Single(
        m.Containment["ConceptPkg"]("ownedConceptPkg", (NS, "ConceptPkg")),
        enforce="max",
    )
    function_pkg = m.Single(
        m.Containment["OperationalActivityPkg"](
            None, (NS, "OperationalActivityPkg")
        )
    )
    activity_pkg = m.Single(
        m.Shortcut["OperationalActivityPkg"]("function_pkg"),
        enforce="max",
    )

    root_entity = m.Single(
        m.Shortcut["Entity"]("entity_pkg.entities"),
        enforce=False,
    )
    root_activity = m.Single(
        m.Shortcut["OperationalActivity"]("activity_pkg.activities"),
        enforce=False,
    )

    @property
    def all_activities(self) -> m.ElementList[OperationalActivity]:
        return self._model.search("OperationalActivity", below=self)

    @property
    def all_processes(self) -> m.ElementList[OperationalProcess]:
        return self._model.search("OperationalProcess", below=self)

    @property
    def all_capabilities(self) -> m.ElementList[OperationalCapability]:
        return self._model.search("OperationalCapability", below=self)

    @property
    def all_actors(self) -> m.ElementList[Entity]:
        return self.all_entities.by_is_actor(True, single=False)

    @property
    def all_entities(self) -> m.ElementList[Entity]:
        return self._model.search("Entity", below=self)

    @property
    def all_activity_exchanges(self) -> m.ElementList[fa.FunctionalExchange]:
        return self._model.search("FunctionalExchange", below=self)

    @property
    def all_entity_exchanges(self) -> m.ElementList[CommunicationMean]:
        return self._model.search("CommunicationMean", below=self)

    @property
    def all_operational_processes(self) -> m.ElementList[OperationalProcess]:
        return self._model.search("OperationalProcess", below=self)

    diagrams = m.Todo()


class OperationalScenario(capellacore.NamedElement):
    context = m.StringPOD("context")
    objective = m.StringPOD("objective")


class OperationalActivityPkg(fa.FunctionPkg):
    """A package that holds operational entities."""

    activities = m.Containment["OperationalActivity"](
        "ownedOperationalActivities", (NS, "OperationalActivity")
    )
    packages = m.Containment["OperationalActivityPkg"](
        "ownedOperationalActivityPkgs", (NS, "OperationalActivityPkg")
    )


class OperationalActivity(fa.AbstractFunction):
    activity_pkgs = m.Containment["OperationalActivityPkg"](
        "ownedOperationalActivityPkgs", (NS, "OperationalActivityPkg")
    )
    functional_chains = m.Containment["OperationalProcess"](
        None, (NS, "OperationalProcess")
    )
    processes = m.Shortcut["OperationalProcess"]("functional_chains")

    exchanges = m.Containment["fa.FunctionalExchange"](
        "ownedFunctionalExchanges",
        (ns.FA, "FunctionalExchange"),
    )
    incoming_exchanges = m.Backref["fa.FunctionalExchange"](
        (ns.FA, "FunctionalExchange"), lookup="target"
    )
    outgoing_exchanges = m.Backref["fa.FunctionalExchange"](
        (ns.FA, "FunctionalExchange"), lookup="source"
    )
    related_exchanges = m.Backref["fa.FunctionalExchange"](
        (ns.FA, "FunctionalExchange"), lookup=["source", "target"]
    )
    packages = m.Containment["OperationalActivityPkg"](
        "ownedFunctionPkg", (NS, "OperationalActivityPkg")
    )
    owner = m.Single(
        m.Backref["Entity"]((NS, "Entity"), lookup="activities"),
        enforce="max",
    )
    activities = m.Containment["OperationalActivity"](
        "ownedOperationalActivities", (NS, "OperationalActivity")
    )


class OperationalProcess(fa.FunctionalChain):
    """An operational process."""


class Swimlane(capellacore.NamedElement, activity.ActivityPartition):
    represented_element = m.Single(
        m.Association["Entity"]("representedElement", (NS, "Entity")),
        enforce="max",
    )


class OperationalCapabilityPkg(capellacommon.AbstractCapabilityPkg):
    """A package that holds operational capabilities."""

    capabilities = m.Containment["OperationalCapability"](
        "ownedOperationalCapabilities", (NS, "OperationalCapability")
    )
    packages = m.Containment["OperationalCapabilityPkg"](
        "ownedOperationalCapabilityPkgs", (NS, "OperationalCapabilityPkg")
    )
    configurations = m.Containment["CapabilityConfiguration"](
        "ownedCapabilityConfigurations", (NS, "CapabilityConfiguration")
    )
    concept_compliances = m.Allocation["Concept"](
        (NS, "ConceptCompliance"),
        (
            "ownedConceptCompliances",
            "complyWithConcept",
            "compliantCapability",
        ),
        (NS, "Concept"),
    )


class OperationalCapability(
    interaction.AbstractCapability, capellacore.Namespace
):
    compliances = m.Allocation["Concept"](
        (NS, "ConceptCompliance"),
        (
            "ownedConceptCompliances",
            "complyWithConcept",
            "compliantCapability",
        ),
        (NS, "Concept"),
    )
    configurations = m.Association["CapabilityConfiguration"](
        "configurations", (NS, "CapabilityConfiguration")
    )
    involved_entities = m.Allocation["Entity"](
        (NS, "EntityOperationalCapabilityInvolvement"),
        ("ownedEntityOperationalCapabilityInvolvements", "involved"),
        (NS, "Entity"),
    )

    extends = m.Allocation["OperationalCapability"](
        None, None, (NS, "OperationalCapability")
    )
    extended_by = m.Backref["OperationalCapability"](
        (NS, "OperationalCapability"), lookup="extends"
    )
    includes = m.Allocation["OperationalCapability"](
        None, None, (NS, "OperationalCapability")
    )
    included_by = m.Backref["OperationalCapability"](
        (NS, "OperationalCapability"), lookup="includes"
    )


class RolePkg(capellacore.Structure):
    packages = m.Containment["RolePkg"]("ownedRolePkgs", (NS, "RolePkg"))
    roles = m.Containment["Role"]("ownedRoles", (NS, "Role"))


class Role(information.AbstractInstance):
    usages = m.Containment["RoleAssemblyUsage"](
        "ownedRoleAssemblyUsages", (NS, "RoleAssemblyUsage")
    )
    allocated_activities = m.Allocation["OperationalActivity"](
        (NS, "ActivityAllocation"),
        ("ownedActivityAllocations", "targetElement", "sourceElement"),
        (NS, "OperationalActivity"),
    )


class RoleAssemblyUsage(capellacore.NamedElement):
    child = m.Single(
        m.Association["Role"]("child", (NS, "Role")), enforce=False
    )


class EntityPkg(cs.ComponentPkg):
    entities = m.Containment["Entity"]("ownedEntities", (NS, "Entity"))
    packages = m.Containment["EntityPkg"]("ownedEntityPkg", (NS, "EntityPkg"))
    locations = m.Containment["Location"]("ownedLocations", (NS, "Location"))
    state_machines = m.Containment["capellacommon.StateMachine"](
        "ownedStateMachines", (ns.CAPELLACOMMON, "StateMachine")
    )
    exchanges = m.Containment["CommunicationMean"](
        "ownedCommunicationMeans", (NS, "CommunicationMean")
    )
    communication_means = m.Shortcut["CommunicationMean"]("exchanges")


class AbstractConceptItem(cs.Component):
    composing_links = m.Association["ItemInConcept"](
        "composingLinks", (NS, "ItemInConcept")
    )


class Entity(
    AbstractConceptItem,
    modellingcore.InformationsExchanger,
    capellacore.InvolvedElement,
):
    ou_memberships = m.Allocation["OrganisationalUnit"](
        (NS, "OrganisationalUnitComposition"),
        (
            "organisationalUnitMemberships",
            "organisationalUnit",
            "participatingEntity",
        ),
        (NS, "OrganisationalUnit"),
    )
    actual_location = m.Single(
        m.Association["Location"]("actualLocation", (NS, "Location")),
        enforce="max",
    )
    entities = m.Containment["Entity"]("ownedEntities", (NS, "Entity"))
    communication_means = m.Containment["CommunicationMean"](
        "ownedCommunicationMeans", (NS, "CommunicationMean")
    )
    allocated_roles = m.Allocation["Role"](
        (NS, "RoleAllocation"),
        ("ownedRoleAllocations", "targetElement", "sourceElement"),
        (NS, "Role"),
    )

    ###########################################################################

    activities = m.Allocation["OperationalActivity"](
        (ns.FA, "ComponentFunctionalAllocation"),
        ("ownedFunctionalAllocation", "targetElement", "sourceElement"),
        (NS, "OperationalActivity"),
    )
    capabilities = m.Backref["OperationalCapability"](
        (NS, "OperationalCapability"), lookup="involved_entities"
    )
    inputs = m.Backref["CommunicationMean"](
        (NS, "CommunicationMean"), lookup="target"
    )
    outputs = m.Backref["CommunicationMean"](
        (NS, "CommunicationMean"), lookup="source"
    )
    exchanges = m.Containment["CommunicationMean"](
        "ownedComponentExchanges", (NS, "CommunicationMean")
    )
    related_exchanges = m.Backref["CommunicationMean"](
        (NS, "CommunicationMean"), lookup=["source", "target"]
    )


class ConceptPkg(capellacore.Structure):
    packages = m.Containment["ConceptPkg"](
        "ownedConceptPkgs", (NS, "ConceptPkg")
    )
    concepts = m.Containment["Concept"]("ownedConcepts", (NS, "Concept"))


class Concept(capellacore.NamedElement):
    compliances = m.Allocation["Concept"](
        (NS, "ConceptCompliance"),
        (
            "ownedConceptCompliances",
            "complyWithConcept",
            "compliantCapability",
        ),
        (NS, "Concept"),
    )
    composite_links = m.Containment["ItemInConcept"](
        "compositeLinks", (NS, "ItemInConcept")
    )


class ItemInConcept(capellacore.NamedElement):
    concept = m.Single(m.Association["Concept"]("concept", (NS, "Concept")))
    item = m.Single(
        m.Association["AbstractConceptItem"](
            "item", (NS, "AbstractConceptItem")
        )
    )


class CommunityOfInterest(capellacore.NamedElement):
    coi_components = m.Containment["CommunityOfInterestComposition"](
        "communityOfInterestCompositions",
        (NS, "CommunityOfInterestComposition"),
    )
    interested_ous = m.Shortcut["OrganisationalUnit"](
        "coi_compositions.interested_ou"
    )


class CommunityOfInterestComposition(capellacore.NamedElement):
    interested_ou = m.Single(
        m.Association["OrganisationalUnit"](
            "interestedOrganisationalUnit", (NS, "OrganisationalUnit")
        )
    )
    community_of_interest = m.Single(
        m.Association["CommunityOfInterest"](
            "communityOfInterest", (NS, "CommunityOfInterest")
        )
    )


class OrganisationalUnit(capellacore.NamedElement):
    ou_compositions = m.Containment["OrganisationalUnitComposition"](
        "organisationalUnitCompositions", (NS, "OrganisationalUnitComposition")
    )


class OrganisationalUnitComposition(capellacore.NamedElement):
    ou = m.Single(
        m.Association["OrganisationalUnit"](
            "organisationalUnit", (NS, "OrganisationalUnit")
        )
    )
    participating_entity = m.Single(
        m.Association["Entity"]("participatingEntity", (NS, "Entity"))
    )


class Location(AbstractConceptItem):
    location_description = m.StringPOD("locationDescription")


class CapabilityConfiguration(AbstractConceptItem):
    capability = m.Association["OperationalCapability"](
        "configuredCapability", (NS, "OperationCapability")
    )


class CommunicationMean(fa.ComponentExchange):
    """An operational entity exchange."""

    allocated_interactions = m.Allocation["fa.FunctionalExchange"](
        (ns.FA, "ComponentExchangeFunctionalExchangeAllocation"),
        ("ownedFunctionalExchanges", "targetElement", "sourceElement"),
        (ns.FA, "FunctionalExchange"),
    )
    allocated_exchange_items = m.Association["information.ExchangeItem"](
        "convoyedInformations", (ns.INFORMATION, "ExchangeItem")
    )
