# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Classes handling Mode/State-Machines and related content."""

import capellambse.model as m

from . import capellacore, modellingcore


class AbstractStateRealization(m.GenericElement): ...


class TransfoLink(m.GenericElement): ...


class CapabilityRealizationInvolvement(m.GenericElement): ...


@m.xtype_handler(None)
class Region(m.GenericElement):
    """A region inside a state machine or state/mode."""

    _xmltag = "ownedRegions"

    states: m.Accessor
    modes: m.Accessor
    transitions: m.Accessor


class AbstractStateMode(m.GenericElement):
    """Common code for states and modes."""

    _xmltag = "ownedStates"

    regions = m.DirectProxyAccessor(Region, aslist=m.ElementList)


@m.xtype_handler(None)
class State(AbstractStateMode):
    """A state."""

    entries = m.AttrProxyAccessor(
        m.GenericElement, "entry", aslist=m.MixedElementList
    )
    do_activity = m.AttrProxyAccessor(
        m.GenericElement, "doActivity", aslist=m.MixedElementList
    )
    exits = m.AttrProxyAccessor(
        m.GenericElement, "exit", aslist=m.MixedElementList
    )

    functions: m.Accessor


@m.xtype_handler(None)
class Mode(AbstractStateMode):
    """A mode."""


@m.xtype_handler(None)
class DeepHistoryPseudoState(AbstractStateMode):
    """A deep history pseudo state."""


@m.xtype_handler(None)
class FinalState(AbstractStateMode):
    """A final state."""


@m.xtype_handler(None)
class ForkPseudoState(AbstractStateMode):
    """A fork pseudo state."""


@m.xtype_handler(None)
class InitialPseudoState(AbstractStateMode):
    """An initial pseudo state."""


@m.xtype_handler(None)
class JoinPseudoState(AbstractStateMode):
    """A join pseudo state."""


@m.xtype_handler(None)
class ShallowHistoryPseudoState(AbstractStateMode):
    """A shallow history pseudo state."""


@m.xtype_handler(None)
class TerminatePseudoState(AbstractStateMode):
    """A terminate pseudo state."""


@m.xtype_handler(None)
class StateMachine(m.GenericElement):
    """A state machine."""

    _xmltag = "ownedStateMachines"

    regions = m.DirectProxyAccessor(Region, aslist=m.ElementList)


@m.xtype_handler(None)
class StateTransition(m.GenericElement):
    r"""A transition between :class:`State`\ s or :class:`Mode`\ s."""

    _xmltag = "ownedTransitions"

    source = m.AttrProxyAccessor(m.GenericElement, "source")
    destination = m.AttrProxyAccessor(m.GenericElement, "target")
    triggers = m.AttrProxyAccessor(
        m.GenericElement, "triggers", aslist=m.MixedElementList
    )
    effects = m.AttrProxyAccessor(
        m.GenericElement, "effect", aslist=m.MixedElementList
    )
    guard = m.AttrProxyAccessor(capellacore.Constraint, "guard")


@m.xtype_handler(None)
class GenericTrace(modellingcore.TraceableElement):
    """A trace between two elements."""

    @property
    def name(self) -> str:  # type: ignore[override]
        """Return the name."""
        direction = ""
        if self.target is not None:
            direction = f" to {self.target.name} ({self.target.uuid})"

        return f"[{type(self).__name__}]{direction}"


m.set_accessor(
    AbstractStateMode,
    "realized_states",
    m.LinkAccessor(
        None,  # FIXME fill in tag
        AbstractStateRealization,
        aslist=m.ElementList,
        attr="targetElement",
    ),
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
    m.set_accessor(
        cls,
        "realizing_states",
        m.ReferenceSearchingAccessor(
            cls, "realized_states", aslist=m.ElementList
        ),
    )

m.set_accessor(
    Region,
    "states",
    m.RoleTagAccessor(AbstractStateMode._xmltag, aslist=m.ElementList),
)
m.set_accessor(
    Region, "modes", m.DirectProxyAccessor(Mode, aslist=m.ElementList)
)
m.set_accessor(
    Region,
    "transitions",
    m.DirectProxyAccessor(StateTransition, aslist=m.ElementList),
)
m.set_accessor(
    m.GenericElement,
    "traces",
    m.DirectProxyAccessor(GenericTrace, aslist=m.ElementList),
)
