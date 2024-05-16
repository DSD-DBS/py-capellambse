# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from capellambse import modelv2 as m

from . import modellingcore
from . import namespaces as ns

NS = ns.BEHAVIOR


class AbstractBehavior(modellingcore.AbstractNamedElement, abstract=True):
    """Abstract base class for behaviors."""

    is_control_operator = m.BoolPOD("isControlOperator")
    parameter_sets = m.Containment["modellingcore.AbstractParameterSet"](
        "ownedParameterSet", (ns.MODELLINGCORE, "AbstractParameterSet")
    )
    parameters = m.Containment["modellingcore.AbstractParameter"](
        "ownedParameter", (ns.MODELLINGCORE, "AbstractParameter")
    )


class AbstractSignal(modellingcore.AbstractType, abstract=True):
    """Abstract base class for signals."""


class AbstractEvent(modellingcore.AbstractType, abstract=True):
    """Specification of an occurrence that may trigger effects."""


class AbstractTimeEvent(AbstractEvent, abstract=True):
    """A point in time.

    A time event specifies a point in time by an expression. The
    expression might be absolute or might be relative to some other
    point in time.
    """

    is_relative = m.BoolPOD("isRelative")
    when = m.Single(
        m.Association["TimeExpression"]("when", (NS, "TimeExpression"))
    )


class AbstractMessageEvent(AbstractEvent, abstract=True):
    """The receipt by an object of either a call or a signal."""


class AbstractSignalEvent(AbstractMessageEvent, abstract=True):
    """The receipt of an asynchronous signal.

    A signal event may cause a response, such as a state machine
    transition as specified in the classifier behavior of the classifier
    that specified the receiver object, if the signal referenced by the
    send request is mentioned in a reception owned or inherited by the
    classifier that specified the receiver object.
    """

    signal = m.Association["AbstractSignal"]("signal", (NS, "AbstractSignal"))


class TimeExpression(modellingcore.ValueSpecification, abstract=True):
    """A specification of a point in time."""

    observations = m.Association["modellingcore.AbstractNamedElement"](
        "observations", (ns.MODELLINGCORE, "AbstractNamedElement")
    )
    expressions = m.Association["modellingcore.ValueSpecification"](
        "expression", (ns.MODELLINGCORE, "ValueSpecification")
    )
