# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Tools for the Operational Analysis layer.

.. diagram:: [CDB] OA ORM
"""
from __future__ import annotations

import operator

from .. import common as c
from .. import crosslayer, diagram
from ..crosslayer import (
    capellacommon,
    capellacore,
    cs,
    fa,
    information,
    interaction,
)

XT_ARCH = "org.polarsys.capella.core.data.oa:OperationalAnalysis"

XT_EOCI = (
    "org.polarsys.capella.core.data.oa:EntityOperationalCapabilityInvolvement"
)


@c.xtype_handler(XT_ARCH)
class OperationalActivity(fa.AbstractFunction):
    """An operational activity."""

    _xmltag = "ownedOperationalActivities"

    owning_entity = c.CustomAccessor(
        c.GenericElement,
        operator.attrgetter("_model.oa.all_entities"),
        matchtransform=operator.attrgetter("activities"),
    )
    exchanges = c.DirectProxyAccessor(
        fa.FunctionalExchange, aslist=c.ElementList
    )

    @property
    def inputs(self) -> c.ElementList[fa.FunctionalExchange]:
        return self._model.oa.all_activity_exchanges.by_target(self)

    @property
    def outputs(self) -> c.ElementList[fa.FunctionalExchange]:
        return self._model.oa.all_activity_exchanges.by_source(self)

    @property
    def related_exchanges(self) -> c.ElementList[fa.FunctionalExchange]:
        seen: set[str] = set()
        exchanges = []
        for fex in self.inputs + self.outputs:
            if fex.uuid not in seen:
                exchanges.append(fex._element)
                seen.add(fex.uuid)
        return self.inputs._newlist(exchanges)


@c.xtype_handler(XT_ARCH)
class OperationalProcess(fa.FunctionalChain):
    """An operational process."""


@c.xtype_handler(XT_ARCH)
class EntityOperationalCapabilityInvolvement(interaction.AbstractInvolvement):
    """An EntityOperationalCapabilityInvolvement."""


@c.xtype_handler(XT_ARCH)
class OperationalCapability(c.GenericElement):
    """A capability in the OperationalAnalysis layer."""

    _xmltag = "ownedOperationalCapabilities"

    extends = c.DirectProxyAccessor(
        interaction.AbstractCapabilityExtend, aslist=c.ElementList
    )
    extended_by = c.ReferenceSearchingAccessor(
        interaction.AbstractCapabilityExtend, "target", aslist=c.ElementList
    )
    includes = c.DirectProxyAccessor(
        interaction.AbstractCapabilityInclude, aslist=c.ElementList
    )
    included_by = c.ReferenceSearchingAccessor(
        interaction.AbstractCapabilityInclude, "target", aslist=c.ElementList
    )
    generalizes = c.DirectProxyAccessor(
        interaction.AbstractCapabilityGeneralization, aslist=c.ElementList
    )
    generalized_by = c.DirectProxyAccessor(
        interaction.AbstractCapabilityGeneralization,
        "target",
        aslist=c.ElementList,
    )
    involved_activities = c.LinkAccessor[OperationalActivity](
        None,  # FIXME fill in tag
        interaction.XT_CAP2ACT,
        aslist=c.ElementList,
        attr="involved",
    )
    involved_entities = c.LinkAccessor[c.GenericElement](
        None,  # FIXME fill in tag
        XT_EOCI,
        aslist=c.MixedElementList,
        attr="involved",
    )
    entity_involvements = c.DirectProxyAccessor(
        EntityOperationalCapabilityInvolvement, aslist=c.ElementList
    )
    involved_processes = c.LinkAccessor[OperationalProcess](
        None,  # FIXME fill in tag
        interaction.XT_CAP2PROC,
        aslist=c.ElementList,
        attr="involved",
    )
    owned_processes = c.DirectProxyAccessor(
        OperationalProcess, aslist=c.ElementList
    )

    postcondition = c.AttrProxyAccessor(
        capellacore.Constraint, "postCondition"
    )
    precondition = c.AttrProxyAccessor(capellacore.Constraint, "preCondition")
    scenarios = c.DirectProxyAccessor(
        interaction.Scenario, aslist=c.ElementList
    )
    states = c.AttrProxyAccessor(
        capellacommon.State, "availableInStates", aslist=c.ElementList
    )

    packages: c.Accessor


@c.xtype_handler(XT_ARCH)
class OperationalCapabilityPkg(c.GenericElement):
    """A package that holds operational capabilities."""

    _xmltag = "ownedAbstractCapabilityPkg"

    capabilities = c.DirectProxyAccessor(
        OperationalCapability, aslist=c.ElementList
    )

    packages: c.Accessor


class AbstractEntity(cs.Component):
    """Common code for Entities."""

    activities = c.LinkAccessor[OperationalActivity](
        "ownedFunctionalAllocation",
        fa.XT_FCALLOC,
        aslist=c.ElementList,
        attr="targetElement",
    )
    capabilities = c.CustomAccessor(
        OperationalCapability,
        operator.attrgetter("_model.oa.all_capabilities"),
        matchtransform=operator.attrgetter("involved_entities"),
        aslist=c.ElementList,
    )


@c.xtype_handler(XT_ARCH)
class Entity(AbstractEntity):
    """An Entity in the OperationalAnalysis layer."""

    _xmltag = "ownedEntities"

    entities: c.Accessor

    @property
    def inputs(self) -> c.ElementList[CommunicationMean]:
        return self._model.oa.all_entity_exchanges.by_target(self)

    @property
    def outputs(self) -> c.ElementList[CommunicationMean]:
        return self._model.oa.all_entity_exchanges.by_source(self)


@c.xtype_handler(XT_ARCH)
class OperationalActivityPkg(c.GenericElement):
    """A package that holds operational entities."""

    _xmltag = "ownedFunctionPkg"

    activities = c.DirectProxyAccessor(
        OperationalActivity, aslist=c.ElementList
    )

    packages: c.Accessor


@c.xtype_handler(XT_ARCH)
class CommunicationMean(fa.AbstractExchange):
    """An operational entity exchange."""

    _xmltag = "ownedComponentExchanges"

    allocated_interactions = c.LinkAccessor[fa.FunctionalExchange](
        None,  # FIXME fill in tag
        fa.XT_COMP_EX_FNC_EX_ALLOC,
        aslist=c.ElementList,
        attr="targetElement",
    )
    allocated_exchange_items = c.AttrProxyAccessor(
        information.ExchangeItem,
        "convoyedInformations",
        aslist=c.ElementList,
    )

    exchange_items = fa.ComponentExchange.exchange_items


@c.xtype_handler(XT_ARCH)
class EntityPkg(c.GenericElement):
    """A package that holds operational entities."""

    _xmltag = "ownedEntityPkg"

    entities = c.DirectProxyAccessor(Entity, aslist=c.ElementList)
    state_machines = c.DirectProxyAccessor(
        capellacommon.StateMachine, aslist=c.ElementList
    )

    packages: c.Accessor
    exchanges = c.DirectProxyAccessor(CommunicationMean, aslist=c.ElementList)


@c.xtype_handler(None)
class OperationalAnalysis(crosslayer.BaseArchitectureLayer):
    """Provides access to the OperationalAnalysis layer of the model."""

    root_entity = c.DirectProxyAccessor(Entity, rootelem=EntityPkg)
    root_activity = c.DirectProxyAccessor(
        OperationalActivity, rootelem=OperationalActivityPkg
    )

    activity_package = c.DirectProxyAccessor(OperationalActivityPkg)
    capability_package = c.DirectProxyAccessor(OperationalCapabilityPkg)
    entity_package = c.DirectProxyAccessor(EntityPkg)

    all_activities = c.DeepProxyAccessor(
        OperationalActivity,
        aslist=c.ElementList,
    )
    all_processes = c.DeepProxyAccessor(
        OperationalProcess,
        aslist=c.ElementList,
    )
    all_capabilities = c.DeepProxyAccessor(
        OperationalCapability,
        aslist=c.ElementList,
    )
    all_actors = property(
        lambda self: self._model.search(Entity).by_is_actor(True)
    )
    all_entities = c.DeepProxyAccessor(
        Entity,
        aslist=c.ElementList,
    )

    all_activity_exchanges = c.DeepProxyAccessor(
        fa.FunctionalExchange,
        aslist=c.ElementList,
        rootelem=[OperationalActivityPkg, OperationalActivity],
    )
    all_entity_exchanges = c.DeepProxyAccessor(
        CommunicationMean,
        aslist=c.ElementList,
    )

    diagrams = diagram.DiagramAccessor(  # type: ignore[assignment]
        "Operational Analysis", cacheattr="_MelodyModel__diagram_cache"
    )


c.set_accessor(
    OperationalActivity,
    "packages",
    c.DirectProxyAccessor(OperationalActivityPkg, aslist=c.ElementList),
)
c.set_accessor(
    Entity,
    "exchanges",
    c.DirectProxyAccessor(CommunicationMean, aslist=c.ElementList),
)
c.set_accessor(
    Entity,
    "related_exchanges",
    c.ReferenceSearchingAccessor(
        CommunicationMean, "source", "target", aslist=c.ElementList
    ),
)
c.set_self_references(
    (OperationalActivityPkg, "packages"),
    (OperationalCapabilityPkg, "packages"),
    (Entity, "entities"),
    (EntityPkg, "packages"),
)
