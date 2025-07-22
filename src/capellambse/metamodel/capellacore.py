# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import collections.abc as cabc
import enum
import sys
import typing as t
import warnings

import capellambse.model as m

from . import modellingcore
from . import namespaces as ns

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

NS = ns.CAPELLACORE


@m.stringy_enum
@enum.unique
class VisibilityKind(enum.Enum):
    """The possibilities regarding the visibility of a feature of a class."""

    UNSET = "UNSET"
    """Visibility is not specified."""
    PUBLIC = "PUBLIC"
    """The feature offers public access."""
    PROTECTED = "PROTECTED"
    """The feature offers visibility only to children of the class."""
    PRIVATE = "PRIVATE"
    """The feature is only visible/accessible from the class itself."""
    PACKAGE = "PACKAGE"
    """The feature is accessible from any element within the same package."""


class CapellaElement(
    modellingcore.TraceableElement,
    modellingcore.PublishableElement,
    abstract=True,
):
    summary = m.StringPOD("summary")
    """Summary of the element."""
    description = m.HTMLStringPOD("description")
    """Description of the Capella element."""
    review = m.StringPOD("review")
    """Review description on the Capella element."""

    property_values = m.Containment["AbstractPropertyValue"](
        "ownedPropertyValues",
        (NS, "AbstractPropertyValue"),
        mapkey="name",
        mapvalue="value",
    )
    enumeration_property_types = m.Containment["EnumerationPropertyType"](
        "ownedEnumerationPropertyTypes", (NS, "EnumerationPropertyType")
    )
    applied_property_values = m.Association["AbstractPropertyValue"](
        (NS, "AbstractPropertyValue"), "appliedPropertyValues"
    )
    property_value_groups = m.Containment["PropertyValueGroup"](
        "ownedPropertyValueGroups",
        (NS, "PropertyValueGroup"),
        mapkey="name",
        mapvalue="property_values",
    )
    applied_property_value_groups = m.Association["PropertyValueGroup"](
        (NS, "PropertyValueGroup"), "appliedPropertyValueGroups"
    )
    status = m.Single["EnumerationPropertyLiteral"](
        m.Association((NS, "EnumerationPropertyLiteral"), "status")
    )
    features = m.Association["EnumerationPropertyLiteral"](
        (NS, "EnumerationPropertyLiteral"), "features"
    )


class NamedElement(
    modellingcore.AbstractNamedElement, CapellaElement, abstract=True
):
    pass


class Relationship(
    modellingcore.AbstractRelationship, CapellaElement, abstract=True
):
    pass


class Namespace(NamedElement, abstract=True):
    traces = m.Containment["Trace"]("ownedTraces", (NS, "Trace"))
    naming_rules = m.Containment["NamingRule"](
        "namingRules", (NS, "NamingRule")
    )


class NamedRelationship(Relationship, NamedElement, abstract=True):
    naming_rules = m.Containment["NamingRule"](
        "namingRules", (NS, "NamingRule")
    )


class Structure(Namespace, abstract=True):
    property_value_pkgs = m.Containment["PropertyValuePkg"](
        "ownedPropertyValuePkgs",
        (NS, "PropertyValuePkg"),
        mapkey="name",
    )

    if not t.TYPE_CHECKING:
        property_value_packages = m.DeprecatedAccessor("property_value_pkgs")


class ReuserStructure(Structure, abstract=True):
    reuse_links = m.Association["ReuseLink"]((NS, "ReuseLink"), "reuseLinks")
    owned_reuse_links = m.Containment["ReuseLink"](
        "ownedReuseLinks", (NS, "ReuseLink")
    )


