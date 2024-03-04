# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Implementation of objects and relations for Functional Analysis."""
from __future__ import annotations

import typing as t

from capellambse import model as m

from . import (
    activity,
    behavior,
    capellacore,
    information,
    modellingcore,
    modeltypes,
)
from . import namespaces as ns

if t.TYPE_CHECKING:
    from . import capellacommon, cs, oa

NS = ns.FA


class AbstractFunctionalArchitecture(
    capellacore.ModellingArchitecture, abstract=True
):
    function_pkg = m.Single(
        m.Containment["FunctionPkg"]("ownedFunctionPkg", (NS, "FunctionPkg")),
        enforce=False,
    )
    component_exchanges = m.Containment["ComponentExchange"](
        "ownedComponentExchanges", (NS, "ComponentExchange")
    )
    component_exchange_categories = m.Containment["ComponentExchangeCategory"](
        "ownedComponentExchangeCategories", (NS, "ComponentExchangeCategory")
    )
    # TODO ownedFunctionalLinks
    # TODO ownedFunctionalAllocations
    # TODO ownedComponentExchangeRealizations


class AbstractFunctionalBlock(capellacore.ModellingBlock, abstract=True):
    allocated_functions = m.Allocation["AbstractFunction"](
        (NS, "ComponentFunctionalAllocation"),
        ("ownedFunctionalAllocation", "targetElement", "sourceElement"),
        (NS, "AbstractFunction"),
    )
    component_exchanges = m.Containment["ComponentExchange"](
        "ownedComponentExchanges", (NS, "ComponentExchange")
    )
    component_exchange_categories = m.Containment["ComponentExchangeCategory"](
        "ownedComponentExchangeCategories", (NS, "ComponentExchangeCategory")
    )
    in_exchange_links = m.Association["ExchangeLink"](
        "inExchangeLinks", (NS, "ExchangeLink")
    )
    out_exchange_links = m.Association["ExchangeLink"](
        "outExchangeLinks", (NS, "ExchangeLink")
    )


class FunctionPkg(capellacore.Structure, abstract=True):
    functional_links = m.Containment["ExchangeLink"](
        "ownedFunctionalLinks", (NS, "ExchangeLink")
    )
    exchanges = m.Containment["FunctionalExchangeSpecification"](
        "ownedExchanges", (NS, "FunctionalExchangeSpecification")
    )
    realized_exchanges = m.Allocation["FunctionalExchangeSpecification"](
        (NS, "ExchangeSpecificationRealization"),
        (
            "ownedExchangeSpecificationRealizations",
            "targetElement",
            "sourceElement",
        ),
        (NS, "ExchangeSpecification"),
    )
    categories = m.Containment["ExchangeCategory"](
        "ownedCategories", (NS, "ExchangeCategory")
    )
    function_specifications = m.Containment["FunctionSpecification"](
        "ownedFunctionSpecifications", (NS, "FunctionSpecification")
    )


class FunctionSpecification(capellacore.Namespace, activity.AbstractActivity):
    in_exchange_links = m.Association["ExchangeLink"](
        "inExchangeLinks", (NS, "ExchangeLink")
    )
    out_exchange_links = m.Association["ExchangeLink"](
        "outExchangeLinks", (NS, "ExchangeLink")
    )
    ports = m.Containment["FunctionPort"](
        "ownedFunctionPorts", (NS, "FunctionPort")
    )


class ExchangeCategory(capellacore.NamedElement):
    exchanges = m.Containment["FunctionalExchange"](
        "exchanges", (NS, "FunctionalExchange")
    )


class ExchangeLink(capellacore.NamedRelationship):
    # TODO exchanges
    # TODO exchangeContainmentLinks
    # TODO ownedExchangeContainments
    sources = m.Association["FunctionSpecification"](
        "sources", (NS, "FunctionSpecification")
    )
    destinations = m.Association["FunctionSpecification"](
        "destinations", (NS, "FunctionSpecification")
    )


