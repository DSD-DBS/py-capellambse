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
class Part(m.GenericElement):
    """A representation of a physical component."""

    _xmltag = "ownedParts"

    type = m.AttrProxyAccessor(m.GenericElement, "abstractType")

    deployed_parts: m.Accessor


@m.xtype_handler(None)
class ExchangeItemAllocation(m.GenericElement):
    """An allocation of an ExchangeItem to an Interface."""

    item = m.AttrProxyAccessor(information.ExchangeItem, "allocatedItem")


@m.xtype_handler(None)
class Interface(m.GenericElement):
    """An interface."""

    exchange_item_allocations = m.DirectProxyAccessor(
        ExchangeItemAllocation, aslist=m.ElementList
    )


@m.xtype_handler(None)
class InterfacePkg(m.GenericElement):
    """A package that can hold interfaces and exchange items."""

    exchange_items = m.DirectProxyAccessor(
        information.ExchangeItem, aslist=m.ElementList
    )
    interfaces = m.DirectProxyAccessor(Interface, aslist=m.ElementList)

    packages: m.Accessor


@m.xtype_handler(None)
class PhysicalPort(m.GenericElement):
    """A physical port."""

    _xmltag = "ownedFeatures"

    owner = m.ParentAccessor(m.GenericElement)
    links: m.Accessor


@m.xtype_handler(None)
class PhysicalLink(PhysicalPort):
    """A physical link."""

    ends = m.PhysicalLinkEndsAccessor(
        PhysicalPort, "linkEnds", aslist=m.ElementList
    )
    exchanges = m.LinkAccessor[fa.ComponentExchange](
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
class PhysicalPath(m.GenericElement):
    """A physical path."""

    _xmltag = "ownedPhysicalPath"

    involved_items = m.LinkAccessor[m.GenericElement](
        None,  # FIXME fill in tag
        "org.polarsys.capella.core.data.cs:PhysicalPathInvolvement",
        aslist=m.MixedElementList,
        attr="involved",
    )
    exchanges = m.LinkAccessor[fa.ComponentExchange](
        None,  # FIXME fill in tag
        "org.polarsys.capella.core.data.fa:ComponentExchangeAllocation",
        aslist=m.ElementList,
        attr="targetElement",
    )

    @property
    def involved_links(self) -> m.ElementList[PhysicalLink]:
        return self.involved_items.by_type("PhysicalLink")


class Component(m.GenericElement):
    """A template class for components."""

    is_abstract = m.BoolPOD("abstract")
    """Boolean flag for an abstract Component."""
    is_human = m.BoolPOD("human")
    """Boolean flag for a human Component."""
    is_actor = m.BoolPOD("actor")
    """Boolean flag for an actor Component."""

    owner = m.ParentAccessor(m.GenericElement)
    state_machines = m.DirectProxyAccessor(
        capellacommon.StateMachine, aslist=m.ElementList
    )
    ports = m.DirectProxyAccessor(fa.ComponentPort, aslist=m.ElementList)
    physical_ports = m.DirectProxyAccessor(PhysicalPort, aslist=m.ElementList)
    parts = m.ReferenceSearchingAccessor(Part, "type", aslist=m.ElementList)
    physical_paths = m.DirectProxyAccessor(PhysicalPath, aslist=m.ElementList)
    physical_links = m.DirectProxyAccessor(PhysicalLink, aslist=m.ElementList)
    exchanges = m.DirectProxyAccessor(
        fa.ComponentExchange, aslist=m.ElementList
    )

    related_exchanges = m.ReferenceSearchingAccessor(
        fa.ComponentExchange,
        "source.owner",
        "target.owner",
        aslist=m.ElementList,
    )

    realized_components = m.LinkAccessor["Component"](
        "ownedComponentRealizations",
        "org.polarsys.capella.core.data.cs:ComponentRealization",
        aslist=m.ElementList,
        attr="targetElement",
    )
    realizing_components = m.ReferenceSearchingAccessor["Component"](
        (), "realized_components", aslist=m.ElementList
    )


@m.xtype_handler(None)
class ComponentRealization(m.GenericElement):
    """A realization that links to a component."""

    _xmltag = "ownedComponentRealizations"


class ComponentArchitecture(m.GenericElement):
    """Formerly known as BaseArchitectureLayer."""

    data_package = m.DirectProxyAccessor(information.DataPkg)
    interface_package = m.DirectProxyAccessor(InterfacePkg)

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
    m.LinkAccessor(
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
    m.ReferenceSearchingAccessor(PhysicalLink, "ends", aslist=m.ElementList),
)
m.set_accessor(
    PhysicalLink,
    "physical_paths",
    m.ReferenceSearchingAccessor(
        PhysicalPath, "involved_items", aslist=m.ElementList
    ),
)
m.set_accessor(
    fa.ComponentExchange,
    "allocating_physical_link",
    m.ReferenceSearchingAccessor(PhysicalLink, "exchanges"),
)
m.set_accessor(
    fa.ComponentExchange,
    "allocating_physical_paths",
    m.ReferenceSearchingAccessor(
        PhysicalPath, "exchanges", aslist=m.ElementList
    ),
)
