# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Implementation of objects and relations for Functional Analysis."""

from __future__ import annotations

import typing as t
import warnings

import capellambse.model as m

from . import capellacore, fa, information, modellingcore
from . import namespaces as ns

NS = ns.CS


class BlockArchitecturePkg(
    capellacore.ModellingArchitecturePkg, abstract=True
):
    """Container package for BlockArchitecture elements."""


class BlockArchitecture(fa.AbstractFunctionalArchitecture, abstract=True):
    """Parent class for deriving specific architectures for each design phase.

    Formerly known as BaseArchitectureLayer.
    """

    capability_pkg = m.Single["capellacommon.AbstractCapabilityPkg"](
        m.Containment(
            "ownedAbstractCapabilityPkg",
            (ns.CAPELLACOMMON, "AbstractCapabilityPkg"),
        )
    )
    interface_pkg = m.Single["InterfacePkg"](
        m.Containment("ownedInterfacePkg", (NS, "InterfacePkg"))
    )
    data_pkg = m.Single["information.DataPkg"](
        m.Containment("ownedDataPkg", (ns.INFORMATION, "DataPkg"))
    )

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
    ) -> m.ElementList[information.datavalue.AbstractComplexValue]:
        return self._model.search(
            (ns.INFORMATION_DATAVALUE, "AbstractComplexValue"), below=self
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

    if not t.TYPE_CHECKING:
        capability_package = m.DeprecatedAccessor("capability_pkg")
        interface_package = m.DeprecatedAccessor("interface_pkg")
        data_package = m.DeprecatedAccessor("data_pkg")


class Block(
    fa.AbstractFunctionalBlock,
    # NOTE: In the upstream metamodel, ModellingBlock comes first,
    # but this would result in an MRO conflict.
    capellacore.ModellingBlock,
    abstract=True,
):
    """A modular unit that describes the structure of a system or element."""

    capability_pkg = m.Single["capellacommon.AbstractCapabilityPkg"](
        m.Containment(
            "ownedAbstractCapabilityPkg",
            (ns.CAPELLACOMMON, "AbstractCapabilityPkg"),
        )
    )
    interface_pkg = m.Single["InterfacePkg"](
        m.Containment("ownedInterfacePkg", (NS, "InterfacePkg"))
    )
    data_pkg = m.Single["information.DataPkg"](
        m.Containment("ownedDataPkg", (ns.INFORMATION, "DataPkg"))
    )
    state_machines = m.Containment["capellacommon.StateMachine"](
        "ownedStateMachines", (ns.CAPELLACOMMON, "StateMachine")
    )

    if not t.TYPE_CHECKING:
        interface_package = m.DeprecatedAccessor("interface_pkg")
        data_package = m.DeprecatedAccessor("data_pkg")


class ComponentArchitecture(BlockArchitecture, abstract=True):
    """A specialized kind of BlockArchitecture.

    Serves as a parent class for the various architecture levels, from
    System analysis down to EPBS architecture.
    """


class InterfaceAllocator(capellacore.CapellaElement, abstract=True):
    interface_allocations = m.Containment["InterfaceAllocation"](
        "ownedInterfaceAllocations", (NS, "InterfaceAllocation")
    )
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
    """An entity, with discrete structure within the system.

    Interacts with other Components of the system, thereby contributing
    at its lowest level to the system properties and characteristics.
    """

    is_actor = m.BoolPOD("actor")
    """Indicates if the Component is an Actor."""
    is_human = m.BoolPOD("human")
    """Indicates whether the Component is a Human."""
    interface_uses = m.Containment["InterfaceUse"](
        "ownedInterfaceUses", (NS, "InterfaceUse")
    )
    used_interfaces = m.Allocation["Interface"](
        "ownedInterfaceUses",
        (NS, "InterfaceUse"),
        (NS, "Interface"),
        attr="usedInterface",
    )
    interface_implementations = m.Containment["InterfaceImplementation"](
        "ownedInterfaceImplementations", (NS, "InterfaceImplementation")
    )
    implemented_interfaces = m.Allocation["Interface"](
        "ownedInterfaceImplementations",
        (NS, "InterfaceImplementation"),
        (NS, "Interface"),
        attr="implementedInterfaces",
    )
    component_realizations = m.Containment["ComponentRealization"](
        "ownedComponentRealizations", (NS, "ComponentRealization")
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
    ports = m.Filter["fa.ComponentPort"](
        "owned_features", (ns.FA, "ComponentPort")
    )
    physical_ports = m.Filter["PhysicalPort"](
        "owned_features", (NS, "PhysicalPort")
    )
    parts = m.Backref["Part"]((NS, "Part"), "type")
    physical_paths = m.Containment["PhysicalPath"](
        "ownedPhysicalPath", (NS, "PhysicalPath")
    )
    physical_links = m.Containment["PhysicalLink"](
        "ownedPhysicalLinks", (NS, "PhysicalLink")
    )
    physical_link_categories = m.Containment["PhysicalLinkCategory"](
        "ownedPhysicalLinkCategories", (NS, "PhysicalLinkCategory")
    )
    related_exchanges = m.Backref["fa.ComponentExchange"](
        (ns.FA, "ComponentExchange"),
        "source",
        "source.owner",
        "target",
        "target.owner",
    )

    if not t.TYPE_CHECKING:
        owner = m.DeprecatedAccessor("parent")
        exchanges = m.DeprecatedAccessor("component_exchanges")


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
    """A representation of a physical component.

    In SysML, a Part is an owned property of a Block.
    """

    _xmltag = "ownedParts"

    deployment_links = m.Containment["AbstractDeploymentLink"](
        "ownedDeploymentLinks", (NS, "AbstractDeploymentLink")
    )
    deployed_parts = m.Allocation["DeployableElement"](
        "ownedDeploymentLinks",
        (NS, "AbstractDeploymentLink"),
        (NS, "DeployableElement"),
        attr="deployedElement",
        backattr="location",
    )
    owned_type = m.Single["modellingcore.AbstractType"](
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
    """A container for Interface elements."""

    interfaces = m.Containment["Interface"](
        "ownedInterfaces", (NS, "Interface")
    )
    packages = m.Containment["InterfacePkg"](
        "ownedInterfacePkgs", (NS, "InterfacePkg")
    )


class Interface(capellacore.GeneralClass, InterfaceAllocator):
    """An interface.

    An interface is a kind of classifier that represents a declaration of a set
    of coherent public features and obligations. An interface specifies a
    contract; any instance of a classifier that realizes the interface must
    fulfill that contract.

    Interfaces are defined by functional and physical characteristics that
    exist at a common boundary with co-functioning items and allow systems,
    equipment, software, and system data to be compatible.

    That design feature of one piece of equipment that affects a design feature
    of another piece of equipment. An interface can extend beyond the physical
    boundary between two items. (For example, the weight and center of gravity
    of one item can affect the interfacing item; however, the center of gravity
    is rarely located at the physical boundary. An electrical interface
    generally extends to the first isolating element rather than terminating at
    a series of connector pins.)

    Usage guideline
    ---------------
    In Capella, Interfaces are created to declare the nature of interactions
    between the System and external actors.
    """

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
        "sendProtocol", information.communication.CommunicationLinkProtocol
    )
    receive_protocol = m.EnumPOD(
        "receiveProtocol", information.communication.CommunicationLinkProtocol
    )
    allocated_item = m.Single["information.ExchangeItem"](
        m.Association((ns.INFORMATION, "ExchangeItem"), "allocatedItem")
    )

    if not t.TYPE_CHECKING:
        item = m.DeprecatedAccessor("allocated_item")


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
    ends = m.Association["AbstractPhysicalLinkEnd"](
        (NS, "AbstractPhysicalLinkEnd"), "linkEnds", fixed_length=2
    )
    functional_exchange_allocations = m.Containment[
        "fa.ComponentExchangeFunctionalExchangeAllocation"
    ](
        "ownedComponentExchangeFunctionalExchangeAllocations",
        (ns.FA, "ComponentExchangeFunctionalExchangeAllocation"),
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
    physical_paths = m.Backref["PhysicalPath"](
        (NS, "PhysicalPath"), "involved_items"
    )

    @property
    def source(self) -> AbstractPhysicalLinkEnd | None:
        try:
            return self.ends[0]
        except IndexError:
            return None

    @source.setter
    def source(self, end: AbstractPhysicalLinkEnd | None) -> None:
        if end is None:
            raise TypeError(f"Cannot delete 'source' of {type(self).__name__}")

        ends = self.ends
        if len(ends) == 0:
            ends.append(end)
        else:
            ends[0] = end

    @property
    def target(self) -> AbstractPhysicalLinkEnd | None:
        try:
            return self.ends[1]
        except IndexError:
            return None

    @target.setter
    def target(self, end: AbstractPhysicalLinkEnd | None) -> None:
        if end is None:
            raise TypeError(f"Cannot delete 'target' of {type(self).__name__}")

        ends = self.ends
        if len(ends) == 0:
            raise TypeError(
                f"Cannot set 'target' on a {type(self).__name__}"
                " that has no 'source'"
            )
        if len(ends) == 1:
            ends.append(end)
        else:
            ends[1] = end

    def links(self) -> m.ElementList[m.ModelElement]:
        warnings.warn(
            "PhysicalLink.links is deprecated and will be removed soon",
            category=FutureWarning,
            stacklevel=2,
        )
        return m.ElementList(self._model, [])

    if not t.TYPE_CHECKING:
        exchanges = m.DeprecatedAccessor("allocated_component_exchanges")
        owner = m.DeprecatedAccessor("parent")


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

    _involved_links = m.Association["AbstractPhysicalPathLink"](
        (NS, "AbstractPhysicalPathLink"), "involvedLinks"
    )
    physical_path_involvements = m.Containment["PhysicalPathInvolvement"](
        "ownedPhysicalPathInvolvements", (NS, "PhysicalPathInvolvement")
    )
    involved_items = m.Allocation["AbstractPathInvolvedElement"](
        "ownedPhysicalPathInvolvements",
        (NS, "PhysicalPathInvolvement"),
        (NS, "AbstractPathInvolvedElement"),
        attr="involved",
        legacy_by_type=True,
    )
    physical_path_realizations = m.Containment["PhysicalPathRealization"](
        "ownedPhysicalPathRealizations", (NS, "PhysicalPathRealization")
    )
    realized_paths = m.Allocation["PhysicalPath"](
        "ownedPhysicalPathRealizations",
        (NS, "PhysicalPathRealization"),
        (NS, "PhysicalPath"),
        attr="targetElement",
        backattr="sourceElement",
    )
    involved_links = m.Filter["PhysicalLink"](
        "involved_items", (NS, "PhysicalLink")
    )

    if not t.TYPE_CHECKING:
        exchanges = m.DeprecatedAccessor("allocated_component_exchanges")


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
    """A port on a physical component."""

    _xmltag = "ownedFeatures"

    component_port_allocations = m.Containment["fa.ComponentPortAllocation"](
        "ownedComponentPortAllocations",
        (ns.FA, "ComponentPortAllocation"),
    )
    allocated_component_ports = m.Allocation["fa.ComponentPort"](
        "ownedComponentPortAllocations",
        (ns.FA, "ComponentPortAllocation"),
        (ns.FA, "ComponentPort"),
        attr="targetElement",
        backattr="sourceElement",
    )
    physical_port_realizations = m.Containment["PhysicalPortRealization"](
        "ownedPhysicalPortRealizations", (NS, "PhysicalPortRealization")
    )
    realized_ports = m.Allocation["PhysicalPort"](
        "ownedPhysicalPortRealizations",
        (NS, "PhysicalPortRealization"),
        (NS, "PhysicalPort"),
        attr="targetElement",
        backattr="sourceElement",
    )
    links = m.Backref["PhysicalLink"]((NS, "PhysicalLink"), "ends")

    if not t.TYPE_CHECKING:
        owner = m.DeprecatedAccessor("parent")


class PhysicalPortRealization(capellacore.Allocation):
    pass


class ComponentPkg(capellacore.Structure, abstract=True):
    """A package containing parts."""

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
    functional_allocations = m.Containment["fa.ComponentFunctionalAllocation"](
        "ownedFunctionalAllocations",
        (ns.FA, "ComponentFunctionalAllocation"),
    )
    allocated_functions = m.Allocation["fa.AbstractFunction"](
        "ownedFunctionalAllocations",
        (ns.FA, "ComponentFunctionalAllocation"),
        (ns.FA, "AbstractFunction"),
        attr="targetElement",
        backattr="sourceElement",
    )
    component_exchange_realizations = m.Containment[
        "fa.ComponentExchangeRealization"
    ](
        "ownedComponentExchangeRealizations",
        (ns.FA, "ComponentExchangeRealization"),
    )
    realized_component_exchanges = m.Allocation["fa.ComponentExchange"](
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


from . import capellacommon, interaction  # noqa: F401
