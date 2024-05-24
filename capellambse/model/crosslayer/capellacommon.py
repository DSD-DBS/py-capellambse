# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Classes handling Mode/State-Machines and related content."""
from .. import common as c
from . import capellacore, modellingcore

XT_TRAFO = "org.polarsys.capella.core.data.capellacommon:TransfoLink"
XT_ABSTRACT_STATE_REAL = (
    "org.polarsys.capella.core.data.capellacommon:AbstractStateRealization"
)
XT_CAPABILITY_REALIZATION_INVOLVEMENT = (
    "org.polarsys.capella.core.data.capellacommon"
    ":CapabilityRealizationInvolvement"
)


@c.xtype_handler(None)
class Region(c.GenericElement):
    """A region inside a state machine or state/mode."""

    _xmltag = "ownedRegions"

    states: c.Accessor
    modes: c.Accessor
    transitions: c.Accessor

class AbstractPrimitiveState(c.GenericElement):
    _xmltag = "ownedStates"

    incoming_transitions: c.Accessor
    outgoing_transitions: c.Accessor
    related_states: c.Accessor


class AbstractStateMode(AbstractPrimitiveState):
    """Common code for states and modes."""

    _xmltag = "ownedStates"

    regions = c.DirectProxyAccessor(Region, aslist=c.ElementList)

    entry = c.AttrProxyAccessor(
        c.GenericElement, "entry", aslist=c.MixedElementList
    )
    do_activity = c.AttrProxyAccessor(
        c.GenericElement, "doActivity", aslist=c.MixedElementList
    )
    exit = c.AttrProxyAccessor(
        c.GenericElement, "exit", aslist=c.MixedElementList
    )


@c.xtype_handler(None)
class State(AbstractStateMode):
    """A state."""


@c.xtype_handler(None)
class Mode(AbstractStateMode):
    """A mode."""


@c.xtype_handler(None)
class DeepHistoryPseudoState(AbstractPrimitiveState):
    """A deep history pseudo state."""


@c.xtype_handler(None)
class FinalState(AbstractPrimitiveState):
    """A final state."""


@c.xtype_handler(None)
class ForkPseudoState(AbstractPrimitiveState):
    """A fork pseudo state."""


@c.xtype_handler(None)
class InitialPseudoState(AbstractPrimitiveState):
    """An initial pseudo state."""


@c.xtype_handler(None)
class JoinPseudoState(AbstractPrimitiveState):
    """A join pseudo state."""


@c.xtype_handler(None)
class ShallowHistoryPseudoState(AbstractPrimitiveState):
    """A shallow history pseudo state."""


@c.xtype_handler(None)
class TerminatePseudoState(AbstractPrimitiveState):
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
class GenericTrace(modellingcore.TraceableElement):
    """A trace between two elements."""

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
    AbstractPrimitiveState,
    "incoming_transitions",
    c.ReferenceSearchingAccessor(
        StateTransition, "destination", aslist=c.ElementList
    )
)
c.set_accessor(
    AbstractPrimitiveState,
    "outgoing_transitions",
    c.ReferenceSearchingAccessor(
        StateTransition, "source", aslist=c.ElementList
    )
)
c.set_accessor(
    AbstractPrimitiveState,
    "related_transitions",
    c.ReferenceSearchingAccessor(
        StateTransition, "source", "destination", aslist=c.ElementList
    )
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