class ExchangeSpecification(
    capellacore.NamedElement, activity.ActivityExchange, abstract=True
):
    ...
    # TODO link


class FunctionalExchangeSpecification(ExchangeSpecification):
    pass


class FunctionalChain(
    capellacore.NamedElement,
    capellacore.InvolverElement,
    capellacore.InvolvedElement,
):
    kind = m.EnumPOD("kind", modeltypes.FunctionalChainKind)
    involvements = m.Containment["FunctionalChainInvolvement"](
        "ownedFunctionalChainInvolvements",
        (NS, "FunctionalChainInvolvement"),
    )
    realized_chains = m.Allocation["FunctionalChain"](
        (NS, "FunctionalChainRealization"),
        ("ownedFunctionalChainRealizations", "targetElement", "sourceElement"),
        (NS, "FunctionalChain"),
    )
    available_in_states = m.Association["capellacommon.State"](
        "availableInStates", (ns.CAPELLACOMMON, "State")
    )
    precondition = m.Single(
        m.Association["capellacore.Constraint"](
            "preCondition", (ns.CAPELLACORE, "Constraint")
        ),
        enforce=False,
    )
    postcondition = m.Single(
        m.Association["capellacore.Constraint"](
            "postCondition", (ns.CAPELLACORE, "Constraint")
        ),
        enforce=False,
    )
    sequence_nodes = m.Containment["ControlNode"](
        "ownedSequenceNodes", (NS, "ControlNode")
    )
    sequence_links = m.Containment["SequenceLink"](
        "ownedSequenceLinks", (NS, "SequenceLink")
    )


class AbstractFunctionalChainContainer(
    capellacore.CapellaElement, abstract=True
):
    functional_chains = m.Containment["FunctionalChain"](
        "ownedFunctionalChains", (NS, "FunctionalChain")
    )


class FunctionalChainInvolvement(capellacore.Involvement, abstract=True):
    pass


class FunctionalChainReference(FunctionalChainInvolvement):
    involved = m.TypeFilter["FunctionalChain"](None, (NS, "FunctionalChain"))


class FunctionPort(
    information.Port,
    capellacore.TypedElement,
    behavior.AbstractEvent,
    abstract=True,
):
    represented_component_ports = m.Association["ComponentPort"](
        "representedComponentPorts", (NS, "ComponentPort")
    )
    realized_ports = m.TypeFilter["FunctionPort"](  # type: ignore[assignment]
        None, (NS, "FunctionPort")
    )
    allocated_ports = m.TypeFilter["FunctionPort"](  # type: ignore[assignment]
        None, (NS, "FunctionPort")
    )


class FunctionInputPort(FunctionPort, activity.InputPin):
    """A function input port."""

    exchange_items = m.Association["information.ExchangeItem"](
        "incomingExchangeItems", (ns.INFORMATION, "ExchangeItem")
    )
    exchanges = m.Backref["FunctionalExchange"](
        (NS, "FunctionalExchange"), lookup=["source", "target"]
    )


class FunctionOutputPort(FunctionPort, activity.OutputPin):
    """A function output port."""

    exchange_items = m.Association["information.ExchangeItem"](
        "outgoingExchangeItems", (ns.INFORMATION, "ExchangeItem")
    )
    exchanges = m.Backref["FunctionalExchange"](
        (NS, "FunctionalExchange"), lookup=["source", "target"]
    )


