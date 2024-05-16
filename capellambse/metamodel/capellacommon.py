# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from capellambse import modelv2 as m

from . import behavior, capellacore, modellingcore, modeltypes
from . import namespaces as ns

NS = ns.CAPELLACOMMON


STATES_AND_MODES = (
    (NS, "ChoicePseudoState"),
    (NS, "DeepHistoryPseudoState"),
    (NS, "FinalState"),
    (NS, "ForkPseudoState"),
    (NS, "InitialPseudoState"),
    (NS, "JoinPseudoState"),
    (NS, "Mode"),
    (NS, "ShallowHistoryPseudoState"),
    (NS, "State"),
    (NS, "TerminatePseudoState"),
)


class AbstractCapabilityPkg(capellacore.Structure, abstract=True):
    pass


class GenericTrace(capellacore.Trace):
    key_value_pairs = m.Containment["capellacore.KeyValue"](
        "keyValuePairs", (ns.CAPELLACORE, "KeyValue")
    )


class TransfoLink(GenericTrace):
    pass


class JustificationLink(GenericTrace):
    pass


class CapabilityRealizationInvolvement(capellacore.Involvement): ...


class CapabilityRealizationInvolvedElement(capellacore.InvolvedElement): ...


class StateMachine(capellacore.CapellaElement, behavior.AbstractBehavior):
    """A state machine."""

    regions = m.Containment["Region"]("ownedRegions", (NS, "Region"))
    connection_points = m.Containment["Pseudostate"](
        "ownedConnectionPoints", (NS, "Pseudostate")
    )


class Region(capellacore.NamedElement):
    """A region inside a state machine or state/mode."""

    states = m.Containment["AbstractState"](
        "ownedStates", (NS, "AbstractState")
    )
    transitions = m.Containment["StateTransition"](
        "ownedTransitions", (NS, "StateTransition")
    )
    involved_states = m.Association["AbstractState"](
        "involvedStates", (NS, "AbstractState")
    )


class AbstractState(
    capellacore.NamedElement, modellingcore.IState, abstract=True
):
    realized_states = m.Allocation["AbstractState"](
        (NS, "AbstractStateRealization"),
        ("ownedAbstractStateRealizations", "targetElement", "sourceElement"),
        (NS, "AbstractState"),
    )
    realizing_states = m.Backref["AbstractState"](
        (NS, "AbstractState"), lookup="realized_states"
    )


class State(AbstractState):
    """A situation during which some invariant condition holds.

    A condition of a system or element, as defined by some of its
    properties, which can enable system behaviors and/or structure to
    occur.

    Note: The enabled behavior may include no actions, such as
    associated with a wait state. Also, the condition that defines the
    state may be dependent on one or more previous states.
    """

    regions = m.Containment["Region"]("ownedRegions", (NS, "Region"))
    connection_points = m.Containment["Pseudostate"](
        "ownedConnectionPoints", (NS, "Pseudostate")
    )
    entry = m.Association["behavior.AbstractEvent"](
        "entry", (ns.BEHAVIOR, "AbstractEvent")
    )
    do_activity = m.Association["behavior.AbstractEvent"](
        "doActivity", (ns.BEHAVIOR, "AbstractEvent")
    )
    exit = m.Association["behavior.AbstractEvent"](
        "exit", (ns.BEHAVIOR, "AbstractEvent")
    )
    state_invariant = m.Containment["capellacore.Constraint"](
        "stateInvariant", (ns.CAPELLACORE, "Constraint")
    )


class Mode(State):
    """Characterizes an expected behavior at a point in time.

    A Mode characterizes an expected behaviour through the set of
    functions or elements available at a point in time.
    """


class FinalState(State):
    """Special state signifying that the enclosing region is completed.

    If the enclosing region is directly contained in a state machine and
    all other regions in the state machine also are completed, then it
    means that the entire state machine is completed.
    """


class StateTransition(capellacore.NamedElement, capellacore.Relationship):
    """A directed relationship between a source and target vertex.

    It may be part of a compound transition, which takes the state
    machine from one state configuration to another, representing the
    complete response of the state machine to an occurrence of an event
    of a particular type.
    """

    kind = m.EnumPOD("kind", modeltypes.TransitionKind)
    trigger_description = m.StringPOD("triggerDescription")

    guard = m.Association["capellacore.Constraint"](
        "guard", (ns.CAPELLACORE, "Constraint")
    )
    source = m.Single(
        m.Association["AbstractState"]("source", (NS, "AbstractState"))
    )
    target = m.Single(
        m.Association["AbstractState"]("target", (NS, "AbstractState"))
    )
    effect = m.Association["behavior.AbstractEvent"](
        "effect", (ns.BEHAVIOR, "AbstractEvent")
    )
    triggers = m.Association["behavior.AbstractEvent"](
        "triggers", (ns.BEHAVIOR, "AbstractEvent")
    )
    realized_transitions = m.Allocation["StateTransition"](
        (NS, "StateTransitionRealization"),
        ("ownedStateTransitionRealizations", "targetElement", "sourceElement"),
        (NS, "StateTransition"),
    )


class Pseudostate(AbstractState, abstract=True):
    pass


class InitialPseudoState(Pseudostate):
    pass


class JoinPseudoState(Pseudostate):
    pass


class ForkPseudoState(Pseudostate):
    pass


class ChoicePseudoState(Pseudostate):
    pass


class TerminatePseudoState(Pseudostate):
    pass


class ShallowHistoryPseudoState(Pseudostate):
    pass


class DeepHistoryPseudoState(Pseudostate):
    pass


class EntryPointPseudoState(Pseudostate):
    pass


class ExitPointPseudoState(Pseudostate):
    pass


class StateEventRealization(capellacore.Allocation):
    pass


class StateEvent(capellacore.NamedElement, behavior.AbstractEvent):
    expression = m.Association["capellacore.Constraint"](
        "expression", (ns.CAPELLACORE, "Constraint")
    )
    realized_events = m.Allocation["StateEvent"](
        (NS, "StateEventRealization"),
        ("ownedStateEventRealizations", "targetElement", "sourceElement"),
        (NS, "StateEvent"),
    )


class ChangeEvent(StateEvent):
    kind = m.EnumPOD("kind", modeltypes.ChangeEventKind)


class TimeEvent(StateEvent):
    kind = m.EnumPOD("kind", modeltypes.TimeEventKind)
