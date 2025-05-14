# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import enum

import capellambse.model as m

from . import behavior, modellingcore
from . import namespaces as ns

NS = ns.ACTIVITY


@m.stringy_enum
@enum.unique
class ObjectNodeKind(enum.Enum):
    """The behavior type of the object node with respect to incoming data."""

    UNSPECIFIED = "Unspecified"
    """Used when incoming object node management policy is not specified."""
    NO_BUFFER = "NoBuffer"
    """Discard incoming tokens if they are refused.

    When the "nobuffer" stereotype is applied to object nodes, tokens
    arriving at the node are discarded if they are refused by outgoing
    edges, or refused by actions for object nodes that are input pins.
    """
    OVERWRITE = "Overwrite"
    """Incoming tokens may overwrite existing ones.

    When the "overwrite" stereotype is applied to object nodes, a token
    arriving at a full object node replaces the ones already there. A
    full object node has as many tokens as allowed by its upper bound.
    """


@m.stringy_enum
@enum.unique
class ObjectNodeOrderingKind(enum.Enum):
    """Indicates queuing order within a node."""

    FIFO = "FIFO"
    """First In First Out ordering."""
    LIFO = "LIFO"
    """Last In First Out ordering."""
    ORDERED = "ordered"
    """Indicates that object node tokens are ordered."""
    UNORDERED = "unordered"
    """Indicates that object node tokens are unordered."""


class AbstractActivity(
    behavior.AbstractBehavior, modellingcore.TraceableElement, abstract=True
):
    is_read_only = m.BoolPOD("isReadOnly")
    is_single_execution = m.BoolPOD("isSingleExecution")
    nodes = m.Containment["ActivityNode"]("ownedNodes", (NS, "ActivityNode"))
    edges = m.Containment["ActivityEdge"]("ownedEdges", (NS, "ActivityEdge"))
    groups = m.Containment["ActivityGroup"](
        "ownedGroups", (NS, "ActivityGroup")
    )


class ExceptionHandler(modellingcore.ModelElement, abstract=True):
    protected_node = m.Single["ExecutableNode"](
        m.Association((NS, "ExecutableNode"), "protectedNode")
    )
    handler_body = m.Single["ExecutableNode"](
        m.Association((NS, "ExecutableNode"), "handlerBody")
    )
    exception_input = m.Single["ObjectNode"](
        m.Association((NS, "ObjectNode"), "exceptionInput")
    )
    exception_types = m.Association["modellingcore.AbstractType"](
        (ns.MODELLINGCORE, "AbstractType"), "exceptionTypes"
    )


class ActivityGroup(modellingcore.ModelElement, abstract=True):
    super_group = m.Association["ActivityGroup"](
        (NS, "ActivityGroup"), "superGroup"
    )
    sub_groups = m.Containment["ActivityGroup"](
        "subGroups", (NS, "ActivityGroup")
    )
    nodes = m.Containment["ActivityNode"]("ownedNodes", (NS, "ActivityNode"))
    edges = m.Containment["ActivityEdge"]("ownedEdges", (NS, "ActivityEdge"))


class InterruptibleActivityRegion(ActivityGroup, abstract=True):
    interrupting_edges = m.Association["ActivityEdge"](
        (NS, "ActivityEdge"), "interruptingEdges"
    )


class ActivityEdge(modellingcore.AbstractRelationship, abstract=True):
    rate_kind = m.EnumPOD("kindOfRate", modellingcore.RateKind)
    rate = m.Containment["modellingcore.ValueSpecification"](
        "rate", (ns.MODELLINGCORE, "ValueSpecification")
    )
    probability = m.Containment["modellingcore.ValueSpecification"](
        "probability", (ns.MODELLINGCORE, "ValueSpecification")
    )
    target = m.Single["ActivityNode"](
        m.Association((NS, "ActivityNode"), "target")
    )
    source = m.Single["ActivityNode"](
        m.Association((NS, "ActivityNode"), "source")
    )
    guard = m.Containment["modellingcore.ValueSpecification"](
        "guard", (ns.MODELLINGCORE, "ValueSpecification")
    )
    weight = m.Containment["modellingcore.ValueSpecification"](
        "weight", (ns.MODELLINGCORE, "ValueSpecification")
    )
    interrupts = m.Association["InterruptibleActivityRegion"](
        (NS, "InterruptibleActivityRegion"), "interrupts"
    )


class ControlFlow(ActivityEdge, abstract=True):
    """An edge that starts an activity node after the previous one finished."""


