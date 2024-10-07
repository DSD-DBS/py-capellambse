# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import enum
import sys
import typing as t
import warnings

import capellambse.model as m

from . import behavior, capellacore, modellingcore
from . import namespaces as ns

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

NS = ns.CAPELLACOMMON


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

    @property
    @deprecated("Synthetic names are deprecated", category=FutureWarning)
    def name(self) -> str:
        myname = type(self).__name__
        if self.target is not None:
            tgname = self.target.name
            tguuid = self.target.uuid
        else:
            tgname = tguuid = "<no target>"
        return f"[{myname}] to {tgname} ({tguuid})"


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

    state_realizations = m.Containment["AbstractStateRealization"](
        "ownedAbstractStateRealizations", (NS, "AbstractStateRealization")
    )
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

    if not t.TYPE_CHECKING:

        @property
        def regions(self) -> m.ElementList[Region]:
            myname = AbstractState.__name__
            if type(self) is not AbstractState:
                myname = f"{type(self).__name__}, a subclass of {AbstractState.__name__},"
            warnings.warn(
                (
                    f"{myname} cannot contain regions directly,"
                    f" use the concrete {State.__name__!r} class instead"
                ),
                category=FutureWarning,
                stacklevel=2,
            )
            return m.ElementList(self._model, [], Region)


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
    do_activity = m.Association["behavior.AbstractEvent"](
        (ns.BEHAVIOR, "AbstractEvent"), "doActivity", legacy_by_type=True
    )
    exit = m.Association["behavior.AbstractEvent"](
        (ns.BEHAVIOR, "AbstractEvent"), "exit", legacy_by_type=True
    )
    state_invariant = m.Containment["modellingcore.AbstractConstraint"](
        "stateInvariant", (ns.MODELLINGCORE, "AbstractConstraint")
    )
    functions = m.Backref["fa.AbstractFunction"](
        (ns.FA, "AbstractFunction"), "available_in_states"
    )

    if not t.TYPE_CHECKING:
        entries = m.DeprecatedAccessor("entry")
        exits = m.DeprecatedAccessor("exit")


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
    effect = m.Association["behavior.AbstractEvent"](
        (ns.BEHAVIOR, "AbstractEvent"), "effect", legacy_by_type=True
    )
    triggers = m.Association["behavior.AbstractEvent"](
        (ns.BEHAVIOR, "AbstractEvent"), "triggers", legacy_by_type=True
    )
    state_transition_realizations = m.Containment[
        "StateTransitionRealization"
    ]("ownedStateTransitionRealizations", (NS, "StateTransitionRealization"))
    realized_transitions = m.Allocation["StateTransition"](
        "ownedStateTransitionRealizations",
        (NS, "StateTransitionRealization"),
        (NS, "StateTransition"),
        attr="targetElement",
        backattr="sourceElement",
    )

    if not t.TYPE_CHECKING:
        destination = m.DeprecatedAccessor("target")
        effects = m.DeprecatedAccessor("effect")


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
    state_event_realizations = m.Containment["StateEventRealization"](
        "ownedStateEventRealizations", (NS, "StateEventRealization")
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


from . import fa  # noqa: F401