class FunctionalExchange(
    capellacore.Relationship,
    capellacore.InvolvedElement,
    activity.ObjectFlow,
    behavior.AbstractEvent,
    information.AbstractEventOperation,
    # NOTE: NamedElement is first in the upstream metamodel,
    # but that would result in an MRO conflict with AbstractEventOperation,
    # which inherits from NamedElement.
    capellacore.NamedElement,
):
    exchange_specifications = m.Association["FunctionalExchangeSpecification"](
        "exchangeSpecifications", (NS, "FunctionalExchangeSpecification")
    )
    exchanged_items = m.Association["information.ExchangeItem"](
        "exchangedItems", (ns.INFORMATION, "ExchangeItem")
    )
    exchange_items = m.Shortcut["information.ExchangeItem"]("exchanged_items")
    realized_functional_exchanges = m.Allocation["FunctionalExchange"](
        (NS, "FunctionalExchangeRealization"),
        (
            "ownedFunctionalExchangeRealizations",
            "targetElement",
            "sourceElement",
        ),
        (NS, "FunctionalExchange"),
    )
    realizing_functional_exchanges = m.Backref["FunctionalExchange"](
        (NS, "FunctionalExchange"), lookup="realized_functional_exchanges"
    )

    owner = m.Single(
        m.Backref["ComponentExchange"](
            (NS, "ComponentExchange"), lookup="allocated_functional_exchanges"
        ),
        enforce="max",
    )
    allocating_component_exchange = m.Single(
        m.Backref["ComponentExchange"](
            (NS, "ComponentExchange"), lookup="allocated_functional_exchanges"
        ),
        enforce="max",
    )


class AbstractFunction(
    capellacore.Namespace,
    capellacore.InvolvedElement,
    information.AbstractInstance,
    AbstractFunctionalChainContainer,
    activity.CallBehaviorAction,
    behavior.AbstractEvent,
    abstract=True,
):
    """An abstract function."""

    kind = m.EnumPOD("kind", modeltypes.FunctionKind, default="FUNCTION")
    condition = m.StringPOD("condition")
    functions = m.Containment["AbstractFunction"](
        "ownedFunctions", (NS, "AbstractFunction")
    )
    realized_functions = m.Allocation["AbstractFunction"](
        (NS, "FunctionRealization"),
        ("ownedFunctionRealizations", "targetElement", "sourceElement"),
        (NS, "AbstractFunction"),
    )
    realizing_functions = m.Backref["AbstractFunction"](
        (NS, "Function"), lookup="realized_functions"
    )
    exchanges = m.Containment["FunctionalExchange"](
        "ownedFunctionalExchanges", (NS, "FunctionalExchange")
    )
    available_in_states = m.Association["capellacommon.State"](
        "availableInStates", (ns.CAPELLACOMMON, "State")
    )


class ComponentExchange(
    behavior.AbstractEvent,
    information.AbstractEventOperation,
    # NOTE: NamedElement comes before ExchangeSpecification in the upstream
    # metamodel, but that would result in an MRO conflict.
    ExchangeSpecification,
    capellacore.NamedElement,
):
    """A functional component exchange."""

    kind = m.EnumPOD("kind", modeltypes.ComponentExchangeKind, default="UNSET")
    is_oriented = m.BoolPOD("oriented")

    allocated_functional_exchanges = m.Allocation["FunctionalExchange"](
        (NS, "ComponentExchangeFunctionalExchangeAllocation"),
        (
            "ownedComponentExchangeFunctionalExchangeAllocations",
            "targetElement",
            "sourceElement",
        ),
        (NS, "FunctionalExchange"),
    )
    realized_component_exchanges = m.Allocation["ComponentExchange"](
        (NS, "ComponentExchangeRealization"),
        (
            "ownedComponentExchangeRealizations",
            "targetElement",
            "sourceElement",
        ),
        (NS, "ComponentExchange"),
    )
    realizing_component_exchanges = m.Backref["ComponentExchange"](
        (NS, "ComponentExchange"), lookup="realized_component_exchanges"
    )
    ends = m.Containment["ComponentExchangeEnd"](
        "ownedComponentExchangeEnds", (NS, "ComponentExchangeEnd")
    )

    ###########################################################################

    allocated_exchange_items = m.Association["information.ExchangeItem"](
        "convoyedInformations", (ns.INFORMATION, "ExchangeItem")
    )

    allocating_physical_links = m.Backref["cs.PhysicalLink"](
        (ns.CS, "PhysicalLink"), lookup="exchanges"
    )
    allocating_physical_paths = m.Backref["cs.PhysicalPath"](
        (ns.CS, "PhysicalPath"), lookup="exchanges"
    )


