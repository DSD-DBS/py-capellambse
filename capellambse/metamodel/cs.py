# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Implementation of objects and relations for Functional Analysis.

Composite Structure objects inheritance tree (taxonomy):

.. diagram:: [CDB] CompositeStructure [Taxonomy]

Composite Structure object-relations map (ontology):

.. diagram:: [CDB] CompositeStructure [Ontology]
"""

import capellambse.model as m

from . import capellacommon, fa, information


@m.xtype_handler(None)
class Part(m.ModelElement):
    """A representation of a physical component."""

    _xmltag = "ownedParts"

    type = m.Association(m.ModelElement, "abstractType")

    deployed_parts: m.Accessor


@m.xtype_handler(None)
class ExchangeItemAllocation(m.ModelElement):
    """An allocation of an ExchangeItem to an Interface."""

    item = m.Association(information.ExchangeItem, "allocatedItem")


@m.xtype_handler(None)
class Interface(m.ModelElement):
    """An interface."""

    exchange_item_allocations = m.DirectProxyAccessor(
        ExchangeItemAllocation, aslist=m.ElementList
    )


@m.xtype_handler(None)
class InterfacePkg(m.ModelElement):
    """A package that can hold interfaces and exchange items."""

    exchange_items = m.DirectProxyAccessor(
        information.ExchangeItem, aslist=m.ElementList
    )
    interfaces = m.DirectProxyAccessor(Interface, aslist=m.ElementList)

    packages: m.Accessor


@m.xtype_handler(None)
class PhysicalPort(m.ModelElement):
    """A physical port."""

    _xmltag = "ownedFeatures"

    owner = m.ParentAccessor(m.ModelElement)
    links: m.Accessor


@m.xtype_handler(None)
class PhysicalLink(PhysicalPort):
    """A physical link."""

    ends = m.PhysicalLinkEndsAccessor(
        PhysicalPort, "linkEnds", aslist=m.ElementList
    )
    exchanges = m.Allocation[fa.ComponentExchange](
        "ownedComponentExchangeAllocations",
        fa.ComponentExchangeAllocation,
        aslist=m.ElementList,
        attr="targetElement",
        backattr="sourceElement",
    )

    physical_paths: m.Accessor

    source = m.IndexAccessor[PhysicalPort]("ends", 0)
    target = m.IndexAccessor[PhysicalPort]("ends", 1)


@m.xtype_handler(None)
class PhysicalPath(m.ModelElement):
    """A physical path."""

    _xmltag = "ownedPhysicalPath"

    involved_items = m.Allocation[m.ModelElement](
        None,  # FIXME fill in tag
        "org.polarsys.capella.core.data.cs:PhysicalPathInvolvement",
        aslist=m.MixedElementList,
        attr="involved",
    )
    exchanges = m.Allocation[fa.ComponentExchange](
        None,  # FIXME fill in tag
        "org.polarsys.capella.core.data.fa:ComponentExchangeAllocation",
        aslist=m.ElementList,
        attr="targetElement",
    )

    @property
    def involved_links(self) -> m.ElementList[PhysicalLink]:
        return self.involved_items.by_type("PhysicalLink")


class Component(m.ModelElement):
    """A template class for components."""

    is_abstract = m.BoolPOD("abstract")
    """Boolean flag for an abstract Component."""
    is_human = m.BoolPOD("human")
    """Boolean flag for a human Component."""
    is_actor = m.BoolPOD("actor")
    """Boolean flag for an actor Component."""

    owner = m.ParentAccessor(m.ModelElement)
    state_machines = m.DirectProxyAccessor(
        capellacommon.StateMachine, aslist=m.ElementList
    )
    ports = m.DirectProxyAccessor(fa.ComponentPort, aslist=m.ElementList)
    physical_ports = m.DirectProxyAccessor(PhysicalPort, aslist=m.ElementList)
    parts = m.Backref(Part, "type", aslist=m.ElementList)
    physical_paths = m.DirectProxyAccessor(PhysicalPath, aslist=m.ElementList)
    physical_links = m.DirectProxyAccessor(PhysicalLink, aslist=m.ElementList)
    exchanges = m.DirectProxyAccessor(
        fa.ComponentExchange, aslist=m.ElementList
    )

    related_exchanges = m.Backref(
        fa.ComponentExchange,
        "source.owner",
        "target.owner",
        aslist=m.ElementList,
    )

    realized_components = m.Allocation["Component"](
        "ownedComponentRealizations",
        "org.polarsys.capella.core.data.cs:ComponentRealization",
        aslist=m.ElementList,
        attr="targetElement",
    )
    realizing_components = m.Backref["Component"](
        (), "realized_components", aslist=m.ElementList
    )


@m.xtype_handler(None)
class ComponentRealization(m.ModelElement):
    """A realization that links to a component."""

    _xmltag = "ownedComponentRealizations"


class ComponentArchitecture(m.ModelElement):
    """Formerly known as BaseArchitectureLayer."""

    data_package = m.DirectProxyAccessor(information.DataPkg)
    interface_package = m.DirectProxyAccessor(InterfacePkg)
    component_exchange_categories = m.DirectProxyAccessor(
        fa.ComponentExchangeCategory, aslist=m.ElementList
    )

    all_classes = m.DeepProxyAccessor(information.Class, aslist=m.ElementList)
    all_collections = m.DeepProxyAccessor(
        information.Collection, aslist=m.ElementList
    )
    all_unions = m.DeepProxyAccessor(information.Union, aslist=m.ElementList)
    all_enumerations = m.DeepProxyAccessor(
        information.datatype.Enumeration, aslist=m.ElementList
    )
    all_complex_values = m.DeepProxyAccessor(
        information.datavalue.ComplexValue, aslist=m.ElementList
    )
    all_interfaces = m.DeepProxyAccessor(Interface, aslist=m.ElementList)


m.set_accessor(
    InterfacePkg,
    "packages",
    m.DirectProxyAccessor(InterfacePkg, aslist=m.ElementList),
)
m.set_accessor(
    Part,
    "deployed_parts",
    m.Allocation(
        "ownedDeploymentLinks",
        "org.polarsys.capella.core.data.pa.deployment:PartDeploymentLink",
        aslist=m.ElementList,
        attr="deployedElement",
        backattr="location",
    ),
)
m.set_accessor(
    PhysicalPort,
    "links",
    m.Backref(PhysicalLink, "ends", aslist=m.ElementList),
)
m.set_accessor(
    PhysicalLink,
    "physical_paths",
    m.Backref(PhysicalPath, "involved_items", aslist=m.ElementList),
)
m.set_accessor(
    fa.ComponentExchange,
    "allocating_physical_link",
    m.Backref(PhysicalLink, "exchanges"),
)
m.set_accessor(
    fa.ComponentExchange,
    "allocating_physical_paths",
    m.Backref(PhysicalPath, "exchanges", aslist=m.ElementList),
)
