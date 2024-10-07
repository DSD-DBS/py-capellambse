# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Implementation of objects and relations for Functional Analysis."""

from __future__ import annotations

import typing as t

import capellambse.model as m

from . import (
    capellacore,
    fa,
    information,
    interaction,
    modellingcore,
    modeltypes,
)
from . import namespaces as ns

if t.TYPE_CHECKING:
    from . import capellacommon

NS = ns.CS


class BlockArchitecturePkg(
    capellacore.ModellingArchitecturePkg, abstract=True
):
    """Container package for BlockArchitecture elements."""


class BlockArchitecture(fa.AbstractFunctionalArchitecture, abstract=True):
    """Formerly known as BaseArchitectureLayer."""

    capability_pkg = m.Single["capellacommon.AbstractCapabilityPkg"](
        m.Containment(
            "ownedAbstractCapabilityPkgs",
            (ns.CAPELLACOMMON, "AbstractCapabilityPkg"),
        )
    )
    capability_package = m.DeprecatedAccessor["AbstractCapabilityPkg"](
        "capability_pkg"
    )
    interface_pkg = m.Single["InterfacePkg"](
        m.Containment("ownedInterfacePkg", (NS, "InterfacePkg"))
    )
    interface_package = m.DeprecatedAccessor["InterfacePkg"]("interface_pkg")
    data_pkg = m.Single["information.DataPkg"](
        m.Containment("ownedDataPkg", (ns.INFORMATION, "DataPkg"))
    )
    data_package = m.DeprecatedAccessor["information.DataPkg"]("data_pkg")

    @property
    def all_classes(self) -> m.ElementList[information.Class]:
        return self._model.search((ns.INFORMATION, "Class"), below=self)

    @property
    def all_collections(self) -> m.ElementList[information.Collection]:
        return self._model.search((ns.INFORMATION, "Collection"), below=self)

    @property
    def all_unions(self) -> m.ElementList[information.Union]:
        return self._model.search((ns.INFORMATION, "Union"), below=self)

    @property
    def all_enumerations(
        self,
    ) -> m.ElementList[information.datatype.Enumeration]:
        return self._model.search(
            (ns.INFORMATION_DATATYPE, "Enumeration"), below=self
        )

    @property
    def all_complex_values(
        self,
    ) -> m.ElementList[information.datatype.ComplexValue]:
        return self._model.search(
            (ns.INFORMATION_DATATYPE, "ComplexValue"), below=self
        )

    @property
    def all_interfaces(self) -> m.ElementList[Interface]:
        return self._model.search((NS, "Interface"), below=self)

    @property
    def all_capabilities(
        self,
    ) -> m.ElementList[interaction.AbstractCapability]:
        return self._model.search(
            (ns.INTERACTION, "AbstractCapability"), below=self
        )


class Block(
    fa.AbstractFunctionalBlock,
    # NOTE: In the upstream metamodel, ModellingBlock comes first,
    # but this would result in an MRO conflict.
    capellacore.ModellingBlock,
    abstract=True,
):
    capability_pkg = m.Single["capellacommon.AbstractCapabilityPkg"](
        m.Containment(
            "ownedAbstractCapabilityPkg",
            (ns.CAPELLACOMMON, "AbstractCapabilityPkg"),
        )
    )
    interface_pkg = m.Single["InterfacePkg"](
        m.Containment("ownedInterfacePkg", (NS, "InterfacePkg"))
    )
    interface_package = m.DeprecatedAccessor["InterfacePkg"]("interface_pkg")
    data_pkg = m.Single["information.DataPkg"](
        m.Containment("ownedDataPkg", (ns.INFORMATION, "DataPkg"))
    )
    data_package = m.DeprecatedAccessor["information.DataPkg"]("data_pkg")
    state_machines = m.Containment["capellacommon.StateMachine"](
        "ownedStateMachines", (ns.CAPELLACOMMON, "StateMachine")
    )


class ComponentArchitecture(BlockArchitecture, abstract=True):
    pass


class InterfaceAllocator(capellacore.CapellaElement, abstract=True):
    allocated_interfaces = m.Allocation["Interface"](
        "ownedInterfaceAllocations",
        (NS, "InterfaceAllocation"),
        (NS, "Interface"),
        attr="targetElement",
        backattr="sourceElement",
    )


