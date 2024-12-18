# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Classes handling Mode/State-Machines and related content."""

from __future__ import annotations

import typing as t

import capellambse.model as m

from . import capellacore, modellingcore
from . import namespaces as ns

NS = ns.CAPELLACOMMON


class AbstractStateRealization(m.ModelElement): ...


class TransfoLink(m.ModelElement): ...


class CapabilityRealizationInvolvement(m.ModelElement): ...


class Region(m.ModelElement):
    """A region inside a state machine or state/mode."""

    _xmltag = "ownedRegions"

    states: m.Accessor
    modes: m.Accessor
    transitions: m.Accessor


class AbstractStateMode(m.ModelElement):
    """Common code for states and modes."""

    _xmltag = "ownedStates"

    regions = m.DirectProxyAccessor(Region, aslist=m.ElementList)


class State(AbstractStateMode):
    """A state."""

    entries = m.Association(m.ModelElement, "entry", legacy_by_type=True)
    do_activity = m.Association(
        m.ModelElement, "doActivity", legacy_by_type=True
    )
    exits = m.Association(m.ModelElement, "exit", legacy_by_type=True)

    incoming_transitions = m.Accessor
    outgoing_transitions = m.Accessor

    functions: m.Accessor


class Mode(AbstractStateMode):
    """A mode."""


class DeepHistoryPseudoState(AbstractStateMode):
    """A deep history pseudo state."""


class FinalState(AbstractStateMode):
    """A final state."""


class ForkPseudoState(AbstractStateMode):
    """A fork pseudo state."""


class InitialPseudoState(AbstractStateMode):
    """An initial pseudo state."""


class JoinPseudoState(AbstractStateMode):
    """A join pseudo state."""


class ShallowHistoryPseudoState(AbstractStateMode):
    """A shallow history pseudo state."""


class TerminatePseudoState(AbstractStateMode):
    """A terminate pseudo state."""


class StateMachine(m.ModelElement):
    """A state machine."""

    _xmltag = "ownedStateMachines"

    regions = m.DirectProxyAccessor(Region, aslist=m.ElementList)


class StateTransition(m.ModelElement):
    r"""A transition between :class:`State`\ s or :class:`Mode`\ s."""

    _xmltag = "ownedTransitions"

    source = m.Single(m.Association(m.ModelElement, "source"))
    target = m.Single(m.Association(m.ModelElement, "target"))
    destination = m.DeprecatedAccessor[t.Any]("target")
    triggers = m.Association(m.ModelElement, "triggers", legacy_by_type=True)
    effects = m.Association(m.ModelElement, "effect", legacy_by_type=True)
    guard = m.Single(m.Association(capellacore.Constraint, "guard"))


class GenericTrace(modellingcore.TraceableElement):
    """A trace between two elements."""

    @property
    def name(self) -> str:  # type: ignore[override]
        """Return the name."""
        direction = ""
        if self.target is not None:
            direction = f" to {self.target.name} ({self.target.uuid})"

        return f"[{type(self).__name__}]{direction}"


AbstractStateMode.realized_states = m.Allocation(
    None,  # FIXME fill in tag
    AbstractStateRealization,
    attr="targetElement",
)
for cls in [
    State,
    Mode,
    DeepHistoryPseudoState,
    FinalState,
    ForkPseudoState,
    InitialPseudoState,
    JoinPseudoState,
    ShallowHistoryPseudoState,
    TerminatePseudoState,
]:
    cls.realizing_states = m.Backref(cls, "realized_states")

for cls in [
    State,
    Mode,
    DeepHistoryPseudoState,
    FinalState,
    ForkPseudoState,
    JoinPseudoState,
    ShallowHistoryPseudoState,
    TerminatePseudoState,
]:
    cls.incoming_transitions = m.Backref(StateTransition, "destination")

for cls in [
    State,
    Mode,
    DeepHistoryPseudoState,
    ForkPseudoState,
    InitialPseudoState,
    JoinPseudoState,
    ShallowHistoryPseudoState,
]:
    cls.outgoing_transitions = m.Backref(StateTransition, "source")

Region.states = m.Containment(AbstractStateMode._xmltag)
Region.modes = m.DirectProxyAccessor(Mode, aslist=m.ElementList)
Region.transitions = m.DirectProxyAccessor(
    StateTransition, aslist=m.ElementList
)
m.ModelElement.traces = m.DirectProxyAccessor(
    GenericTrace, aslist=m.ElementList
)
