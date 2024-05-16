# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import typing as t

from capellambse import modelv2 as m

from . import modellingcore, modeltypes
from . import namespaces as ns

if t.TYPE_CHECKING:
    from . import information

NS = ns.CAPELLACORE


class CapellaElement(
    modellingcore.TraceableElement,
    modellingcore.PublishableElement,
    abstract=True,
):
    summary = m.StringPOD(name="summary")
    """Summary of the element."""
    description = m.StringPOD(name="description")
    """Description of the Capella element."""
    review = m.StringPOD(name="review")
    """Review description on the Capella element."""

    property_values = m.Containment["AbstractPropertyValue"](
        "ownedPropertyValues", (NS, "AbstractPropertyValue")
    )
    enumeration_property_types = m.Containment["EnumerationPropertyType"](
        "ownedEnumerationPropertyTypes", (NS, "EnumerationPropertyType")
    )
    applied_property_values = m.Association["AbstractPropertyValue"](
        "appliedPropertyValues", (NS, "AbstractPropertyValue")
    )
    property_value_groups = m.Containment["PropertyValueGroup"](
        "ownedPropertyValueGroups", (NS, "PropertyValueGroup")
    )
    applied_property_value_groups = m.Association["PropertyValueGroup"](
        "appliedPropertyValueGroups", (NS, "PropertyValueGroup")
    )
    status = m.Single(
        m.Association["EnumerationPropertyLiteral"](
            "status", (NS, "EnumerationPropertyLiteral")
        ),
        enforce=False,
    )
    features = m.Association["EnumerationPropertyLiteral"](
        "features", (NS, "EnumerationPropertyLiteral")
    )


class NamedElement(
    modellingcore.AbstractNamedElement, CapellaElement, abstract=True
):
    """A Capella element that has a name."""


class Relationship(
    modellingcore.AbstractRelationship, CapellaElement, abstract=True
):
    """Specifies some kind of relationship between elements."""


class Namespace(NamedElement, abstract=True):
    """Contains a set of named elements that can be identified by name."""

    owned_traces = m.Containment["Trace"]("ownedTraces", (NS, "Trace"))
    naming_rules = m.Containment["NamingRule"](
        "namingRules", (NS, "NamingRule")
    )


class NamedRelationship(Relationship, NamedElement, abstract=True):
    naming_rules = m.Containment["NamingRule"](
        "namingRules", (NS, "NamingRule")
    )


class Structure(Namespace, abstract=True):
    property_value_pkgs = m.Containment["PropertyValuePkg"](
        "ownedPropertyValuePkgs", (NS, "PropertyValuePkg")
    )


class Type(modellingcore.AbstractType, Namespace, abstract=True):
    """Represents a set of values.

    A typed element that has this type is constrained to represent
    values within this set.
    """


class ModellingBlock(Type, abstract=True):
    """A modular unit that describes the structure of a system or element.

    A class (or block) that cannot be directly instantiated. Contrast:
    concrete class.
    """


class ModellingArchitecture(Structure, abstract=True):
    """Supports the definition of the model structure at a design level."""


class ModellingArchitecturePkg(Structure, abstract=True):
    """A container for modelling architectures."""


class TypedElement(
    modellingcore.AbstractTypedElement, NamedElement, abstract=True
):
    """An element that has a type."""

    type = m.Single(
        m.Association["Type"](None, (NS, "Type")),
        enforce="max",
    )


class Trace(Relationship, modellingcore.AbstractTrace, abstract=True): ...


class AbstractAnnotation(CapellaElement, abstract=True):
    content = m.StringPOD(name="content")


class NamingRule(AbstractAnnotation):
    target_type = m.StringPOD("targetType")
    """Type to whose instances the naming rule has to be applied."""


class Constraint(NamedElement, modellingcore.AbstractConstraint):
    """A condition or restriction.

    The constraint is expressed in natural language text or in a machine
    readable language for the purpose of declaring some of the semantics
    of an element.
    """


class KeyValue(CapellaElement):
    """A generic key/value pair used to index data."""

    key = m.StringPOD("key")
    value = m.StringPOD("value")


class ReuseLink(Relationship):
    reused = m.Association["ReusableStructure"](
        "reused", (NS, "ReusableStructure")
    )
    reuser = m.Association["ReuserStructure"](
        "reuser", (NS, "ReuserStructure")
    )


