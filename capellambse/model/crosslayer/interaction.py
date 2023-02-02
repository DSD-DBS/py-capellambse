# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0


from .. import common as c
from . import capellacore

XT_CAP2PROC = (
    "org.polarsys.capella.core.data.interaction"
    ":FunctionalChainAbstractCapabilityInvolvement"
)
XT_CAP_REAL = (
    "org.polarsys.capella.core.data.interaction:AbstractCapabilityRealization"
)


@c.xtype_handler(None)
class Execution(c.GenericElement):
    """An execution."""

    start = c.AttrProxyAccessor(c.GenericElement, "start")
    finish = c.AttrProxyAccessor(c.GenericElement, "finish")


@c.xtype_handler(None)
class StateFragment(Execution):
    """A state fragment."""

    function = c.AttrProxyAccessor(c.GenericElement, "relatedAbstractFunction")


@c.xtype_handler(None)
class CombinedFragment(Execution):
    """A combined fragment."""

    operator = c.AttributeProperty("operator", optional=True)
    operands = c.AttrProxyAccessor(
        c.GenericElement, "referencedOperands", aslist=c.ElementList
    )


@c.xtype_handler(None)
class InstanceRole(c.GenericElement):
    """An instance role."""

    instance = c.AttrProxyAccessor[c.GenericElement](
        None, "representedInstance"
    )


@c.xtype_handler(None)
class SequenceMessage(c.GenericElement):
    """A sequence message."""

    source = c.AttrProxyAccessor(c.GenericElement, "sendingEnd")
    target = c.AttrProxyAccessor(c.GenericElement, "receivingEnd")


class Event(c.GenericElement):
    """Abstract super class of all events in a Scenario."""


class EventOperation(Event):
    """Abstract super class for events about operations."""

    operation = c.AttrProxyAccessor(c.GenericElement, "operation")


@c.xtype_handler(None)
class ExecutionEvent(Event):
    """An execution event."""


@c.xtype_handler(None)
class EventSentOperation(EventOperation):
    """An event-sent operation."""


@c.xtype_handler(None)
class EventReceiptOperation(EventOperation):
    """An event-receipt operation."""


@c.xtype_handler(None)
class Scenario(c.GenericElement):
    """A scenario that holds instance roles."""

    instance_roles = c.DirectProxyAccessor[c.GenericElement](
        InstanceRole, aslist=c.ElementList
    )
    messages = c.DirectProxyAccessor(SequenceMessage, aslist=c.ElementList)
    events = c.RoleTagAccessor("ownedEvents", aslist=c.MixedElementList)
    fragments = c.RoleTagAccessor(
        "ownedInteractionFragments", aslist=c.MixedElementList
    )
    time_lapses = c.RoleTagAccessor(
        "ownedTimeLapses", aslist=c.MixedElementList
    )


class InteractionFragment(c.GenericElement):
    """Abstract super class of all interaction fragments in a Scenario."""

    covered = c.AttrProxyAccessor[c.GenericElement](
        None, "coveredInstanceRoles", aslist=c.MixedElementList
    )


@c.xtype_handler(None)
class ExecutionEnd(InteractionFragment):
    event = c.AttrProxyAccessor[Event](None, "event")


@c.xtype_handler(None)
class FragmentEnd(InteractionFragment):
    """An end for a fragment."""


@c.xtype_handler(None)
class InteractionOperand(InteractionFragment):
    """An interaction-operand."""

    guard = c.AttrProxyAccessor(capellacore.Constraint, "guard")


@c.xtype_handler(None)
class InteractionState(InteractionFragment):
    """An interaction-state."""

    state = c.AttrProxyAccessor(c.GenericElement, "relatedAbstractState")
    function = c.AttrProxyAccessor(c.GenericElement, "relatedAbstractFunction")


@c.xtype_handler(None)
class MessageEnd(InteractionFragment):
    """A message-end."""

    event = c.AttrProxyAccessor[Event](None, "event")


class Exchange(c.GenericElement):
    """An abstract Exchange."""

    source = c.ParentAccessor(c.GenericElement)


@c.xtype_handler(None)
class AbstractCapabilityExtend(Exchange):
    """An AbstractCapabilityExtend."""

    _xmltag = "extends"

    source = c.ParentAccessor(c.GenericElement)
    target = c.AttrProxyAccessor(c.GenericElement, "extended")


@c.xtype_handler(None)
class AbstractCapabilityInclude(Exchange):
    """An AbstractCapabilityInclude."""

    _xmltag = "includes"

    source = c.ParentAccessor(c.GenericElement)
    target = c.AttrProxyAccessor(c.GenericElement, "included")


@c.xtype_handler(None)
class AbstractCapabilityGeneralization(Exchange):
    """An AbstractCapabilityGeneralization."""

    _xmltag = "superGeneralizations"

    source = c.ParentAccessor(c.GenericElement)
    target = c.AttrProxyAccessor(c.GenericElement, "super")


class AbstractInvolvement(c.GenericElement):
    """An abstract Involvement."""

    source = c.ParentAccessor(c.GenericElement)
    target = c.AttrProxyAccessor(c.GenericElement, "involved")

    involved = c.AttrProxyAccessor(c.GenericElement, "involved")

    @property
    def name(self) -> str:  # type: ignore[override]
        """Return the name."""
        direction = ""
        if self.involved is not None:
            direction = f" to {self.involved.name} ({self.involved.uuid})"

        return f"[{self.__class__.__name__}]{direction}"


@c.xtype_handler(None)
class AbstractFunctionAbstractCapabilityInvolvement(AbstractInvolvement):
    """An abstract CapabilityInvolvement linking to SystemFunctions."""
