# Copyright 2021 DB Netz AG
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tools for the Operational Analysis layer.

.. diagram:: [CDB] OA ORM
"""
import operator

from .. import common as c
from .. import crosslayer, diagram
from ..crosslayer import capellacommon, capellacore, cs, fa, interaction

XT_ARCH = "org.polarsys.capella.core.data.oa:OperationalAnalysis"

XT_EOCI = (
    "org.polarsys.capella.core.data.oa:EntityOperationalCapabilityInvolvement"
)


@c.xtype_handler(XT_ARCH)
class OperationalActivity(c.GenericElement):
    """An operational activity."""

    _xmltag = "ownedOperationalActivities"

    owning_entity = c.CustomAccessor(
        c.GenericElement,
        operator.attrgetter("_model.oa.all_entities"),
        matchtransform=operator.attrgetter("activities"),
    )


@c.xtype_handler(XT_ARCH)
class OperationalProcess(c.GenericElement):
    """An operational process."""

    _xmltag = "ownedFunctionalChains"

    involved = c.ProxyAccessor(
        c.GenericElement,
        fa.XT_FCI,
        aslist=c.MixedElementList,
        follow="involved",
    )


@c.xtype_handler(XT_ARCH)
class OperationalCapability(c.GenericElement):
    """A capability in the OperationalAnalysis layer."""

    _xmltag = "ownedOperationalCapabilities"

    involved_activities = c.ProxyAccessor(
        OperationalActivity,
        interaction.XT_CAP2ACT,
        aslist=c.ElementList,
        follow="involved",
    )
    involved_entities = c.ProxyAccessor(
        c.GenericElement,
        XT_EOCI,
        follow="involved",
        aslist=c.MixedElementList,
    )
    involved_processes = c.ProxyAccessor(
        OperationalProcess,
        interaction.XT_CAP2PROC,
        aslist=c.ElementList,
        follow="involved",
    )
    owned_processes = c.ProxyAccessor(OperationalProcess, aslist=c.ElementList)

    postcondition = c.AttrProxyAccessor(
        capellacore.Constraint, "postCondition"
    )
    precondition = c.AttrProxyAccessor(capellacore.Constraint, "preCondition")
    scenarios = c.ProxyAccessor(interaction.Scenario, aslist=c.ElementList)
    states = c.AttrProxyAccessor(
        capellacommon.State, "availableInStates", aslist=c.ElementList
    )

    packages: c.Accessor


@c.xtype_handler(XT_ARCH)
class OperationalCapabilityPkg(c.GenericElement):
    """A package that holds operational capabilities."""

    _xmltag = "ownedAbstractCapabilityPkg"

    capabilities = c.ProxyAccessor(OperationalCapability, aslist=c.ElementList)

    packages: c.Accessor


class AbstractEntity(cs.Component):
    """Common code for Entities."""

    activities = c.ProxyAccessor(
        OperationalActivity,
        fa.XT_FCALLOC,
        aslist=c.ElementList,
        follow="targetElement",
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


@c.xtype_handler(XT_ARCH)
class OperationalActivityPkg(c.GenericElement):
    """A package that holds operational entities."""

    _xmltag = "ownedFunctionPkg"

    activities = c.ProxyAccessor(OperationalActivity, aslist=c.ElementList)

    packages: c.Accessor


@c.xtype_handler(XT_ARCH)
class EntityPkg(c.GenericElement):
    """A package that holds operational entities."""

    _xmltag = "ownedEntityPkg"

    entities = c.ProxyAccessor(Entity, aslist=c.ElementList)
    state_machines = c.ProxyAccessor(
        capellacommon.StateMachine, aslist=c.ElementList
    )

    packages: c.Accessor


class OperationalAnalysis(crosslayer.BaseArchitectureLayer):
    """Provides access to the OperationalAnalysis layer of the model."""

    root_entity = c.ProxyAccessor(Entity, rootelem=EntityPkg)
    root_activity = c.ProxyAccessor(
        OperationalActivity, rootelem=OperationalActivityPkg
    )

    activity_package = c.ProxyAccessor(OperationalActivityPkg)
    capability_package = c.ProxyAccessor(OperationalCapabilityPkg)
    entity_package = c.ProxyAccessor(EntityPkg)

    all_activities = c.ProxyAccessor(
        OperationalActivity,
        aslist=c.ElementList,
        deep=True,
    )
    all_actors = c.CustomAccessor(  # type: ignore[misc]
        Entity,
        operator.attrgetter("all_entities"),
        elmmatcher=lambda x, _: x.is_actor,  # type: ignore[attr-defined]
        aslist=c.ElementList,
    )
    all_capabilities = c.ProxyAccessor(
        OperationalCapability,
        aslist=c.ElementList,
        deep=True,
    )
    all_entities = c.ProxyAccessor(
        Entity,
        aslist=c.ElementList,
        deep=True,
    )
    all_processes = c.ProxyAccessor(
        OperationalProcess,
        aslist=c.ElementList,
        deep=True,
    )
    diagrams = diagram.DiagramAccessor(
        "Operational Analysis", cacheattr="_MelodyModel__diagram_cache"
    )


c.set_accessor(
    OperationalCapability,
    "inheritance",
    c.ProxyAccessor(
        OperationalCapability,
        interaction.XT_CAP_GEN,
        follow="super",
        aslist=c.ElementList,
    ),
)
c.set_self_references(
    (OperationalActivityPkg, "packages"),
    (OperationalCapabilityPkg, "packages"),
    (Entity, "entities"),
    (EntityPkg, "packages"),
)
