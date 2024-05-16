# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import typing as t

from capellambse import modelv2 as m

from . import namespaces as ns

if t.TYPE_CHECKING:
    from . import capellacommon, capellacore, fa, modellingcore

# TODO Check the `enforce` parameters for all `Single` fields


NS = ns.INTERACTION


class Execution(m.ModelElement):
    """An execution."""

    # XXX wildcards
    start = m.Single(
        m.Association["modellingcore.ModelElement"]("start", ("", "")),
        enforce="max",
    )
    finish = m.Single(
        m.Association["modellingcore.ModelElement"]("finish", ("", "")),
        enforce="max",
    )


class StateFragment(Execution):
    """A state fragment."""

    function = m.Single(
        m.Association["modellingcore.ModelElement"](
            "relatedAbstractFunction", ("", "")
        ),
        enforce="max",
    )


class CombinedFragment(Execution):
    """A combined fragment."""

    operator = m.StringPOD("operator")
    # XXX wildcards
    operands = m.Association["modellingcore.ModelElement"](
        "referencedOperands", ("", "")
    )


class InstanceRole(m.ModelElement):
    """An instance role."""

    # XXX wildcards
    instance = m.Single(
        m.Association["modellingcore.ModelElement"](
            "representedInstance", ("", "")
        ),
        enforce="max",
    )


class SequenceMessage(m.ModelElement):
    """A sequence message."""

    # XXX wildcards
    source = m.Single(
        m.Association["modellingcore.ModelElement"]("sendingEnd", ("", "")),
        enforce="max",
    )
    target = m.Single(
        m.Association["modellingcore.ModelElement"]("receivingEnd", ("", "")),
        enforce="max",
    )


class Event(m.ModelElement):
    """Abstract super class of all events in a Scenario."""


class EventOperation(Event):
    """Abstract super class for events about operations."""

    # XXX wildcards
    operation = m.Single(
        m.Association["modellingcore.ModelElement"]("operation", ("", "")),
        enforce="max",
    )


class ExecutionEvent(Event):
    """An execution event."""


class EventSentOperation(EventOperation):
    """An event-sent operation."""


class EventReceiptOperation(EventOperation):
    """An event-receipt operation."""


class Scenario(m.ModelElement):
    """A scenario that holds instance roles."""

    # TODO verify types
    instance_roles = m.Containment["InstanceRole"](
        "ownedInstanceRoles", (NS, "InstanceRole")
    )
    messages = m.Containment["SequenceMessage"](
        "ownedMessages", (NS, "SequenceMessage")
    )
    events = m.Containment["Event"]("ownedEvents", (NS, "Event"))
    fragments = m.Containment["InteractionFragment"](
        "ownedInteractionFragments", (NS, "InteractionFragment")
    )
    time_lapses = m.Containment["Execution"](
        "ownedTimeLapses", (NS, "Execution")
    )
    postcondition = m.Single(
        m.Association["capellacore.Constraint"](
            "postCondition", (ns.CAPELLACORE, "Constraint")
        ),
        enforce="max",
    )
    precondition = m.Single(
        m.Association["capellacore.Constraint"](
            "preCondition", (ns.CAPELLACORE, "Constraint")
        ),
        enforce="max",
    )


class InteractionFragment(m.ModelElement):
    """Abstract super class of all interaction fragments in a Scenario."""

    covered = m.Association["InstanceRole"](
        "coveredInstanceRoles", (NS, "InstanceRole")
    )


class ExecutionEnd(InteractionFragment):
    """An end for an execution."""

    event = m.Single(
        m.Association["Event"]("event", (NS, "Event")),
        enforce="max",
    )


class FragmentEnd(InteractionFragment):
    """An end for a fragment."""


class InteractionOperand(InteractionFragment):
    """An interaction operand."""

    guard = m.Single(
        m.Association["capellacore.Constraint"](
            "guard", (ns.CAPELLACORE, "Constraint")
        ),
        enforce="max",
    )


class InteractionState(InteractionFragment):
    """An interaction state."""

    # XXX wildcards
    state = m.Single(
        m.Association["modellingcore.ModelElement"](
            "relatedAbstractState", ("", "")
        ),
        enforce="max",
    )
    function = m.Single(
        m.Association["modellingcore.ModelElement"](
            "relatedAbstractFunction", ("", "")
        ),
        enforce="max",
    )


class MessageEnd(InteractionFragment):
    """A message end."""

    event = m.Single(
        m.Association["Event"]("event", (NS, "Event")),
        enforce="max",
    )


