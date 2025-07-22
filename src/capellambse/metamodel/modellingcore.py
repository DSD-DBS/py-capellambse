# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import enum

import capellambse.model as m
from capellambse.model._obj import ModelElement as ModelElement

from . import namespaces as ns

NS = ns.MODELLINGCORE


@m.stringy_enum
@enum.unique
class ParameterEffectKind(enum.Enum):
    """A behavior's effect on values passed in or out of its parameters."""

    READ = "read"
    """The parameter value is only being read upon behavior execution."""
    UPDATE = "update"
    """The parameter value is being updated upon behavior execution."""
    CREATE = "create"
    """The parameter value is being created upon behavior execution."""
    DELETE = "delete"
    """The parameter value is being deleted upon behavior execution."""


@m.stringy_enum
@enum.unique
class RateKind(enum.Enum):
    """The possible caracterizations for the rate of a streaming parameter."""

    UNSPECIFIED = "Unspecified"
    """The rate kind is not specified."""
    CONTINUOUS = "Continuous"
    """The rate characterizes a continuous flow."""
    DISCRETE = "Discrete"
    """The rate characterizes a discrete flow."""


ModelElement.extensions = m.Containment["ModelElement"](
    "ownedExtensions", (NS, "ModelElement")
)
ModelElement.constraints = m.Containment(
    "ownedConstraints", (ns.CAPELLACORE, "Constraint")
)
ModelElement.migrated_elements = m.Containment["ModelElement"](
    "ownedMigratedElements", (NS, "ModelElement")
)


class AbstractRelationship(ModelElement, abstract=True):
    realized_flow = m.Association["AbstractInformationFlow"](
        (NS, "AbstractInformationFlow"), "realizedFlow"
    )


class AbstractNamedElement(ModelElement, abstract=True):
    """An element that may have a name.

    The name is used for identification of the named element within the
    namespace in which it is defined. A named element also has a
    qualified name that allows it to be unambiguously identified within
    a hierarchy of nested namespaces.
    """

    name = m.StringPOD("name")


class InformationsExchanger(ModelElement, abstract=True):
    """An element that may exchange information with other elements."""


class TraceableElement(ModelElement, abstract=True):
    """An element that may be traced to other elements."""


class FinalizableElement(ModelElement, abstract=True):
    is_final = m.BoolPOD("final")


class PublishableElement(ModelElement, abstract=True):
    is_visible_in_doc = m.BoolPOD("visibleInDoc")
    is_visible_in_lm = m.BoolPOD("visibleInLM")


class AbstractType(AbstractNamedElement, abstract=True):
    """Base abstract class supporting the definition of data types."""


class AbstractTypedElement(AbstractNamedElement, abstract=True):
    """A (named) model element to which a specific type is associated."""

    type = m.Single["AbstractType"](
        m.Association((NS, "AbstractType"), "abstractType")
    )


class AbstractTrace(TraceableElement, abstract=True):
    target = m.Single["TraceableElement"](
        m.Association((NS, "TraceableElement"), "targetElement")
    )
    source = m.Single["TraceableElement"](
        m.Association((NS, "TraceableElement"), "sourceElement")
    )


class AbstractConstraint(ModelElement, abstract=True):
    """A constraint that applies to a given set of model elements."""

    constrained_elements = m.Association["ModelElement"](
        (NS, "ModelElement"), "constrainedElements", legacy_by_type=True
    )
    specification = m.Single["ValueSpecification"](
        m.Containment("ownedSpecification", (NS, "ValueSpecification"))
    )
    """A condition that must evaluate to true to satisfy the constraint."""


class ValueSpecification(AbstractTypedElement, abstract=True):
    """The specification of a set of instances.

    The set includes both objects and data values, and may be empty.
    """


class AbstractParameter(AbstractTypedElement, abstract=True):
    """Specification of an argument to a behavioral feature.

    Parameters are used to pass information into or out of an invocation
    of a behavioral feature.
    """

    is_exception = m.BoolPOD("isException")
    is_stream = m.BoolPOD("isStream")
    is_optional = m.BoolPOD("isOptional")
    kind_of_rate = m.EnumPOD("kindOfRate", RateKind)
    effect = m.EnumPOD("effect", ParameterEffectKind)
    rate = m.Single["ValueSpecification"](
        m.Containment("rate", (NS, "ValueSpecification"))
    )
    probability = m.Single["ValueSpecification"](
        m.Containment("probability", (NS, "ValueSpecification"))
    )
    parameter_set = m.Single["AbstractParameterSet"](
        m.Association((NS, "AbstractParameterSet"), "parameterSet")
    )


class AbstractParameterSet(AbstractNamedElement, abstract=True):
    """An alternative set of inputs or outputs that a behavior may use."""

    conditions = m.Containment["AbstractConstraint"](
        "ownedConditions", (NS, "AbstractConstraint")
    )
    probability = m.Single["ValueSpecification"](
        m.Containment("probability", (NS, "ValueSpecification"))
    )
    parameters = m.Single["AbstractParameter"](
        m.Association((NS, "AbstractParameter"), "parameters")
    )


class AbstractInformationFlow(
    AbstractNamedElement, AbstractRelationship, abstract=True
):
    realizations = m.Association["AbstractRelationship"](
        (NS, "AbstractRelationship"), "realizations"
    )
    convoyed_informations = m.Association["AbstractExchangeItem"](
        (NS, "AbstractExchangeItem"), "convoyedInformations"
    )
    source = m.Single["InformationsExchanger"](
        m.Association((NS, "InformationsExchanger"), "source")
    )
    target = m.Single["InformationsExchanger"](
        m.Association((NS, "InformationsExchanger"), "target")
    )


class AbstractExchangeItem(AbstractType, abstract=True):
    """Set of exchanged element exchanged between ports."""


class IState(AbstractNamedElement, abstract=True):
    """A vertex is an abstraction of a node in a state machine graph.

    In general, it can be the source or destination of any number of
    transitions.
    """

    referenced_states = m.Association["IState"](
        (NS, "IState"), "referencedStates"
    )
    exploited_states = m.Association["IState"](
        (NS, "IState"), "exploitedStates"
    )