class Component(
    Block,
    capellacore.Classifier,
    InterfaceAllocator,
    information.communication.CommunicationLinkExchanger,
    abstract=True,
):
    is_abstract = m.BoolPOD("abstract")  # TODO not in metamodel?
    """Boolean flag for an abstract Component."""
    is_actor = m.BoolPOD("actor")
    """Boolean flag for an actor Component."""
    is_human = m.BoolPOD("human")
    """Boolean flag for a human Component."""
    owner = m.DeprecatedAccessor[m.ModelElement]("parent")
    used_interfaces = m.Allocation["Interface"](
        "ownedInterfaceUses",
        (NS, "InterfaceUse"),
        (NS, "Interface"),
        attr="usedInterface",
    )
    implemented_interfaces = m.Allocation["Interface"](
        "ownedInterfaceImplementations",
        (NS, "InterfaceImplementation"),
        (NS, "Interface"),
        attr="implementedInterfaces",
    )
    realized_components = m.Allocation["Component"](
        "ownedComponentRealizations",
        (NS, "ComponentRealization"),
        (NS, "Component"),
        attr="targetElement",
        backattr="sourceElement",
    )
    realizing_components = m.Backref["Component"](
        (NS, "Component"), "realized_components"
    )
    ports = m.DirectProxyAccessor(  # TODO not in metamodel?
        fa.ComponentPort, aslist=m.ElementList
    )
    physical_ports = m.DirectProxyAccessor(  # TODO not in metamodel?
        PhysicalPort, aslist=m.ElementList
    )
    parts = m.Backref(Part, "type")  # TODO not in metamodel?
    physical_paths = m.Containment["PhysicalPath"](
        "ownedPhysicalPath", (NS, "PhysicalPath")
    )
    physical_links = m.Containment["PhysicalLink"](
        "ownedPhysicalLinks", (NS, "PhysicalLink")
    )
    physical_link_categories = m.Containment["PhysicalLinkCategory"](
        "ownedPhysicalLinkCategories", (NS, "PhysicalLinkCategory")
    )
    exchanges = m.DeprecatedAccessor["fa.ComponentExchange"](
        "component_exchanges"
    )
    related_exchanges = m.Backref["fa.ComponentExchange"](
        (ns.FA, "ComponentExchange"), "source.owner", "target.owner"
    )


class DeployableElement(capellacore.NamedElement, abstract=True):
    """A physical model element intended to be deployed."""


class DeploymentTarget(capellacore.NamedElement, abstract=True):
    """The physical target that will host a deployable element."""


class AbstractPathInvolvedElement(capellacore.InvolvedElement, abstract=True):
    pass


class Part(
    information.AbstractInstance,
    modellingcore.InformationsExchanger,
    DeployableElement,
    DeploymentTarget,
    AbstractPathInvolvedElement,
):
    """A representation of a physical component."""

    _xmltag = "ownedParts"

    deployed_parts = m.Allocation["DeployableElement"](
        "ownedDeploymentLinks",
        (NS, "AbstractDeploymentLink"),
        (NS, "DeployableElement"),
        attr="deployedElement",
        backattr="location",
    )
    type = m.Single["modellingcore.AbstractType"](
        m.Containment("ownedAbstractType", (ns.MODELLINGCORE, "AbstractType"))
    )


class ArchitectureAllocation(capellacore.Allocation, abstract=True):
    pass


class ComponentRealization(capellacore.Allocation):
    """A realization that links to a component."""

    _xmltag = "ownedComponentRealizations"


class InterfacePkg(
    information.communication.MessageReferencePkg,
    capellacore.AbstractDependenciesPkg,
    capellacore.AbstractExchangeItemPkg,
):
    """A container for interface elements."""

    interfaces = m.Containment["Interface"](
        "ownedInterfaces", (NS, "Interface")
    )
    packages = m.Containment["InterfacePkg"](
        "ownedInterfacePkgs", (NS, "InterfacePkg")
    )


class Interface(capellacore.GeneralClass, InterfaceAllocator):
    """An interface."""

    mechanism = m.StringPOD("mechanism")
    is_structural = m.BoolPOD("structural")
    exchange_item_allocations = m.Containment["ExchangeItemAllocation"](
        "ownedExchangeItemAllocations", (NS, "ExchangeItemAllocation")
    )
    allocated_exchange_items = m.Allocation["information.ExchangeItem"](
        "ownedExchangeItemAllocations",
        (NS, "ExchangeItemAllocation"),
        (ns.INFORMATION, "ExchangeItem"),
        attr="allocatedItem",
    )