class Exchange(m.ModelElement):
    """An abstract Exchange."""

    source = m.Todo()  # TODO source = parent


class AbstractCapability(m.ModelElement, abstract=True):
    """Base class for Capabilities."""

    precondition = m.Single(
        m.Association["capellacore.Constraint"](
            "preCondition", (ns.CAPELLACORE, "Constraint")
        ),
        enforce="max",
    )
    postcondition = m.Single(
        m.Association["capellacore.Constraint"](
            "postCondition", (ns.CAPELLACORE, "Constraint")
        ),
        enforce="max",
    )
    scenarios = m.Containment["Scenario"]("ownedScenarios", (NS, "Scenario"))
    extends = m.Allocation["AbstractCapability"](
        (NS, "AbstractCapabilityExtend"),
        ("extends", "extended"),
        (NS, "AbstractCapability"),
    )
    extending = m.Backref["AbstractCapability"](
        (NS, "AbstractCapability"), lookup="extends"
    )
    super = m.Allocation["AbstractCapability"](
        (NS, "AbstractCapabilityGeneralization"),
        ("superGeneralizations", "super"),
        (NS, "AbstractCapability"),
    )
    sub = m.Backref["AbstractCapability"](
        (NS, "AbstractCapability"), lookup="super"
    )
    includes = m.Allocation["AbstractCapability"](
        (NS, "AbstractCapabilityInclude"),
        ("includes", "included"),
        (NS, "AbstractCapability"),
    )
    including = m.Backref["AbstractCapability"](
        (NS, "AbstractCapability"), lookup="includes"
    )
    involved_functional_chains = m.Allocation["fa.FunctionalChain"](
        (NS, "FunctionalChainAbstractCapabilityInvolvement"),
        (
            "ownedFunctionalChainAbstractCapabilityInvolvements",
            "involved",
            "involver",
        ),
        (ns.FA, "FunctionalChain"),
    )
    involved_functions = m.Allocation["fa.AbstractFunction"](
        (NS, "AbstractFunctionAbstractCapabilityInvolvement"),
        (
            "ownedAbstractFunctionAbstractCapabilityInvolvements",
            "involved",
            "involver",
        ),
        (ns.FA, "AbstractFunction"),
    )
    available_in_states = m.Association["capellacommon.State"](
        "availableInStates", (ns.CAPELLACOMMON, "State")
    )
    realized_capabilities = m.Allocation["AbstractCapability"](
        (NS, "AbstractCapabilityRealization"),
        (
            "ownedAbstractCapabilityRealizations",
            "targetElement",
            "sourceElement",
        ),
        (NS, "AbstractCapability"),
    )
    realizing_capabilities = m.Backref["AbstractCapability"](
        (NS, "AbstractCapability"), lookup="realized_capabilities"
    )


class AbstractCapabilityExtend(Exchange):
    """An AbstractCapabilityExtend."""

    # XXX wildcards
    extended = m.Single(
        m.Association["modellingcore.ModelElement"]("extended", ("", "")),
        enforce="max",
    )
    target = m.Single(
        m.Shortcut["modellingcore.ModelElement"]("extended"),
        enforce="max",
    )


class AbstractCapabilityInclude(Exchange):
    """An AbstractCapabilityInclude."""

    # XXX wildcards
    included = m.Single(
        m.Association["modellingcore.ModelElement"]("included", ("", "")),
        enforce="max",
    )
    target = m.Single(
        m.Shortcut["modellingcore.ModelElement"]("included"),
        enforce="max",
    )


class AbstractCapabilityGeneralization(Exchange):
    """An AbstractCapabilityGeneralization."""

    # XXX wildcards
    super = m.Single(
        m.Association["modellingcore.ModelElement"]("super", ("", "")),
        enforce="max",
    )
    target = m.Single(
        m.Shortcut["modellingcore.ModelElement"]("super"),
        enforce="max",
    )


class AbstractInvolvement(m.ModelElement):
    """An abstract Involvement."""

    source = m.Todo()  # TODO source = parent

    # XXX wildcards
    involved = m.Single(
        m.Association["modellingcore.ModelElement"]("involved", ("", "")),
        enforce="max",
    )
    target = m.Single(
        m.Shortcut["modellingcore.ModelElement"]("involved"),
        enforce="max",
    )


class AbstractFunctionAbstractCapabilityInvolvement(AbstractInvolvement):
    """An abstract CapabilityInvolvement linking to SystemFunctions."""