class AbstractModellingStructure(ReuserStructure, abstract=True):
    architectures = m.Containment["ModellingArchitecture"](
        "ownedArchitectures", (NS, "ModellingArchitecture")
    )
    architecture_pkgs = m.Containment["ModellingArchitecturePkg"](
        "ownedArchitecturePkgs", (NS, "ModellingArchitecturePkg")
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


class Trace(Relationship, modellingcore.AbstractTrace, abstract=True):
    pass


class AbstractAnnotation(CapellaElement, abstract=True):
    content = m.StringPOD("content")


class NamingRule(AbstractAnnotation):
    target_type = m.StringPOD("targetType")
    """Type to whose instances the naming rule has to be applied."""


class Constraint(NamedElement, modellingcore.AbstractConstraint):
    """A condition or restriction.

    The constraint is expressed in natural language text or in a machine
    readable language for the purpose of declaring some of the semantics
    of an element.
    """

    _xmltag = "ownedConstraints"


class KeyValue(CapellaElement):
    key = m.StringPOD("key")
    value = m.StringPOD("value")


class ReuseLink(Relationship):
    reused = m.Single["ReuseableStructure"](
        m.Association((NS, "ReuseableStructure"), "reused")
    )
    reuser = m.Single["ReuserStructure"](
        m.Association((NS, "ReuserStructure"), "reuser")
    )


class ReuseableStructure(Structure, abstract=True):
    """A structure intended to be reused across various architectures."""

    reuse_links = m.Association["ReuseLink"]((NS, "ReuseLink"), "reuseLinks")


class GeneralizableElement(Type, abstract=True):
    """A type than can be generalized."""

    is_abstract = m.BoolPOD("abstract")
    generalizations = m.Containment["Generalization"](
        "ownedGeneralizations", (NS, "Generalization")
    )
    sub = m.Backref["GeneralizableElement"](
        (NS, "GeneralizableElement"), "super", legacy_by_type=True
    )
    super = m.Single["GeneralizableElement"](
        m.Allocation(
            "ownedGeneralizations",
            (NS, "Generalization"),
            (NS, "GeneralizableElement"),
            attr="super",
            backattr="sub",
        )
    )


class Classifier(GeneralizableElement, abstract=True):
    owned_features = m.Containment["Feature"]("ownedFeatures", (NS, "Feature"))


class GeneralClass(
    Classifier, modellingcore.FinalizableElement, abstract=True
):
    visibility = m.EnumPOD("visibility", VisibilityKind)
    nested_classes = m.Containment["GeneralClass"](
        "nestedGeneralClasses", (NS, "GeneralClass")
    )


class Generalization(Relationship):
    _xmltag = "ownedGeneralizations"

    super = m.Single["GeneralizableElement"](
        m.Association((NS, "GeneralizableElement"), "super")
    )
    sub = m.Single["GeneralizableElement"](
        m.Association((NS, "GeneralizableElement"), "sub")
    )


class Feature(NamedElement, abstract=True):
    is_abstract = m.BoolPOD("isAbstract")
    is_static = m.BoolPOD("isStatic")
    visibility = m.EnumPOD("visibility", VisibilityKind)


class AbstractExchangeItemPkg(Structure, abstract=True):
    exchange_items = m.Containment["information.ExchangeItem"](
        "ownedExchangeItems", (ns.INFORMATION, "ExchangeItem")
    )


class Allocation(Relationship, modellingcore.AbstractTrace, abstract=True):
    pass


class Involvement(Relationship, abstract=True):
    involved = m.Single["InvolvedElement"](
        m.Association((NS, "InvolvedElement"), "involved")
    )

    @property
    @deprecated("Synthetic names are deprecated", category=FutureWarning)
    def name(self) -> str:
        """Return the name."""
        direction = ""
        try:
            if self.involved is not None:
                direction = f" to {self.involved.name} ({self.involved.uuid})"
        except AttributeError:
            pass

        return f"[{self.__class__.__name__}]{direction}"

    if not t.TYPE_CHECKING:
        source = m.DeprecatedAccessor("parent")
        target = m.DeprecatedAccessor("involved")


class InvolverElement(CapellaElement, abstract=True):
    pass


class InvolvedElement(CapellaElement, abstract=True):
    pass


class AbstractPropertyValue(NamedElement, abstract=True):
    _xmltag = "ownedPropertyValues"

    involved_elements = m.Association["CapellaElement"](
        (NS, "CapellaElement"), "involvedElements"
    )

    if not t.TYPE_CHECKING:
        enumerations = m.DeprecatedAccessor("enumeration_property_types")


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
    type = m.Single["EnumerationPropertyType"](
        m.Association((NS, "EnumerationPropertyType"), "type")
    )
    value = m.Single["EnumerationPropertyLiteral"](
        m.Association((NS, "EnumerationPropertyLiteral"), "value")
    )


class EnumerationPropertyType(NamedElement):
    _xmltag = "ownedEnumerationPropertyTypes"

    literals = m.Containment["EnumerationPropertyLiteral"](
        "ownedLiterals", (NS, "EnumerationPropertyLiteral")
    )


class EnumerationPropertyLiteral(NamedElement):
    """A Literal for EnumerationPropertyType."""

    _xmltag = "ownedLiterals"


class PropertyValueGroup(Namespace, cabc.MutableMapping[str, str]):
    """A group for PropertyValues."""

    _xmltag = "ownedPropertyValueGroups"

    def __getitem__(self, k: str, /) -> t.Any:
        return self.property_values.by_name(k).value

    def __setitem__(self, k: str, v: t.Any, /) -> None:
        self.property_values.by_name(k).value = v

    def __delitem__(self, k: str, /) -> None:
        self.property_values.delete_all(name=k)

    def __iter__(self) -> cabc.Iterator[str]:
        for prop in self.property_values:
            yield prop.name

    def __len__(self) -> int:
        return sum(1 for _ in self)

    if not t.TYPE_CHECKING:
        values = m.DeprecatedAccessor("property_values")


class PropertyValuePkg(Structure):
    """A Package for PropertyValues."""

    _xmltag = "ownedPropertyValuePkgs"

    packages = m.Alias["m.ElementList[PropertyValuePkg]"](
        "property_value_pkgs", dirhide=False
    )
    groups = m.Alias["m.ElementList[PropertyValueGroup]"](
        "property_value_groups", dirhide=False
    )
    values = m.Alias["m.ElementList[AbstractPropertyValue]"](
        "property_values", dirhide=False
    )


class AbstractDependenciesPkg(Structure, abstract=True):
    pass


if not t.TYPE_CHECKING:

    def __getattr__(attr):
        if attr == "PropertyValue":
            warnings.warn(
                "PropertyValue has been renamed to AbstractPropertyValue",
                DeprecationWarning,
                stacklevel=2,
            )
            return AbstractPropertyValue

        raise AttributeError(f"{__name__} has no attribute {attr}")


from . import information  # noqa: F401