class ReusableStructure(Structure, abstract=True):
    """A structure intended to be reused across various architectures."""

    reuse_links = m.Association["ReuseLink"]("reuseLinks", (NS, "ReuseLink"))


class ReuserStructure(Structure, abstract=True):
    reused = m.Allocation["ReusableStructure"](
        (NS, "ReuseLink"),
        ("ownedReuseLinks", "reused", "reuser"),
        (NS, "ReusableStructure"),
    )


class AbstractModellingStructure(ReuserStructure, abstract=True):
    architectures = m.Containment["ModellingArchitecture"](
        "ownedArchitectures", (NS, "ModellingArchitecture")
    )
    architecture_pkgs = m.Containment["ModellingArchitecturePkg"](
        "ownedArchitecturePkgs", (NS, "ModellingArchitecturePkg")
    )


class GeneralizableElement(Type, abstract=True):
    """A type than can be generalized."""

    is_abstract = m.BoolPOD("abstract")

    sub = m.Backref["GeneralizableElement"](
        (NS, "GeneralizableElement"), lookup="super"
    )
    super = m.Single(
        m.Allocation["GeneralizableElement"](
            (NS, "Generalization"),
            ("ownedGeneralizations", "super", "sub"),
            (NS, "GeneralizableElement"),
        ),
        enforce="max",
    )


class Classifier(GeneralizableElement, abstract=True):
    owned_features = m.Containment["Feature"]("ownedFeatures", (NS, "Feature"))


class GeneralClass(
    Classifier, modellingcore.FinalizableElement, abstract=True
):
    visibility = m.EnumPOD("visibility", modeltypes.VisibilityKind)
    nested_classes = m.Containment["GeneralClass"](
        "nestedGeneralClasses", (NS, "GeneralClass")
    )


class Generalization(Relationship):
    """A Generalization."""

    super = m.Single(
        m.Association["GeneralizableElement"](
            "super", (NS, "GeneralizableElement")
        )
    )
    sub = m.Single(
        m.Association["GeneralizableElement"](
            "sub", (NS, "GeneralizableElement")
        )
    )


class Feature(NamedElement, abstract=True):
    is_abstract = m.BoolPOD("isAbstract")
    is_static = m.BoolPOD("isStatic")
    visibility = m.EnumPOD("visibility", modeltypes.VisibilityKind)


class AbstractExchangeItemPkg(Structure, abstract=True):
    exchange_items = m.Containment["information.ExchangeItem"](
        "ownedExchangeItems", (ns.INFORMATION, "ExchangeItem")
    )


class Allocation(Relationship, modellingcore.AbstractTrace, abstract=True):
    pass


class Involvement(Relationship, abstract=True):
    involved = m.Single(
        m.Association["InvolvedElement"]("involved", (NS, "InvolvedElement"))
    )


class InvolverElement(CapellaElement, abstract=True):
    pass


class InvolvedElement(CapellaElement, abstract=True):
    pass


class AbstractPropertyValue(NamedElement, abstract=True):
    involved_elements = m.Association["CapellaElement"](
        "involvedElements", (NS, "CapellaElement")
    )


class StringPropertyValue(AbstractPropertyValue):
    """A string property value."""

    value = m.StringPOD("value")


class IntegerPropertyValue(AbstractPropertyValue):
    """An integer property value."""

    value = m.IntPOD("value")


class BooleanPropertyValue(AbstractPropertyValue):
    """A boolean property value."""

    value = m.BoolPOD("value")


class FloatPropertyValue(AbstractPropertyValue):
    """A floating point property value."""

    value = m.FloatPOD("value")


class EnumerationPropertyValue(AbstractPropertyValue):
    """An enumeration property value."""

    type = m.Single(
        m.Association["EnumerationPropertyType"](
            "type", (NS, "EnumerationPropertyType")
        )
    )
    value = m.Single(
        m.Association["EnumerationPropertyLiteral"](
            "value", (NS, "EnumerationPropertyLiteral")
        )
    )


class EnumerationPropertyType(NamedElement):
    """An EnumerationPropertyType."""

    literals = m.Containment["EnumerationPropertyLiteral"](
        "ownedLiterals", (NS, "EnumerationPropertyLiteral")
    )


class EnumerationPropertyLiteral(NamedElement):
    """A Literal for EnumerationPropertyType."""


class PropertyValueGroup(Namespace):
    """A group for PropertyValues."""


class PropertyValuePkg(Structure):
    pass


class AbstractDependenciesPkg(Structure, abstract=True):
    pass
