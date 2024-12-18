# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Implementation of objects and relations for Functional Analysis.

Composite Structure objects inheritance tree (taxonomy):

.. diagram:: [CDB] CompositeStructure [Taxonomy]

Composite Structure object-relations map (ontology):

.. diagram:: [CDB] CompositeStructure [Ontology]
"""

import typing as t

import capellambse.model as m

from . import capellacommon, fa, information
from . import namespaces as ns

NS = ns.CS


class Part(m.ModelElement):
    """A representation of a physical component."""

    _xmltag = "ownedParts"

    type = m.Single(m.Association(m.ModelElement, "abstractType"))

    deployed_parts: m.Accessor


class ExchangeItemAllocation(m.ModelElement):
    """An allocation of an ExchangeItem to an Interface."""

    item = m.Single(m.Association(information.ExchangeItem, "allocatedItem"))


class Interface(m.ModelElement):
    """An interface."""

    exchange_item_allocations = m.DirectProxyAccessor(
        ExchangeItemAllocation, aslist=m.ElementList
    )


class InterfacePkg(m.ModelElement):
    """A package that can hold interfaces and exchange items."""

    exchange_items = m.DirectProxyAccessor(
        information.ExchangeItem, aslist=m.ElementList
    )
    interfaces = m.DirectProxyAccessor(Interface, aslist=m.ElementList)

    packages: m.Accessor


class PhysicalPort(m.ModelElement):
    """A physical port."""

    _xmltag = "ownedFeatures"

    owner = m.ParentAccessor()
    links: m.Accessor


class PhysicalLink(PhysicalPort):
    """A physical link."""

    ends = m.PhysicalLinkEndsAccessor(
        PhysicalPort, "linkEnds", aslist=m.ElementList
    )
    exchanges = m.Allocation[fa.ComponentExchange](
        "ownedComponentExchangeAllocations",
        fa.ComponentExchangeAllocation,
        attr="targetElement",
        backattr="sourceElement",
    )

    physical_paths: m.Accessor

    source = m.IndexAccessor[PhysicalPort]("ends", 0)
    target = m.IndexAccessor[PhysicalPort]("ends", 1)


class PhysicalPath(m.ModelElement):
    """A physical path."""

    _xmltag = "ownedPhysicalPath"

    involved_items = m.Allocation[m.ModelElement](
        None,  # FIXME fill in tag
        "org.polarsys.capella.core.data.cs:PhysicalPathInvolvement",
        attr="involved",
        legacy_by_type=True,
    )
    exchanges = m.Allocation[fa.ComponentExchange](
        None,  # FIXME fill in tag
        "org.polarsys.capella.core.data.fa:ComponentExchangeAllocation",
        attr="targetElement",
    )

    @property
    def involved_links(self) -> m.ElementList[PhysicalLink]:
        items = self.involved_items.by_class("PhysicalLink")
        assert isinstance(items, m.ElementList)
        assert all(isinstance(i, PhysicalLink) for i in items)
        return t.cast(m.ElementList[PhysicalLink], items)


class Component(m.ModelElement):
    """A template class for components."""

    is_abstract = m.BoolPOD("abstract")
    """Boolean flag for an abstract Component."""
    is_human = m.BoolPOD("human")
    """Boolean flag for a human Component."""
    is_actor = m.BoolPOD("actor")
    """Boolean flag for an actor Component."""

    owned_features = m.Containment(
        "ownedFeatures", m.ModelElement, aslist=m.ElementList
    )

    owner = m.ParentAccessor()
    state_machines = m.DirectProxyAccessor(
        capellacommon.StateMachine, aslist=m.ElementList
    )
    ports = m.DirectProxyAccessor(fa.ComponentPort, aslist=m.ElementList)
    physical_ports = m.DirectProxyAccessor(PhysicalPort, aslist=m.ElementList)
    parts = m.Backref(Part, "type")
    physical_paths = m.DirectProxyAccessor(PhysicalPath, aslist=m.ElementList)
    physical_links = m.DirectProxyAccessor(PhysicalLink, aslist=m.ElementList)
    exchanges = m.DirectProxyAccessor(
        fa.ComponentExchange, aslist=m.ElementList
    )

    related_exchanges = m.Backref(
        fa.ComponentExchange,
        "source.owner",
        "target.owner",
    )

    realized_components = m.Allocation["Component"](
        "ownedComponentRealizations",
        "org.polarsys.capella.core.data.cs:ComponentRealization",
        attr="targetElement",
    )
    realizing_components = m.Backref["Component"]((), "realized_components")


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


InterfacePkg.packages = m.DirectProxyAccessor(
    InterfacePkg, aslist=m.ElementList
)
Part.deployed_parts = m.Allocation(
    "ownedDeploymentLinks",
    "org.polarsys.capella.core.data.pa.deployment:PartDeploymentLink",
    attr="deployedElement",
    backattr="location",
)
PhysicalPort.links = m.Backref(PhysicalLink, "ends")
PhysicalLink.physical_paths = m.Backref(PhysicalPath, "involved_items")
fa.ComponentExchange.allocating_physical_link = m.Single(
    m.Backref(PhysicalLink, "exchanges")
)
fa.ComponentExchange.allocating_physical_paths = m.Backref(
    PhysicalPath, "exchanges"
)
