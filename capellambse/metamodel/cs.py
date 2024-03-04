# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Implementation of objects and relations for Functional Analysis."""
from __future__ import annotations

import typing as t

from capellambse import model as m

from . import (
    capellacore,
    fa,
    information,
    information_communication,
    modellingcore,
    modeltypes,
)
from . import namespaces as ns

if t.TYPE_CHECKING:
    from . import capellacommon, requirement

NS = ns.CS


class BlockArchitecturePkg(
    capellacore.ModellingArchitecturePkg, abstract=True
):
    """Container package for BlockArchitecture elements."""


class BlockArchitecture(fa.AbstractFunctionalArchitecture, abstract=True):
    requirement_pkgs = m.Containment["requirement.RequirementsPkg"](
        "ownedRequirementPkgs", (ns.REQUIREMENT, "RequirementsPkg")
    )
    capability_pkgs = m.Containment["capellacommon.AbstractCapabilityPkg"](
        "ownedAbstractCapabilityPkgs",
        (ns.CAPELLACOMMON, "AbstractCapabilityPkg"),
    )
    interface_pkg = m.Single(
        m.Containment["InterfacePkg"](
            "ownedInterfacePkg", (NS, "InterfacePkg")
        ),
        enforce="max",
    )
    data_pkg = m.Single(
        m.Containment["information.DataPkg"](
            "ownedDataPkg", (ns.INFORMATION, "DataPkg")
        ),
        enforce="max",
    )


class Block(
    fa.AbstractFunctionalBlock,
    # NOTE: In the upstream metamodel, ModellingBlock comes first,
    # but this would result in an MRO conflict.
    capellacore.ModellingBlock,
    abstract=True,
):
    capability_pkg = m.Single(
        m.Containment["capellacommon.AbstractCapabilityPkg"](
            "ownedAbstractCapabilityPkg",
            (ns.CAPELLACOMMON, "AbstractCapabilityPkg"),
        ),
        enforce="max",
    )
    interface_pkg = m.Single(
        m.Containment["InterfacePkg"](
            "ownedInterfacePkg", (NS, "InterfacePkg")
        ),
        enforce="max",
    )
    data_pkg = m.Single(
        m.Containment["information.DataPkg"](
            "ownedDataPkg", (ns.INFORMATION, "DataPkg")
        ),
        enforce="max",
    )
    state_machines = m.Containment["capellacommon.StateMachine"](
        "ownedStateMachines", (ns.CAPELLACOMMON, "StateMachine")
    )


class ComponentArchitecture(BlockArchitecture, abstract=True):
    pass


class InterfaceAllocator(capellacore.CapellaElement, abstract=True):
    allocated_interfaces = m.Allocation["Interface"](
        (NS, "InterfaceAllocation"),
        ("ownedInterfaceAllocations", "targetElement", "sourceElement"),
        (NS, "Interface"),
    )


