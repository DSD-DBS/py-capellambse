# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import typing as t

import capellambse.model as m

from . import capellacore
from . import namespaces as ns

NS = ns.INTERACTION


class FunctionalChainAbstractCapabilityInvolvement(m.ModelElement): ...


class AbstractCapabilityRealization(m.ModelElement): ...


class Execution(m.ModelElement):
    """An execution."""

    start = m.Single(m.Association(m.ModelElement, "start"))
    finish = m.Single(m.Association(m.ModelElement, "finish"))


class StateFragment(Execution):
    """A state fragment."""

    function = m.Single(
        m.Association(m.ModelElement, "relatedAbstractFunction")
    )


class CombinedFragment(Execution):
    """A combined fragment."""

    operator = m.StringPOD("operator")
    operands = m.Association(m.ModelElement, "referencedOperands")


class InstanceRole(m.ModelElement):
    """An instance role."""

    instance = m.Single(
        m.Association[m.ModelElement](None, "representedInstance")
    )


class SequenceMessage(m.ModelElement):
    """A sequence message."""

    source = m.Single(m.Association(m.ModelElement, "sendingEnd"))
    target = m.Single(m.Association(m.ModelElement, "receivingEnd"))


class Event(m.ModelElement):
    """Abstract super class of all events in a Scenario."""


class EventOperation(Event):
    """Abstract super class for events about operations."""

    operation = m.Single(m.Association(m.ModelElement, "operation"))


class ExecutionEvent(Event):
    """An execution event."""


class EventSentOperation(EventOperation):
    """An event-sent operation."""


class EventReceiptOperation(EventOperation):
    """An event-receipt operation."""


class Scenario(m.ModelElement):
    """A scenario that holds instance roles."""

    instance_roles = m.DirectProxyAccessor[m.ModelElement](
        InstanceRole, aslist=m.ElementList
    )
    messages = m.DirectProxyAccessor(SequenceMessage, aslist=m.ElementList)
    events = m.Containment[t.Any]("ownedEvents", legacy_by_type=True)
    fragments = m.Containment[t.Any](
        "ownedInteractionFragments", legacy_by_type=True
    )
    time_lapses = m.Containment[t.Any]("ownedTimeLapses", legacy_by_type=True)
    postcondition = m.Single(
        m.Association(capellacore.Constraint, "postCondition")
    )
    precondition = m.Single(
        m.Association(capellacore.Constraint, "preCondition")
    )
    realized_scenarios = m.Allocation["Scenario"](
        "ownedScenarioRealization",
        "org.polarsys.capella.core.data.interaction:ScenarioRealization",
        attr="targetElement",
        backattr="sourceElement",
    )
    realizing_scenarios: m.Backref[Scenario]

    @property
    def related_functions(self) -> m.ElementList[fa.AbstractFunction]:
        return self.fragments.map("function")


class InteractionFragment(m.ModelElement):
    """Abstract super class of all interaction fragments in a Scenario."""

    covered = m.Association[m.ModelElement](
        None, "coveredInstanceRoles", legacy_by_type=True
    )


class ExecutionEnd(InteractionFragment):
    """An end for an execution."""

    event = m.Single(m.Association[Event](None, "event"))


class FragmentEnd(InteractionFragment):
    """An end for a fragment."""


class InteractionOperand(InteractionFragment):
    """An interaction-operand."""

    guard = m.Single(m.Association(capellacore.Constraint, "guard"))


class InteractionState(InteractionFragment):
    """An interaction-state."""

    state = m.Single(m.Association(m.ModelElement, "relatedAbstractState"))
    function = m.Single(
        m.Association(m.ModelElement, "relatedAbstractFunction")
    )


class MessageEnd(InteractionFragment):
    """A message-end."""

    event = m.Single(m.Association[Event](None, "event"))


class Exchange(m.ModelElement):
    """An abstract Exchange."""

    source = m.ParentAccessor()


class AbstractCapabilityExtend(Exchange):
    """An AbstractCapabilityExtend."""

    _xmltag = "extends"

    source = m.ParentAccessor()
    target = m.Single(m.Association(m.ModelElement, "extended"))


class AbstractCapabilityInclude(Exchange):
    """An AbstractCapabilityInclude."""

    _xmltag = "includes"

    source = m.ParentAccessor()
    target = m.Single(m.Association(m.ModelElement, "included"))


class AbstractCapabilityGeneralization(Exchange):
    """An AbstractCapabilityGeneralization."""

    _xmltag = "superGeneralizations"

    source = m.ParentAccessor()
    target = m.Single(m.Association(m.ModelElement, "super"))


class AbstractInvolvement(m.ModelElement):
    """An abstract Involvement."""

    source = m.ParentAccessor()
    target = m.Alias[t.Any]("involved")
    involved = m.Single(m.Association(m.ModelElement, "involved"))

    @property
    def name(self) -> str:  # type: ignore[override]
        """Return the name."""
        direction = ""
        if self.involved is not None:
            direction = f" to {self.involved.name} ({self.involved.uuid})"

        return f"[{self.__class__.__name__}]{direction}"


class AbstractFunctionAbstractCapabilityInvolvement(AbstractInvolvement):
    """An abstract CapabilityInvolvement linking to SystemFunctions."""


Scenario.realizing_scenarios = m.Backref(Scenario, "realized_scenarios")


from . import fa