class ComponentExchangeAllocator(  # FIXME necessary?
    capellacore.NamedElement, abstract=True
): ...


class ComponentExchangeCategory(capellacore.NamedElement):
    exchanges = m.Association["ComponentExchange"](
        "exchanges", (NS, "ComponentExchange")
    )


class ComponentExchangeEnd(
    modellingcore.InformationsExchanger, capellacore.CapellaElement
):
    port = m.Single(
        m.Association["information.Port"]("port", (ns.INFORMATION, "Port")),
        enforce="max",
    )
    part = m.Single(
        m.Association["cs.Part"]("part", (ns.CS, "Part")),
        enforce="max",
    )


class ComponentPort(
    information.Port, modellingcore.InformationsExchanger, information.Property
):
    """A component port."""

    orientation = m.EnumPOD("orientation", modeltypes.OrientationPortKind)
    kind = m.EnumPOD("kind", modeltypes.ComponentPortKind)
    exchanges = m.Backref["ComponentExchange"](
        (NS, "ComponentExchange"), lookup=["source", "target"]
    )
    realized_ports = m.TypeFilter["ComponentPort"](  # type: ignore[assignment]
        None, (NS, "ComponentPort")
    )
    allocated_ports = m.TypeFilter["FunctionPort"](  # type: ignore[assignment]
        None, (NS, "FunctionPort")
    )


class ComponentPortAllocation(capellacore.Allocation):
    ends = m.Containment["ComponentPortAllocationEnd"](
        "ownedComponentPortAllocationEnds", (NS, "ComponentPortAllocationEnd")
    )


class ComponentPortAllocationEnd(capellacore.CapellaElement):
    port = m.Single(
        m.Association["information.Port"]("port", (ns.INFORMATION, "Port")),
        enforce="max",
    )
    part = m.Single(
        m.Association["cs.Part"]("part", (ns.CS, "Part")),
        enforce="max",
    )


class ReferenceHierarchyContext(modellingcore.ModelElement, abstract=True):
    source_reference_hierarchy = m.Association["FunctionalChainReference"](
        "sourceReferenceHierarchy", (NS, "FunctionalChainReference")
    )
    target_reference_hierarchy = m.Association["FunctionalChainReference"](
        "targetReferenceHierarchy", (NS, "FunctionalChainReference")
    )


class FunctionalChainInvolvementLink(
    FunctionalChainInvolvement, ReferenceHierarchyContext
):
    context = m.Association["capellacore.Constraint"](
        "exchangeContext", (ns.CAPELLACORE, "Constraint")
    )
    exchanged_items = m.Association["information.ExchangeItem"](
        "exchangedItems", (ns.INFORMATION, "ExchangeItem")
    )
    source = m.Single(
        m.Association["FunctionalChainInvolvementFunction"](
            "source", (NS, "FunctionalChainInvolvementFunction")
        )
    )
    target = m.Single(
        m.Association["FunctionalChainInvolvementFunction"](
            "target", (NS, "FunctionalChainInvolvementFunction")
        )
    )


class SequenceLink(capellacore.CapellaElement, ReferenceHierarchyContext):
    condition = m.Single(
        m.Association["capellacore.Constraint"](
            "condition", (ns.CAPELLACORE, "Constraint")
        ),
        enforce=False,
    )
    links = m.Association["FunctionalChainInvolvementLink"](
        "links", (NS, "FunctionalChainInvolvementLink")
    )
    source = m.Single(
        m.Association["SequenceLinkEnd"]("source", (NS, "SequenceLinkEnd"))
    )
    target = m.Single(
        m.Association["SequenceLinkEnd"]("target", (NS, "SequenceLinkEnd"))
    )


class SequenceLinkEnd(capellacore.CapellaElement, abstract=True):
    pass


class FunctionalChainInvolvementFunction(
    FunctionalChainInvolvement, SequenceLinkEnd
):
    pass


class ControlNode(SequenceLinkEnd):
    kind = m.EnumPOD("kind", modeltypes.ControlNodeKind)