class Component(
    Block,
    capellacore.Classifier,
    InterfaceAllocator,
    information_communication.CommunicationLinkExchanger,
    abstract=True,
):
    is_actor = m.BoolPOD("actor")
    is_human = m.BoolPOD("human")

    used_interfaces = m.Allocation["Interface"](
        (NS, "InterfaceUse"),
        ("ownedInterfaceUses", "usedInterface"),
        (NS, "Interface"),
    )
    implemented_interfaces = m.Allocation["Interface"](
        (NS, "InterfaceImplementation"),
        ("ownedInterfaceImplementations", "implementedInterfaces"),
        (NS, "Interface"),
    )
    realized_components: m.RelationshipDescriptor["Component"] = m.Allocation(
        (NS, "ComponentRealization"),
        ("ownedComponentRealizations", "targetElement", "sourceElement"),
        (NS, "Component"),
    )
    physical_paths = m.Containment["PhysicalPath"](
        "ownedPhysicalPath", (NS, "PhysicalPath")
    )
    physical_links = m.Containment["PhysicalLink"](
        "ownedPhysicalLinks", (NS, "PhysicalLink")
    )
    physical_link_categories = m.Containment["PhysicalLinkCategory"](
        "ownedPhysicalLinkCategories", (NS, "PhysicalLinkCategory")
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

    deployed_parts = m.Allocation["Part"](
        (ns.PA_DEPLOYMENT, "PartDeploymentLink"),
        ("ownedDeploymentLinks", "deployedElement", "location"),
        (NS, "Part"),
    )

    owned_type = m.Single(
        m.Containment["modellingcore.AbstractType"](
            "ownedAbstractType", (ns.MODELLINGCORE, "AbstractType")
        ),
        enforce="max",
    )


class InterfacePkg(
    information_communication.MessageReferencePkg,
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
    allocated_item = m.Single(
        m.Association["information.ExchangeItem"](
            "allocatedItem", (ns.INFORMATION, "ExchangeItem")
        )
    )


class AbstractDeploymentLink(capellacore.Relationship, abstract=True):
    """Abstract base class for deployment links on the physical layer."""

    deployed_element = m.Single(
        m.Association["DeployableElement"](
            "deployedElement", (NS, "DeployableElement")
        )
    )
    location = m.Single(
        m.Association["DeploymentTarget"]("location", (NS, "DeploymentTarget"))
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

    # FIXME limit PhysicalLink.ends to exactly 2
    ends = m.Association["PhysicalPort"]("linkEnds", (NS, "PhysicalPort"))
    allocated_functional_exchanges = m.Allocation["fa.FunctionalExchange"](
        (ns.FA, "ComponentExchangeFunctionalExchangeAllocation"),
        (
            "ownedComponentExchangeFunctionalExchangeAllocations",
            "targetElement",
            "sourceElement",
        ),
        (ns.FA, "FunctionalExchange"),
    )
    owned_link_ends = m.Containment["PhysicalLinkEnd"](
        "ownedPhysicalLinkEnds", (NS, "PhysicalLinkEnd")
    )
    realized_physical_links = m.Allocation["PhysicalLink"](
        (NS, "PhysicalLinkRealization"),
        ("ownedPhysicalLinkRealizations", "targetElement", "sourceElement"),
        (NS, "PhysicalLink"),
    )


class PhysicalLinkCategory(capellacore.NamedElement):
    links = m.Association["PhysicalLink"]("links", (NS, "PhysicalLink"))


class PhysicalLinkEnd(AbstractPhysicalLinkEnd):
    port = m.Single(
        m.Association["PhysicalPort"]("port", (NS, "PhysicalPort"))
    )
    part = m.Single(m.Association["Part"]("part", (NS, "Part")))


class PhysicalPath(
    fa.ComponentExchangeAllocator,
    AbstractPathInvolvedElement,
    capellacore.InvolverElement,
    capellacore.NamedElement,
):
    involved_links = m.Association["AbstractPhysicalPathLink"](
        "involvedLinks", (NS, "AbstractPhysicalPathLink")
    )
    involved_paths = m.Allocation["AbstractPathInvolvedElement"](
        (NS, "PhysicalPathInvolvement"),
        ("ownedPhysicalPathInvolvements", "involved"),
        (NS, "AbstractPathInvolvedElement"),
    )
    realized_paths = m.Allocation["PhysicalPath"](
        (NS, "PhysicalPathRealization"),
        ("ownedPhysicalPathRealizations", "targetElement", "sourceElement"),
        (NS, "PhysicalPath"),
    )


class PhysicalPort(
    information.Port,
    AbstractPhysicalArtifact,
    modellingcore.InformationsExchanger,
    AbstractPhysicalLinkEnd,
    information.Property,
):
    allocated_component_ports = m.Allocation["fa.ComponentPort"](
        (ns.FA, "ComponentPortAllocation"),
        ("ownedComponentPortAllocations", "targetElement", "sourceElement"),
        (ns.FA, "ComponentPort"),
    )
    realized_ports = m.TypeFilter["PhysicalPort"](  # type: ignore[assignment]
        None, (NS, "PhysicalPort")
    )


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
        (ns.FA, "ComponentFunctionalAllocation"),
        (
            "ownedComponentFunctionalAllocations",
            "targetElement",
            "sourceElement",
        ),
        (ns.FA, "AbstractFunction"),
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
