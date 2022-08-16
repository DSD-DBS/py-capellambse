# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

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

    exchange_items = c.DirectProxyAccessor(
        information.ExchangeItem, aslist=c.ElementList
    )
    interfaces = c.DirectProxyAccessor(Interface, aslist=c.ElementList)

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
    exchanges = c.ReferencingProxyAccessor(
        fa.ComponentExchange,
        xtypes=fa.XT_COMP_EX_ALLOC,
        aslist=c.ElementList,
        follow="targetElement",
    )

    physical_paths: c.Accessor


@c.xtype_handler(None)
class PhysicalPath(c.GenericElement):
    """A physical path."""

    _xmltag = "ownedPhysicalPath"

    involved_items = c.ReferencingProxyAccessor(
        c.GenericElement,
        xtypes=XT_PHYS_PATH_INV,
        aslist=c.MixedElementList,
        follow="involved",
    )
    exchanges = c.ReferencingProxyAccessor(
        fa.ComponentExchange,
        xtypes=fa.XT_COMP_EX_ALLOC,
        aslist=c.ElementList,
        follow="targetElement",
    )

    @property
    def involved_links(self) -> c.ElementList[PhysicalLink]:
        return self.involved_items.by_type("PhysicalLink")


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
    state_machines = c.DirectProxyAccessor(
        capellacommon.StateMachine, aslist=c.ElementList
    )
    ports = c.DirectProxyAccessor(fa.ComponentPort, aslist=c.ElementList)
    physical_ports = c.DirectProxyAccessor(PhysicalPort, aslist=c.ElementList)
    parts = c.ReferenceSearchingAccessor(Part, "type", aslist=c.ElementList)
    physical_paths = c.DirectProxyAccessor(PhysicalPath, aslist=c.ElementList)
    physical_links = c.DirectProxyAccessor(PhysicalLink, aslist=c.ElementList)
    exchanges = c.ReferenceSearchingAccessor(
        fa.ComponentExchange,
        "source.owner",
        "target.owner",
        aslist=c.ElementList,
    )


@c.xtype_handler(None)
class ComponentRealization(c.GenericElement):
    """A realization that links to a component."""

    _xmltag = "ownedComponentRealizations"


c.set_accessor(
    InterfacePkg,
    "packages",
    c.DirectProxyAccessor(InterfacePkg, aslist=c.ElementList),
)
c.set_accessor(
    Part,
    "deployed_parts",
    c.ReferencingProxyAccessor(
        Part, XT_DEPLOY_LINK, aslist=c.ElementList, follow="deployedElement"
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
c.set_accessor(
    fa.ComponentExchange,
    "allocating_physical_link",
    c.ReferenceSearchingAccessor(PhysicalLink, "exchanges"),
)
c.set_accessor(
    fa.ComponentExchange,
    "allocating_physical_path",
    c.ReferenceSearchingAccessor(PhysicalPath, "exchanges"),
)
