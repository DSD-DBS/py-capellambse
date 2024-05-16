# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from capellambse import modelv2 as m

from . import behavior, modellingcore, modeltypes
from . import namespaces as ns

NS = ns.ACTIVITY


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
    protected_node = m.Single(
        m.Association["ExecutableNode"](
            "protectedNodes", (NS, "ExecutableNode")
        ),
        enforce="min",
    )
    handler_body = m.Single(
        m.Association["ExecutableNode"]("handlerBody", (NS, "ExecutableNode")),
        enforce="min",
    )
    exception_input = m.Single(
        m.Association["ObjectNode"]("exceptionInput", (NS, "ObjectNode")),
        enforce="min",
    )
    exception_types = m.Association["modellingcore.AbstractType"](
        "exceptionTypes", (ns.MODELLINGCORE, "AbstractType")
    )


class ActivityGroup(modellingcore.ModelElement, abstract=True):
    # TODO superGroup
    # TODO subGroups

    nodes = m.Containment["ActivityNode"]("ownedNodes", (NS, "ActivityNode"))
    edges = m.Containment["ActivityEdge"]("ownedEdges", (NS, "ActivityEdge"))


class InterruptibleActivityRegion(ActivityGroup, abstract=True):
    interrupting_edges = m.Association["ActivityEdge"](
        "interruptingEdges", (NS, "ActivityEdge")
    )


class ActivityEdge(modellingcore.AbstractRelationship, abstract=True):
    rate_kind = m.EnumPOD("kindOfRate", modeltypes.RateKind)
    rate = m.Containment["modellingcore.ValueSpecification"](
        "rate", (ns.MODELLINGCORE, "ValueSpecification")
    )
    probability = m.Containment["modellingcore.ValueSpecification"](
        "probability", (ns.MODELLINGCORE, "ValueSpecification")
    )
    target = m.Single(
        m.Association["ActivityNode"]("target", (NS, "ActivityNode"))
    )
    source = m.Single(
        m.Association["ActivityNode"]("source", (NS, "ActivityNode"))
    )
    guard = m.Containment["modellingcore.ValueSpecification"](
        "guard", (ns.MODELLINGCORE, "ValueSpecification")
    )
    weight = m.Containment["modellingcore.ValueSpecification"](
        "weight", (ns.MODELLINGCORE, "ValueSpecification")
    )
    interrupts = m.Association["InterruptibleActivityRegion"](
        "interrupts", (NS, "InterruptibleActivityRegion")
    )


class ControlFlow(ActivityEdge, abstract=True):
    """An edge that starts an activity node after the previous one finished."""


class ObjectFlow(ActivityEdge, abstract=True):
    """Models the flow of values to or from object nodes."""

    is_multicast = m.BoolPOD("isMulticast")
    is_multireceive = m.BoolPOD("isMultireceive")
    transformation = m.Single(
        m.Association["behavior.AbstractBehavior"](
            "transformation", (ns.BEHAVIOR, "AbstractBehavior")
        ),
        enforce="max",
    )
    selection = m.Single(
        m.Association["behavior.AbstractBehavior"](
            "selection", (ns.BEHAVIOR, "AbstractBehavior")
        ),
        enforce="max",
    )


class ActivityPartition(
    ActivityGroup, modellingcore.AbstractNamedElement, abstract=True
):
    is_dimension = m.BoolPOD("isDimension")
    is_external = m.BoolPOD("isExternal")
    represented_element = m.Single(
        m.Association["modellingcore.AbstractType"](
            "representedElement", (ns.MODELLINGCORE, "AbstractType")
        ),
        enforce="max",
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
    preconditions = m.Containment["modellingcore.AbstractConstraint"](
        "localPrecondition", (ns.MODELLINGCORE, "AbstractConstraint")
    )
    postcondition = m.Containment["modellingcore.AbstractConstraint"](
        "localPostcondition", (ns.MODELLINGCORE, "AbstractConstraint")
    )
    context = m.Association["modellingcore.AbstractType"](
        "context", (ns.MODELLINGCORE, "AbstractType")
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
    target = m.Single(
        m.Association["InputPin"]("target", (NS, "InputPin")),
        enforce="min",
    )
    signal = m.Single(
        m.Association["behavior.AbstractSignal"](
            "signal", (ns.BEHAVIOR, "AbstractSignal")
        ),
        enforce="min",
    )


class CallAction(InvocationAction, abstract=True):
    results = m.Containment["OutputPin"]("results", (NS, "OutputPin"))


class CallBehaviorAction(CallAction, abstract=True):
    behavior = m.Single(
        m.Association["behavior.AbstractBehavior"](
            "behavior", (ns.BEHAVIOR, "AbstractBehavior")
        ),
        enforce=False,
    )


class ObjectNode(
    ActivityNode, modellingcore.AbstractTypedElement, abstract=True
):
    is_control_type = m.BoolPOD("isControlType")
    node_kind = m.EnumPOD("kindOfNode", modeltypes.ObjectNodeKind)
    ordering = m.EnumPOD("ordering", modeltypes.ObjectNodeOrderingKind)
    upper_bound = m.Containment["modellingcore.ValueSpecification"](
        "upperBound", (ns.MODELLINGCORE, "ValueSpecification")
    )
    in_state = m.Association["modellingcore.IState"](
        "inState", (ns.MODELLINGCORE, "IState")
    )
    selection = m.Single(
        m.Association["behavior.AbstractBehavior"](
            "selection", (ns.BEHAVIOR, "AbstractBehavior")
        ),
        enforce="max",
    )


class Pin(ObjectNode, abstract=True):
    is_control = m.BoolPOD("isControl")


class InputPin(Pin, abstract=True):
    input_evaluation_action = m.Single(
        m.Association["AbstractAction"](
            "inputEvaluationAction", (NS, "AbstractAction")
        ),
        enforce="max",
    )


class ValuePin(InputPin, abstract=True):
    value = m.Single(
        m.Containment["modellingcore.ValueSpecification"](
            "value", (ns.MODELLINGCORE, "ValueSpecification")
        ),
        enforce="max",
    )


class OutputPin(Pin, abstract=True):
    pass
