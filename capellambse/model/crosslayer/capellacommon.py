# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Classes handling Mode/State-Machines and related content."""
from .. import common as c
from . import capellacore

XT_TRAFO = "org.polarsys.capella.core.data.capellacommon:TransfoLink"
XT_ABSTRACT_STATE_REAL = (
    "org.polarsys.capella.core.data.capellacommon:AbstractStateRealization"
)


@c.xtype_handler(None)
class Region(c.GenericElement):
    """A region inside a state machine or state/mode."""

    _xmltag = "ownedRegions"

    states: c.Accessor
    modes: c.Accessor
    transitions: c.Accessor


class AbstractStateMode(c.GenericElement):
    """Common code for states and modes."""

    _xmltag = "ownedStates"

    regions = c.DirectProxyAccessor(Region, aslist=c.ElementList)

    functions: c.Accessor


@c.xtype_handler(None)
class State(AbstractStateMode):
    """A state."""

    entries = c.AttrProxyAccessor(
        c.GenericElement, "entry", aslist=c.MixedElementList
    )
    do_activity = c.AttrProxyAccessor(
        c.GenericElement, "doActivity", aslist=c.MixedElementList
    )
    exits = c.AttrProxyAccessor(
        c.GenericElement, "exit", aslist=c.MixedElementList
    )


@c.xtype_handler(None)
class Mode(AbstractStateMode):
    """A mode."""


@c.xtype_handler(None)
class DeepHistoryPseudoState(AbstractStateMode):
    """A deep history pseudo state."""


@c.xtype_handler(None)
class FinalState(AbstractStateMode):
    """A final state."""


@c.xtype_handler(None)
class ForkPseudoState(AbstractStateMode):
    """A fork pseudo state."""


@c.xtype_handler(None)
class InitialPseudoState(AbstractStateMode):
    """An initial pseudo state."""


@c.xtype_handler(None)
class JoinPseudoState(AbstractStateMode):
    """A join pseudo state."""


@c.xtype_handler(None)
class ShallowHistoryPseudoState(AbstractStateMode):
    """A shallow history pseudo state."""


@c.xtype_handler(None)
class TerminatePseudoState(AbstractStateMode):
    """A terminate pseudo state."""


@c.xtype_handler(None)
class StateMachine(c.GenericElement):
    """A state machine."""

    _xmltag = "ownedStateMachines"

    regions = c.DirectProxyAccessor(Region, aslist=c.ElementList)


@c.xtype_handler(None)
class StateTransition(c.GenericElement):
    r"""A transition between :class:`State`\ s or :class:`Mode`\ s."""

    _xmltag = "ownedTransitions"

    source = c.AttrProxyAccessor(c.GenericElement, "source")
    destination = c.AttrProxyAccessor(c.GenericElement, "target")
    triggers = c.AttrProxyAccessor(
        c.GenericElement, "triggers", aslist=c.MixedElementList
    )
    effects = c.AttrProxyAccessor(
        c.GenericElement, "effect", aslist=c.MixedElementList
    )
    guard = c.AttrProxyAccessor(capellacore.Constraint, "guard")


@c.xtype_handler(None)
class GenericTrace(c.GenericElement):
    """A trace between two elements."""

    source = c.AttrProxyAccessor(c.GenericElement, attr="sourceElement")
    target = c.AttrProxyAccessor(c.GenericElement, attr="targetElement")

    @property
    def name(self) -> str:  # type: ignore[override]
        """Return the name."""
        direction = ""
        if self.target is not None:
            direction = f" to {self.target.name} ({self.target.uuid})"

        return f"[{type(self).__name__}]{direction}"


c.set_accessor(
    AbstractStateMode,
    "realized_states",
    # FIXME fill in tag
    c.LinkAccessor(
        None,
        XT_ABSTRACT_STATE_REAL,
        aslist=c.ElementList,
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
    c.set_accessor(
        cls,
        "realizing_states",
        c.ReferenceSearchingAccessor(
            cls, "realized_states", aslist=c.ElementList
        ),
    )

c.set_accessor(
    Region,
    "states",
    c.RoleTagAccessor(AbstractStateMode._xmltag, aslist=c.ElementList),
)
c.set_accessor(
    Region, "modes", c.DirectProxyAccessor(Mode, aslist=c.ElementList)
)
c.set_accessor(
    Region,
    "transitions",
    c.DirectProxyAccessor(StateTransition, aslist=c.ElementList),
)
c.set_accessor(
    c.GenericElement,
    "traces",
    c.DirectProxyAccessor(GenericTrace, aslist=c.ElementList),
)
