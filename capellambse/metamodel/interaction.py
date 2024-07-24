# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
import capellambse.model as m

from . import capellacore


class FunctionalChainAbstractCapabilityInvolvement(m.GenericElement): ...


class AbstractCapabilityRealization(m.GenericElement): ...


@m.xtype_handler(None)
class Execution(m.GenericElement):
    """An execution."""

    start = m.AttrProxyAccessor(m.GenericElement, "start")
    finish = m.AttrProxyAccessor(m.GenericElement, "finish")


@m.xtype_handler(None)
class StateFragment(Execution):
    """A state fragment."""

    function = m.AttrProxyAccessor(m.GenericElement, "relatedAbstractFunction")


@m.xtype_handler(None)
class CombinedFragment(Execution):
    """A combined fragment."""

    operator = m.StringPOD("operator")
    operands = m.AttrProxyAccessor(
        m.GenericElement, "referencedOperands", aslist=m.ElementList
    )


@m.xtype_handler(None)
class InstanceRole(m.GenericElement):
    """An instance role."""

    instance = m.AttrProxyAccessor[m.GenericElement](
        None, "representedInstance"
    )


@m.xtype_handler(None)
class SequenceMessage(m.GenericElement):
    """A sequence message."""

    source = m.AttrProxyAccessor(m.GenericElement, "sendingEnd")
    target = m.AttrProxyAccessor(m.GenericElement, "receivingEnd")


class Event(m.GenericElement):
    """Abstract super class of all events in a Scenario."""


class EventOperation(Event):
    """Abstract super class for events about operations."""

    operation = m.AttrProxyAccessor(m.GenericElement, "operation")


@m.xtype_handler(None)
class ExecutionEvent(Event):
    """An execution event."""


@m.xtype_handler(None)
class EventSentOperation(EventOperation):
    """An event-sent operation."""


@m.xtype_handler(None)
class EventReceiptOperation(EventOperation):
    """An event-receipt operation."""


@m.xtype_handler(None)
class Scenario(m.GenericElement):
    """A scenario that holds instance roles."""

    instance_roles = m.DirectProxyAccessor[m.GenericElement](
        InstanceRole, aslist=m.ElementList
    )
    messages = m.DirectProxyAccessor(SequenceMessage, aslist=m.ElementList)
    events = m.RoleTagAccessor("ownedEvents", aslist=m.MixedElementList)
    fragments = m.RoleTagAccessor(
        "ownedInteractionFragments", aslist=m.MixedElementList
    )
    time_lapses = m.RoleTagAccessor(
        "ownedTimeLapses", aslist=m.MixedElementList
    )
    postcondition = m.AttrProxyAccessor(
        capellacore.Constraint, "postCondition"
    )
    precondition = m.AttrProxyAccessor(capellacore.Constraint, "preCondition")


class InteractionFragment(m.GenericElement):
    """Abstract super class of all interaction fragments in a Scenario."""

    covered = m.AttrProxyAccessor[m.GenericElement](
        None, "coveredInstanceRoles", aslist=m.MixedElementList
    )


@m.xtype_handler(None)
class ExecutionEnd(InteractionFragment):
    """An end for an execution."""

    event = m.AttrProxyAccessor[Event](None, "event")


@m.xtype_handler(None)
class FragmentEnd(InteractionFragment):
    """An end for a fragment."""


@m.xtype_handler(None)
class InteractionOperand(InteractionFragment):
    """An interaction-operand."""

    guard = m.AttrProxyAccessor(capellacore.Constraint, "guard")


@m.xtype_handler(None)
class InteractionState(InteractionFragment):
    """An interaction-state."""

    state = m.AttrProxyAccessor(m.GenericElement, "relatedAbstractState")
    function = m.AttrProxyAccessor(m.GenericElement, "relatedAbstractFunction")


@m.xtype_handler(None)
class MessageEnd(InteractionFragment):
    """A message-end."""

    event = m.AttrProxyAccessor[Event](None, "event")


class Exchange(m.GenericElement):
    """An abstract Exchange."""

    source = m.ParentAccessor(m.GenericElement)


@m.xtype_handler(None)
class AbstractCapabilityExtend(Exchange):
    """An AbstractCapabilityExtend."""

    _xmltag = "extends"

    source = m.ParentAccessor(m.GenericElement)
    target = m.AttrProxyAccessor(m.GenericElement, "extended")


@m.xtype_handler(None)
class AbstractCapabilityInclude(Exchange):
    """An AbstractCapabilityInclude."""

    _xmltag = "includes"

    source = m.ParentAccessor(m.GenericElement)
    target = m.AttrProxyAccessor(m.GenericElement, "included")


@m.xtype_handler(None)
class AbstractCapabilityGeneralization(Exchange):
    """An AbstractCapabilityGeneralization."""

    _xmltag = "superGeneralizations"

    source = m.ParentAccessor(m.GenericElement)
    target = m.AttrProxyAccessor(m.GenericElement, "super")


class AbstractInvolvement(m.GenericElement):
    """An abstract Involvement."""

    source = m.ParentAccessor(m.GenericElement)
    target = m.AttrProxyAccessor(m.GenericElement, "involved")

    involved = m.AttrProxyAccessor(m.GenericElement, "involved")

    @property
    def name(self) -> str:  # type: ignore[override]
        """Return the name."""
        direction = ""
        if self.involved is not None:
            direction = f" to {self.involved.name} ({self.involved.uuid})"

        return f"[{self.__class__.__name__}]{direction}"


@m.xtype_handler(None)
class AbstractFunctionAbstractCapabilityInvolvement(AbstractInvolvement):
    """An abstract CapabilityInvolvement linking to SystemFunctions."""
