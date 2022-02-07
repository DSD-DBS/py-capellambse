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
"""Implementation of objects and relations for Functional Analysis

Composite Structure objects inheritance tree (taxonomy):

.. diagram:: [CDB] CompositeStructure [Taxonomy]

Composite Structure object-relations map (ontology):

.. diagram:: [CDB] CompositeStructure [Ontology]
"""

import operator

from capellambse.loader import xmltools

from .. import common as c
from . import capellacommon, fa, information

XT_DEPLOY_LINK = (
    "org.polarsys.capella.core.data.pa.deployment:PartDeploymentLink"
)
XT_PHYS_PATH_INV = "org.polarsys.capella.core.data.cs:PhysicalPathInvolvement"


@c.xtype_handler(None)
class Part(c.GenericElement):
    """A representation of a physical component"""

    _xmltag = "ownedParts"

    type = c.AttrProxyAccessor(c.GenericElement, "abstractType")

    deployed_parts: c.Accessor


@c.xtype_handler(None)
class Interface(c.GenericElement):
    """An interface."""


@c.xtype_handler(None)
class InterfacePkg(c.GenericElement):
    """A package that can hold interfaces and exchange items."""

    exchange_items = c.ProxyAccessor(
        information.ExchangeItem,
        aslist=c.ElementList,
    )
    interfaces = c.ProxyAccessor(Interface, aslist=c.ElementList)

    packages: c.Accessor


@c.xtype_handler(None)
class PhysicalPort(c.GenericElement):
    """A physical port."""

    _xmltag = "ownedFeatures"

    owner = c.ParentAccessor(c.GenericElement)


@c.xtype_handler(None)
class PhysicalLink(PhysicalPort):
    """A physical link."""

    linkEnds = c.AttrProxyAccessor(
        PhysicalPort, "linkEnds", aslist=c.ElementList
    )
    exchanges = c.ProxyAccessor(
        fa.ComponentExchange,
        xtypes=fa.XT_COMP_EX_ALLOC,
        aslist=c.ElementList,
        follow="targetElement",
    )

    physical_paths: c.Accessor


class Component(c.GenericElement):
    """A template class for components."""

    is_abstract = xmltools.BooleanAttributeProperty(
        "_element",
        "abstract",
        __doc__="Boolean flag for an abstract Component",
    )
    is_human = xmltools.BooleanAttributeProperty(
        "_element", "human", __doc__="Boolean flag for a human Component"
    )
    is_actor = xmltools.BooleanAttributeProperty(
        "_element", "actor", __doc__="Boolean flag for an actor Component"
    )

    owner = c.ParentAccessor(c.GenericElement)
    state_machines = c.ProxyAccessor(
        capellacommon.StateMachine, aslist=c.ElementList
    )
    ports = c.ProxyAccessor(fa.ComponentPort, aslist=c.ElementList)
    physical_ports = c.ProxyAccessor(PhysicalPort, aslist=c.ElementList)
    parts = c.ReferenceSearchingAccessor(Part, "type", aslist=c.ElementList)


@c.xtype_handler(None)
class PhysicalPath(c.GenericElement):
    """A physical path."""

    _xmltag = "ownedPhysicalPath"

    involved_items = c.ProxyAccessor(
        c.GenericElement,
        xtypes=XT_PHYS_PATH_INV,
        aslist=c.MixedElementList,
        follow="involved",
    )
    exchanges = c.ProxyAccessor(
        fa.ComponentExchange,
        xtypes=fa.XT_COMP_EX_ALLOC,
        aslist=c.ElementList,
        follow="targetElement",
    )

    @property
    def involved_links(self):
        return self.involved_items.by_type("PhysicalLink")


@c.xtype_handler(None)
class ComponentRealization(c.GenericElement):
    """A realization that links to a component."""

    _xmltag = "ownedComponentRealizations"


c.set_accessor(
    InterfacePkg,
    "packages",
    c.ProxyAccessor(InterfacePkg, aslist=c.ElementList),
)
c.set_accessor(
    Part,
    "deployed_parts",
    c.ProxyAccessor(
        Part,
        XT_DEPLOY_LINK,
        aslist=c.ElementList,
        follow="deployedElement",
        follow_abstract=False,
    ),
)
c.set_accessor(
    PhysicalLink,
    "physical_paths",
    c.CustomAccessor(
        PhysicalPath,
        operator.attrgetter("_model.pa.all_physical_paths"),
        matchtransform=operator.attrgetter("involved_items"),
        aslist=c.ElementList,
    ),
)
