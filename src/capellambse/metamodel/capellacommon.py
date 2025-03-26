# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Classes handling Mode/State-Machines and related content."""

from __future__ import annotations

import enum
import typing as t
import warnings

import capellambse.model as m

from . import behavior, capellacore, modellingcore
from . import namespaces as ns

NS = ns.CAPELLACOMMON

if t.TYPE_CHECKING:
    from . import fa  # noqa: F401


@m.stringy_enum
@enum.unique
class ChangeEventKind(enum.Enum):
    WHEN = "WHEN"


@m.stringy_enum
@enum.unique
class TimeEventKind(enum.Enum):
    AT = "AT"
    """Trigger at a specific time.

    An absolute time trigger is specified with the keyword 'at' followed
    by an expression that evaluates to a time value, such as 'Jan. 1,
    2000, Noon'.
    """
    AFTER = "AFTER"
    """Trigger after a relative time duration has passed.

    A relative time trigger is specified with the keyword 'after'
    followed by an expression that evaluates to a time value, such as
    'after (5 seconds)'.
    """


@m.stringy_enum
@enum.unique
class TransitionKind(enum.Enum):
    INTERNAL = "internal"
    LOCAL = "local"
    EXTERNAL = "external"


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


class CapabilityRealizationInvolvement(capellacore.Involvement):
    pass


class CapabilityRealizationInvolvedElement(
    capellacore.InvolvedElement, abstract=True
):
    pass


class StateMachine(capellacore.CapellaElement, behavior.AbstractBehavior):
    regions = m.Containment["Region"]("ownedRegions", (NS, "Region"))
    connection_points = m.Containment["Pseudostate"](
        "ownedConnectionPoints", (NS, "Pseudostate")
    )


class Region(capellacore.NamedElement):
    _xmltag = "ownedRegions"

    states = m.Containment["AbstractState"](
        "ownedStates", (NS, "AbstractState")
    )
    transitions = m.Containment["StateTransition"](
        "ownedTransitions", (NS, "StateTransition")
    )
    involved_states = m.Association["AbstractState"](
        (NS, "AbstractState"), "involvedStates"
    )

    __modes = m.Filter["Mode"]("states", (NS, "Mode"))

    @property
    def modes(self) -> m.ElementList[Mode]:
        warnings.warn(
            (
                "Region.modes is deprecated, use states instead"
                " (note that states may only contain either States or Modes)"
            ),
            DeprecationWarning,
            stacklevel=2,
        )
        return self.__modes


class AbstractState(
    capellacore.NamedElement, modellingcore.IState, abstract=True
):
    _xmltag = "ownedStates"

    realized_states = m.Allocation["AbstractState"](
        "ownedAbstractStateRealizations",
        (NS, "AbstractStateRealization"),
        (NS, "AbstractState"),
        attr="targetElement",
        backattr="sourceElement",
    )
    realizing_states = m.Backref["AbstractState"](
        (NS, "AbstractState"), "realized_states"
    )
    incoming_transitions = m.Backref["StateTransition"](
        (NS, "StateTransition"), "target"
    )
    outgoing_transitions = m.Backref["StateTransition"](
        (NS, "StateTransition"), "source"
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
        (ns.BEHAVIOR, "AbstractEvent"), "entry", legacy_by_type=True
    )
    entries = m.DeprecatedAccessor["behavior.AbstractEvent"]("entry")
    do_activity = m.Association["behavior.AbstractEvent"](
        (ns.BEHAVIOR, "AbstractEvent"), "doActivity", legacy_by_type=True
    )
    exit = m.Association["behavior.AbstractEvent"](
        (ns.BEHAVIOR, "AbstractEvent"), "exit", legacy_by_type=True
    )
    exits = m.DeprecatedAccessor["behavior.AbstractEvent"]("exit")
    state_invariant = m.Containment["modellingcore.AbstractConstraint"](
        "stateInvariant", (ns.MODELLINGCORE, "AbstractConstraint")
    )
    functions = m.Backref["fa.AbstractFunction"](
        (ns.FA, "AbstractFunction"), "available_in_states"
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

    _xmltag = "ownedTransitions"

    kind = m.EnumPOD("kind", TransitionKind)
    trigger_description = m.StringPOD("triggerDescription")
    guard = m.Single["capellacore.Constraint"](
        m.Association((ns.CAPELLACORE, "Constraint"), "guard")
    )
    source = m.Single["AbstractState"](
        m.Association((NS, "AbstractState"), "source")
    )
    target = m.Single["AbstractState"](
        m.Association((NS, "AbstractState"), "target")
    )
    destination = m.DeprecatedAccessor["AbstractState"]("target")
    effect = m.Association["behavior.AbstractEvent"](
        (ns.BEHAVIOR, "AbstractEvent"), "effect", legacy_by_type=True
    )
    effects = m.DeprecatedAccessor["behavior.AbstractEvent"]("effect")
    triggers = m.Association["behavior.AbstractEvent"](
        (ns.BEHAVIOR, "AbstractEvent"), "triggers", legacy_by_type=True
    )
    realized_transitions = m.Allocation["StateTransition"](
        "ownedStateTransitionRealizations",
        (NS, "StateTransitionRealization"),
        (NS, "StateTransition"),
        attr="targetElement",
        backattr="sourceElement",
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


class AbstractStateRealization(capellacore.Allocation):
    pass


class StateTransitionRealization(capellacore.Allocation):
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


class StateEvent(
    capellacore.NamedElement, behavior.AbstractEvent, abstract=True
):
    expression = m.Association["capellacore.Constraint"](
        (ns.CAPELLACORE, "Constraint"), "expression"
    )
    realized_events = m.Allocation["StateEvent"](
        "ownedStateEventRealizations",
        (NS, "StateEventRealization"),
        (NS, "StateEvent"),
        attr="targetElement",
        backattr="sourceElement",
    )


class ChangeEvent(StateEvent):
    kind = m.EnumPOD("kind", ChangeEventKind)


class TimeEvent(StateEvent):
    kind = m.EnumPOD("kind", TimeEventKind)


if not t.TYPE_CHECKING:

    def __getattr__(name):
        if name == "AbstractStateMode":
            warnings.warn(
                "AbstractStateMode has been renamed to AbstractState",
                DeprecationWarning,
                stacklevel=2,
            )
            return AbstractState

        raise AttributeError(name)