class InterfaceImplementation(capellacore.Relationship):
    implemented_interface = m.Single["Interface"](
        m.Association((NS, "Interface"), "implementedInterface")
    )


class InterfaceUse(capellacore.Relationship):
    used_interface = m.Single["Interface"](
        m.Association((NS, "Interface"), "usedInterface")
    )


class ProvidedInterfaceLink(capellacore.Relationship, abstract=True):
    interface = m.Single["Interface"](
        m.Association((NS, "Interface"), "interface")
    )


class RequiredInterfaceLink(capellacore.Relationship, abstract=True):
    interface = m.Single["Interface"](
        m.Association((NS, "Interface"), "interface")
    )


class InterfaceAllocation(capellacore.Allocation, abstract=True):
    pass


class ExchangeItemAllocation(
    capellacore.Relationship,
    information.AbstractEventOperation,
    modellingcore.FinalizableElement,
):
    """An allocation of an ExchangeItem to an Interface."""

    send_protocol = m.EnumPOD(
        "sendProtocol", modeltypes.CommunicationLinkProtocol
    )
    receive_protocol = m.EnumPOD(
        "receiveProtocol", modeltypes.CommunicationLinkProtocol
    )
    allocated_item = m.Single["information.ExchangeItem"](
        m.Association((ns.INFORMATION, "ExchangeItem"), "allocatedItem")
    )
    item = m.DeprecatedAccessor["information.ExchangeItem"]("allocated_item")


class AbstractDeploymentLink(capellacore.Relationship, abstract=True):
    deployed_element = m.Single["DeployableElement"](
        m.Association((NS, "DeployableElement"), "deployedElement")
    )
    location = m.Single["DeploymentTarget"](
        m.Association((NS, "DeploymentTarget"), "location")
    )


class AbstractPhysicalArtifact(capellacore.CapellaElement, abstract=True):
    pass


class AbstractPhysicalLinkEnd(capellacore.CapellaElement, abstract=True):
    pass


class AbstractPhysicalPathLink(fa.ComponentExchangeAllocator, abstract=True):
    pass


class PhysicalLink(
    AbstractPhysicalPathLink,
    AbstractPhysicalArtifact,
    AbstractPathInvolvedElement,
):
    """A physical link."""

    ends = m.Association["AbstractPhysicalLinkEnd"](
        (NS, "AbstractPhysicalLinkEnd"), "linkEnds", fixed_length=2
    )
    allocated_functional_exchanges = m.Allocation["fa.FunctionalExchange"](
        "ownedComponentExchangeFunctionalExchangeAllocations",
        (ns.FA, "ComponentExchangeFunctionalExchangeAllocation"),
        (ns.FA, "FunctionalExchange"),
        attr="targetElement",
        backattr="sourceElement",
    )
    physical_link_ends = m.Containment["PhysicalLinkEnd"](
        "ownedPhysicalLinkEnds", (NS, "PhysicalLinkEnd")
    )
    physical_link_realizations = m.Containment["PhysicalLinkRealization"](
        "ownedPhysicalLinkRealizations", (NS, "PhysicalLinkRealization")
    )
    realized_physical_links = m.Allocation["PhysicalLink"](
        "ownedPhysicalLinkRealizations",
        (NS, "PhysicalLinkRealization"),
        (NS, "PhysicalLink"),
        attr="targetElement",
        backattr="sourceElement",
    )
    exchanges = m.DeprecatedAccessor["fa.FunctionalExchange"](
        "allocated_functional_exchanges"
    )
    physical_paths = m.Backref["PhysicalPath"](
        (NS, "PhysicalPath"), "involved_items"
    )

    @property
    def source(self) -> AbstractPhysicalLinkEnd:
        return self.ends[0]

    @source.setter
    def source(self, end: PhysicalPort) -> None:
        self.ends[0] = end

    @property
    def target(self) -> AbstractPhysicalLinkEnd:
        return self.ends[1]

    @target.setter
    def target(self, end: PhysicalPort) -> None:
        self.ends[1] = end


class PhysicalLinkCategory(capellacore.NamedElement):
    links = m.Association["PhysicalLink"]((NS, "PhysicalLink"), "links")


class PhysicalLinkEnd(AbstractPhysicalLinkEnd):
    port = m.Single["PhysicalPort"](
        m.Association((NS, "PhysicalPort"), "port")
    )
    part = m.Single["Part"](m.Association((NS, "Part"), "part"))


