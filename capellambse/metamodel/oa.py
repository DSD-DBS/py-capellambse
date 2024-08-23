# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Tools for the Operational Analysis layer.

.. diagram:: [CDB] OA ORM
"""

from __future__ import annotations

from capellambse import model as m

from . import capellacommon, capellacore, cs, fa, information, interaction


@m.xtype_handler(None)
class OperationalActivity(fa.AbstractFunction):
    """An operational activity."""

    _xmltag = "ownedOperationalActivities"

    exchanges = m.DirectProxyAccessor(
        fa.FunctionalExchange, aslist=m.ElementList
    )

    inputs = m.Backref(fa.FunctionalExchange, "target", aslist=m.ElementList)
    outputs = m.Backref(fa.FunctionalExchange, "source", aslist=m.ElementList)

    owner: m.Accessor[Entity]

    @property
    def related_exchanges(self) -> m.ElementList[fa.FunctionalExchange]:
        seen: set[str] = set()
        exchanges = []
        for fex in self.inputs + self.outputs:
            if fex.uuid not in seen:
                exchanges.append(fex._element)
                seen.add(fex.uuid)
        return self.inputs._newlist(exchanges)


@m.xtype_handler(None)
class OperationalProcess(fa.FunctionalChain):
    """An operational process."""


@m.xtype_handler(None)
class EntityOperationalCapabilityInvolvement(interaction.AbstractInvolvement):
    """An EntityOperationalCapabilityInvolvement."""


@m.xtype_handler(None)
class OperationalCapability(m.ModelElement):
    """A capability in the OperationalAnalysis layer."""

    _xmltag = "ownedOperationalCapabilities"

    extends = m.DirectProxyAccessor(
        interaction.AbstractCapabilityExtend, aslist=m.ElementList
    )
    extended_by = m.Backref(
        interaction.AbstractCapabilityExtend, "target", aslist=m.ElementList
    )
    includes = m.DirectProxyAccessor(
        interaction.AbstractCapabilityInclude, aslist=m.ElementList
    )
    included_by = m.Backref(
        interaction.AbstractCapabilityInclude, "target", aslist=m.ElementList
    )
    generalizes = m.DirectProxyAccessor(
        interaction.AbstractCapabilityGeneralization, aslist=m.ElementList
    )
    generalized_by = m.DirectProxyAccessor(
        interaction.AbstractCapabilityGeneralization,
        "target",
        aslist=m.ElementList,
    )
    involved_activities = m.Allocation[OperationalActivity](
        "ownedAbstractFunctionAbstractCapabilityInvolvements",
        interaction.AbstractFunctionAbstractCapabilityInvolvement,
        aslist=m.ElementList,
        attr="involved",
    )
    involved_entities = m.Allocation[m.ModelElement](
        "ownedEntityOperationalCapabilityInvolvements",
        EntityOperationalCapabilityInvolvement,
        aslist=m.MixedElementList,
        attr="involved",
    )
    entity_involvements = m.DirectProxyAccessor(
        EntityOperationalCapabilityInvolvement, aslist=m.ElementList
    )
    involved_processes = m.Allocation[OperationalProcess](
        "ownedFunctionalChainAbstractCapabilityInvolvements",
        interaction.FunctionalChainAbstractCapabilityInvolvement,
        aslist=m.ElementList,
        attr="involved",
    )
    owned_processes = m.DirectProxyAccessor(
        OperationalProcess, aslist=m.ElementList
    )

    postcondition = m.Association(capellacore.Constraint, "postCondition")
    precondition = m.Association(capellacore.Constraint, "preCondition")
    scenarios = m.DirectProxyAccessor(
        interaction.Scenario, aslist=m.ElementList
    )
    states = m.Association(
        capellacommon.State, "availableInStates", aslist=m.ElementList
    )

    packages: m.Accessor


@m.xtype_handler(None)
class OperationalCapabilityPkg(m.ModelElement):
    """A package that holds operational capabilities."""

    _xmltag = "ownedAbstractCapabilityPkg"

    capabilities = m.DirectProxyAccessor(
        OperationalCapability, aslist=m.ElementList
    )

    packages: m.Accessor


class AbstractEntity(cs.Component):
    """Common code for Entities."""

    activities = m.Allocation[OperationalActivity](
        "ownedFunctionalAllocation",
        fa.ComponentFunctionalAllocation,
        aslist=m.ElementList,
        attr="targetElement",
        backattr="sourceElement",
    )
    capabilities = m.Backref(
        OperationalCapability, "involved_entities", aslist=m.ElementList
    )


@m.xtype_handler(None)
class Entity(AbstractEntity):
    """An Entity in the OperationalAnalysis layer."""

    _xmltag = "ownedEntities"

    entities: m.Accessor

    @property
    def inputs(self) -> m.ElementList[CommunicationMean]:
        return self._model.search(CommunicationMean).by_target(self)

    @property
    def outputs(self) -> m.ElementList[CommunicationMean]:
        return self._model.search(CommunicationMean).by_source(self)


@m.xtype_handler(None)
class OperationalActivityPkg(m.ModelElement):
    """A package that holds operational entities."""

    _xmltag = "ownedFunctionPkg"

    activities = m.DirectProxyAccessor(
        OperationalActivity, aslist=m.ElementList
    )

    packages: m.Accessor


@m.xtype_handler(None)
class CommunicationMean(fa.AbstractExchange):
    """An operational entity exchange."""

    _xmltag = "ownedComponentExchanges"

    allocated_interactions = m.Allocation[fa.FunctionalExchange](
        None,  # FIXME fill in tag
        fa.ComponentExchangeFunctionalExchangeAllocation,
        aslist=m.ElementList,
        attr="targetElement",
    )
    allocated_exchange_items = m.Association(
        information.ExchangeItem,
        "convoyedInformations",
        aslist=m.ElementList,
    )

    exchange_items = fa.ComponentExchange.exchange_items


@m.xtype_handler(None)
class EntityPkg(m.ModelElement):
    """A package that holds operational entities."""

    _xmltag = "ownedEntityPkg"

    entities = m.DirectProxyAccessor(Entity, aslist=m.ElementList)
    state_machines = m.DirectProxyAccessor(
        capellacommon.StateMachine, aslist=m.ElementList
    )

    packages: m.Accessor
    exchanges = m.DirectProxyAccessor(CommunicationMean, aslist=m.ElementList)


@m.xtype_handler(None)
class OperationalAnalysis(cs.ComponentArchitecture):
    """Provides access to the OperationalAnalysis layer of the model."""

    root_entity = m.DirectProxyAccessor(Entity, rootelem=EntityPkg)
    root_activity = m.DirectProxyAccessor(
        OperationalActivity, rootelem=OperationalActivityPkg
    )

    activity_package = m.DirectProxyAccessor(OperationalActivityPkg)
    capability_package = m.DirectProxyAccessor(OperationalCapabilityPkg)
    entity_package = m.DirectProxyAccessor(EntityPkg)

    all_activities = m.DeepProxyAccessor(
        OperationalActivity,
        aslist=m.ElementList,
    )
    all_processes = m.DeepProxyAccessor(
        OperationalProcess,
        aslist=m.ElementList,
    )
    all_capabilities = m.DeepProxyAccessor(
        OperationalCapability,
        aslist=m.ElementList,
    )
    all_actors = property(
        lambda self: self._model.search(Entity).by_is_actor(True)
    )
    all_entities = m.DeepProxyAccessor(
        Entity,
        aslist=m.ElementList,
    )

    all_activity_exchanges = m.DeepProxyAccessor(
        fa.FunctionalExchange,
        aslist=m.ElementList,
        rootelem=[OperationalActivityPkg, OperationalActivity],
    )
    all_entity_exchanges = m.DeepProxyAccessor(
        CommunicationMean,
        aslist=m.ElementList,
    )
    all_operational_processes = property(
        lambda self: self._model.search(OperationalProcess, below=self)
    )

    diagrams = m.DiagramAccessor(
        "Operational Analysis", cacheattr="_MelodyModel__diagram_cache"
    )


m.set_accessor(
    OperationalActivity,
    "packages",
    m.DirectProxyAccessor(OperationalActivityPkg, aslist=m.ElementList),
)
m.set_accessor(
    OperationalActivity,
    "owner",
    m.Backref(Entity, "activities"),
)
m.set_accessor(
    Entity,
    "exchanges",
    m.DirectProxyAccessor(CommunicationMean, aslist=m.ElementList),
)
m.set_accessor(
    Entity,
    "related_exchanges",
    m.Backref(CommunicationMean, "source", "target", aslist=m.ElementList),
)
m.set_self_references(
    (OperationalActivity, "activities"),
    (OperationalActivityPkg, "packages"),
    (OperationalCapabilityPkg, "packages"),
    (Entity, "entities"),
    (EntityPkg, "packages"),
)
