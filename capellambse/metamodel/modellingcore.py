# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from capellambse import modelv2 as m

from . import modeltypes
from . import namespaces as ns

NS = ns.MODELLINGCORE


ModelElement = m.ModelElement
ModelElement.extensions = m.Containment(
    "ownedExtensions", (NS, "ModelElement")
)
ModelElement.constraints = m.Backref(
    (NS, "AbstractConstraint"), lookup="constrained_elements"
)
ModelElement.owned_constraints = m.Containment(
    "ownedConstraints", (NS, "AbstractConstraint")
)
ModelElement.migrated_elements = m.Containment(
    "ownedMigratedElements", (NS, "ModelElement")
)


class AbstractRelationship(ModelElement, abstract=True):
    realized_flow = m.Backref["AbstractInformationFlow"](
        (NS, "AbstractInformationFlow"), lookup="realizations"
    )


class AbstractNamedElement(ModelElement, abstract=True):
    """An element that may have a name.

    The name is used for identification of the named element within the
    namespace in which it is defined. A named element also has a
    qualified name that allows it to be unambiguously identified within
    a hierarchy of nested namespaces.
    """

    name = m.StringPOD(name="name", required=False, writable=True)
    """The name of the NamedElement."""


class InformationsExchanger(ModelElement, abstract=True):
    """An element that may exchange information with other elements."""


class TraceableElement(ModelElement, abstract=True):
    """An element that may be traced to other elements."""


class FinalizableElement(ModelElement, abstract=True):
    final = m.BoolPOD(name="final")


class PublishableElement(ModelElement, abstract=True):
    visible_in_doc = m.BoolPOD(name="visibleInDoc")
    visible_in_lm = m.BoolPOD(name="visibleInLM")


class AbstractType(AbstractNamedElement, abstract=True):
    """Base abstract class supporting the definition of data types."""


class AbstractTypedElement(AbstractNamedElement, abstract=True):
    """A (named) model element to which a specific type is associated."""

    type = m.Single(
        m.Association["AbstractType"]("abstractType", (NS, "AbstractType")),
        enforce=False,
    )


class AbstractTrace(TraceableElement, abstract=True):
    target = m.Single(
        m.Association["TraceableElement"](
            "targetElement", (NS, "TraceableElement")
        ),
        enforce="min",
    )
    source = m.Single(
        m.Association["TraceableElement"](
            "sourceElement", (NS, "TraceableElement")
        ),
        enforce="min",
    )


class AbstractConstraint(ModelElement, abstract=True):
    """A constraint that applies to a given set of model elements."""

    constrained_elements = m.Association["ModelElement"](
        "constrainedElements", ("", "")
    )
    specification = m.Single(
        m.Containment["ValueSpecification"](
            "ownedSpecification", (NS, "ValueSpecification")
        ),
        enforce=False,
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

    is_exception = m.BoolPOD(name="isException")
    is_stream = m.BoolPOD(name="isStream")
    is_optional = m.BoolPOD(name="isOptional")
    kind_of_rate = m.EnumPOD("kindOfRate", modeltypes.RateKind)
    effect = m.EnumPOD("effect", modeltypes.ParameterEffectKind)
    rate = m.Single(
        m.Containment["ValueSpecification"]("rate", (NS, "ValueSpecification"))
    )
    probability = m.Single(
        m.Containment["ValueSpecification"](
            "probability", (NS, "ValueSpecification")
        )
    )


class AbstractParameterSet(AbstractNamedElement, abstract=True):
    """An alternative set of inputs or outputs that a behavior may use."""

    conditions = m.Containment["AbstractConstraint"](
        "ownedConditions", (NS, "AbstractConstraint")
    )
    probability = m.Single(
        m.Containment["ValueSpecification"](
            "probability", (NS, "ValueSpecification")
        )
    )


class AbstractInformationFlow(
    AbstractNamedElement, AbstractRelationship, abstract=True
):
    realizations = m.Association["AbstractRelationship"](
        "realizations", (NS, "AbstractRelationship")
    )
    convoyed_informations = m.Association["AbstractExchangeItem"](
        "convoyedInformations", (NS, "AbstractExchangeItem")
    )
    source = m.Single(
        m.Association["InformationsExchanger"](
            "source", (NS, "InformationsExchanger")
        )
    )
    target = m.Single(
        m.Association["InformationsExchanger"](
            "target", (NS, "InformationsExchanger")
        )
    )


class AbstractExchangeItem(AbstractType, abstract=True):
    """Set of exchanged element exchanged between ports."""


class IState(AbstractNamedElement, abstract=True):
    """A vertex is an abstraction of a node in a state machine graph.

    In general, it can be the source or destination of any number of
    transitions.
    """

    referenced_states = m.Association["IState"](
        "referencedStates", (NS, "IState")
    )
    exploited_states = m.Association["IState"](
        "exploitedStates", (NS, "IState")
    )
