# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import capellambse.model as m

from . import capellacore


class FunctionalChainAbstractCapabilityInvolvement(m.ModelElement): ...


class AbstractCapabilityRealization(m.ModelElement): ...


@m.xtype_handler(None)
class Execution(m.ModelElement):
    """An execution."""

    start = m.Association(m.ModelElement, "start")
    finish = m.Association(m.ModelElement, "finish")


@m.xtype_handler(None)
class StateFragment(Execution):
    """A state fragment."""

    function = m.Association(m.ModelElement, "relatedAbstractFunction")


@m.xtype_handler(None)
class CombinedFragment(Execution):
    """A combined fragment."""

    operator = m.StringPOD("operator")
    operands = m.Association(
        m.ModelElement, "referencedOperands", aslist=m.ElementList
    )


@m.xtype_handler(None)
class InstanceRole(m.ModelElement):
    """An instance role."""

    instance = m.Association[m.ModelElement](None, "representedInstance")


@m.xtype_handler(None)
class SequenceMessage(m.ModelElement):
    """A sequence message."""

    source = m.Association(m.ModelElement, "sendingEnd")
    target = m.Association(m.ModelElement, "receivingEnd")


class Event(m.ModelElement):
    """Abstract super class of all events in a Scenario."""


class EventOperation(Event):
    """Abstract super class for events about operations."""

    operation = m.Association(m.ModelElement, "operation")


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
class Scenario(m.ModelElement):
    """A scenario that holds instance roles."""

    instance_roles = m.DirectProxyAccessor[m.ModelElement](
        InstanceRole, aslist=m.ElementList
    )
    messages = m.DirectProxyAccessor(SequenceMessage, aslist=m.ElementList)
    events = m.Containment("ownedEvents", aslist=m.MixedElementList)
    fragments = m.Containment(
        "ownedInteractionFragments", aslist=m.MixedElementList
    )
    time_lapses = m.Containment("ownedTimeLapses", aslist=m.MixedElementList)
    postcondition = m.Association(capellacore.Constraint, "postCondition")
    precondition = m.Association(capellacore.Constraint, "preCondition")

    @property
    def related_functions(self) -> m.ElementList[fa.AbstractFunction]:
        return self.fragments.map("function")


class InteractionFragment(m.ModelElement):
    """Abstract super class of all interaction fragments in a Scenario."""

    covered = m.Association[m.ModelElement](
        None, "coveredInstanceRoles", aslist=m.MixedElementList
    )


@m.xtype_handler(None)
class ExecutionEnd(InteractionFragment):
    """An end for an execution."""

    event = m.Association[Event](None, "event")


@m.xtype_handler(None)
class FragmentEnd(InteractionFragment):
    """An end for a fragment."""


@m.xtype_handler(None)
class InteractionOperand(InteractionFragment):
    """An interaction-operand."""

    guard = m.Association(capellacore.Constraint, "guard")


@m.xtype_handler(None)
class InteractionState(InteractionFragment):
    """An interaction-state."""

    state = m.Association(m.ModelElement, "relatedAbstractState")
    function = m.Association(m.ModelElement, "relatedAbstractFunction")


@m.xtype_handler(None)
class MessageEnd(InteractionFragment):
    """A message-end."""

    event = m.Association[Event](None, "event")


class Exchange(m.ModelElement):
    """An abstract Exchange."""

    source = m.ParentAccessor(m.ModelElement)


@m.xtype_handler(None)
class AbstractCapabilityExtend(Exchange):
    """An AbstractCapabilityExtend."""

    _xmltag = "extends"

    source = m.ParentAccessor(m.ModelElement)
    target = m.Association(m.ModelElement, "extended")


@m.xtype_handler(None)
class AbstractCapabilityInclude(Exchange):
    """An AbstractCapabilityInclude."""

    _xmltag = "includes"

    source = m.ParentAccessor(m.ModelElement)
    target = m.Association(m.ModelElement, "included")


@m.xtype_handler(None)
class AbstractCapabilityGeneralization(Exchange):
    """An AbstractCapabilityGeneralization."""

    _xmltag = "superGeneralizations"

    source = m.ParentAccessor(m.ModelElement)
    target = m.Association(m.ModelElement, "super")


class AbstractInvolvement(m.ModelElement):
    """An abstract Involvement."""

    source = m.ParentAccessor(m.ModelElement)
    target = m.Association(m.ModelElement, "involved")

    involved = m.Association(m.ModelElement, "involved")

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


from . import fa