class ObjectFlow(ActivityEdge, abstract=True):
    """Models the flow of values to or from object nodes."""

    is_multicast = m.BoolPOD("isMulticast")
    is_multireceive = m.BoolPOD("isMultireceive")
    transformation = m.Single["behavior.AbstractBehavior"](
        m.Association((ns.BEHAVIOR, "AbstractBehavior"), "transformation")
    )
    selection = m.Single["behavior.AbstractBehavior"](
        m.Association((ns.BEHAVIOR, "AbstractBehavior"), "selection")
    )


class ActivityPartition(
    ActivityGroup, modellingcore.AbstractNamedElement, abstract=True
):
    is_dimension = m.BoolPOD("isDimension")
    is_external = m.BoolPOD("isExternal")
    represented_element = m.Single["modellingcore.AbstractType"](
        m.Association((ns.MODELLINGCORE, "AbstractType"), "representedElement")
    )


class ActivityExchange(modellingcore.AbstractInformationFlow, abstract=True):
    pass


class ActivityNode(modellingcore.AbstractNamedElement, abstract=True):
    pass


class ExecutableNode(ActivityNode, abstract=True):
    handlers = m.Containment["ExceptionHandler"](
        "ownedHandlers", (NS, "ExceptionHandler")
    )


class AbstractAction(
    ExecutableNode, modellingcore.AbstractNamedElement, abstract=True
):
    local_precondition = m.Single["modellingcore.AbstractConstraint"](
        m.Containment(
            "localPrecondition", (ns.MODELLINGCORE, "AbstractConstraint")
        )
    )
    local_postcondition = m.Single["modellingcore.AbstractConstraint"](
        m.Containment(
            "localPostcondition", (ns.MODELLINGCORE, "AbstractConstraint")
        )
    )
    context = m.Association["modellingcore.AbstractType"](
        (ns.MODELLINGCORE, "AbstractType"), "context"
    )
    inputs = m.Containment["InputPin"]("inputs", (NS, "InputPin"))
    outputs = m.Containment["OutputPin"]("outputs", (NS, "OutputPin"))


class StructuredActivityNode(ActivityGroup, AbstractAction, abstract=True):
    pass


class AcceptEventAction(AbstractAction, abstract=True):
    is_unmarshall = m.BoolPOD("isUnmarshall")
    result = m.Containment["OutputPin"]("result", (NS, "OutputPin"))


class InvocationAction(AbstractAction, abstract=True):
    arguments = m.Containment["InputPin"]("arguments", (NS, "InputPin"))


class SendSignalAction(InvocationAction, abstract=True):
    target = m.Single["InputPin"](m.Containment("target", (NS, "InputPin")))
    signal = m.Single["behavior.AbstractSignal"](
        m.Association((ns.BEHAVIOR, "AbstractSignal"), "signal")
    )


class CallAction(InvocationAction, abstract=True):
    results = m.Containment["OutputPin"]("results", (NS, "OutputPin"))


class CallBehaviorAction(CallAction, abstract=True):
    behavior = m.Single["behavior.AbstractBehavior"](
        m.Association((ns.BEHAVIOR, "AbstractBehavior"), "behavior")
    )


class ObjectNode(
    ActivityNode, modellingcore.AbstractTypedElement, abstract=True
):
    is_control_type = m.BoolPOD("isControlType")
    node_kind = m.EnumPOD("kindOfNode", ObjectNodeKind)
    ordering = m.EnumPOD("ordering", ObjectNodeOrderingKind)
    upper_bound = m.Containment["modellingcore.ValueSpecification"](
        "upperBound", (ns.MODELLINGCORE, "ValueSpecification")
    )
    in_state = m.Association["modellingcore.IState"](
        (ns.MODELLINGCORE, "IState"), "inState"
    )
    selection = m.Single["behavior.AbstractBehavior"](
        m.Association((ns.BEHAVIOR, "AbstractBehavior"), "selection")
    )


class Pin(ObjectNode, abstract=True):
    is_control = m.BoolPOD("isControl")


class InputPin(Pin, abstract=True):
    input_evaluation_action = m.Single["AbstractAction"](
        m.Association((NS, "AbstractAction"), "inputEvaluationAction")
    )


class ValuePin(InputPin, abstract=True):
    value = m.Single["modellingcore.ValueSpecification"](
        m.Containment("value", (ns.MODELLINGCORE, "ValueSpecification"))
    )


class OutputPin(Pin, abstract=True):
    pass