class PhysicalLinkRealization(capellacore.Allocation):
    pass


class PhysicalPath(
    fa.ComponentExchangeAllocator,
    AbstractPathInvolvedElement,
    capellacore.InvolverElement,
    capellacore.NamedElement,
):
    """A physical path."""

    _xmltag = "ownedPhysicalPath"

    involved_links = m.Association["AbstractPhysicalPathLink"](
        (NS, "AbstractPhysicalPathLink"), "involvedLinks"
    )
    involved_paths = m.Allocation["AbstractPathInvolvedElement"](
        "ownedPhysicalPathInvolvements",
        (NS, "PhysicalPathInvolvement"),
        (NS, "AbstractPathInvolvedElement"),
        attr="involved",
    )
    involved_items = m.DeprecatedAccessor["AbstractPathInvolvedElement"](
        "involved_paths"
    )
    realized_paths = m.Allocation["PhysicalPath"](
        "ownedPhysicalPathRealizations",
        (NS, "PhysicalPathRealization"),
        (NS, "PhysicalPath"),
        attr="targetElement",
        backattr="sourceElement",
    )
    exchanges = m.DeprecatedAccessor["fa.ComponentExchange"](
        "allocated_exchanges"
    )


class PhysicalPathInvolvement(capellacore.Involvement):
    next_involvements = m.Association["PhysicalPathInvolvement"](
        (NS, "PhysicalPathInvolvement"), "nextInvolvements"
    )


class PhysicalPathReference(PhysicalPathInvolvement):
    pass


class PhysicalPathRealization(capellacore.Allocation):
    pass


class PhysicalPort(
    information.Port,
    AbstractPhysicalArtifact,
    modellingcore.InformationsExchanger,
    AbstractPhysicalLinkEnd,
    information.Property,
):
    """A physical port."""

    _xmltag = "ownedFeatures"

    owner = m.DeprecatedAccessor[m.ModelElement]("parent")
    allocated_component_ports = m.Allocation["fa.ComponentPort"](
        "ownedComponentPortAllocations",
        (ns.FA, "ComponentPortAllocation"),
        (ns.FA, "ComponentPort"),
        attr="targetElement",
        backattr="sourceElement",
    )
    realized_ports = m.Allocation["PhysicalPort"](
        "ownedPhysicalPortRealizations",
        (NS, "PhysicalPortRealization"),
        (NS, "PhysicalPort"),
        attr="targetElement",
        backattr="sourceElement",
    )
    links = m.Backref["PhysicalLink"]((NS, "PhysicalLink"), "ends")


class PhysicalPortRealization(capellacore.Allocation):
    pass


class ComponentPkg(capellacore.Structure, abstract=True):
    parts = m.Containment["Part"]("ownedParts", (NS, "Part"))
    exchanges = m.Containment["fa.ComponentExchange"](
        "ownedComponentExchanges", (ns.FA, "ComponentExchange")
    )
    exchange_categories = m.Containment["fa.ComponentExchangeCategory"](
        "ownedComponentExchangeCategories",
        (ns.FA, "ComponentExchangeCategory"),
    )
    functional_links = m.Containment["fa.ExchangeLink"](
        "ownedFunctionalLinks", (ns.FA, "ExchangeLink")
    )
    allocated_functions = m.Allocation["fa.AbstractFunction"](
        "ownedFunctionalAllocations",
        (ns.FA, "ComponentFunctionalAllocation"),
        (ns.FA, "AbstractFunction"),
        attr="targetElement",
        backattr="sourceElement",
    )
    realized_component_exchanges = m.Allocation["ComponentExchange"](
        "ownedComponentExchangeRealizations",
        (ns.FA, "ComponentExchangeRealization"),
        (ns.FA, "ComponentExchange"),
        attr="targetElement",
        backattr="sourceElement",
    )
    physical_links = m.Containment["PhysicalLink"](
        "ownedPhysicalLinks", (NS, "PhysicalLink")
    )
    physical_link_categories = m.Containment["PhysicalLinkCategory"](
        "ownedPhysicalLinkCategories", (NS, "PhysicalLinkCategory")
    )
    state_machines = m.Containment["capellacommon.StateMachine"](
        "ownedStateMachines", (ns.CAPELLACOMMON, "StateMachine")
    )
