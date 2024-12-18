# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import typing as t

import capellambse.model as m

from . import namespaces as ns

NS = ns.CAPELLACORE


class Constraint(m.ModelElement):
    """A constraint."""

    _xmltag = "ownedConstraints"

    constrained_elements = m.Association(
        m.ModelElement, "constrainedElements", legacy_by_type=True
    )

    specification = m.SpecificationAccessor()


class Generalization(m.ModelElement):
    """A Generalization."""

    _xmltag = "ownedGeneralizations"

    super: m.Accessor


class EnumerationPropertyLiteral(m.ModelElement):
    """A Literal for EnumerationPropertyType."""

    _xmltag = "ownedLiterals"


class EnumerationPropertyType(m.ModelElement):
    """An EnumerationPropertyType."""

    _xmltag = "ownedEnumerationPropertyTypes"

    literals = m.DirectProxyAccessor(
        EnumerationPropertyLiteral, aslist=m.ElementList
    )


class PropertyValue(m.ModelElement):
    """Abstract base class for PropertyValues."""

    _xmltag = "ownedPropertyValues"

    enumerations = m.DirectProxyAccessor(
        EnumerationPropertyType, aslist=m.ElementList
    )

    value: t.ClassVar[m.BasePOD | m.Single]


class BooleanPropertyValue(PropertyValue):
    """A boolean property value."""

    value = m.BoolPOD("value")


class FloatPropertyValue(PropertyValue):
    """A floating point property value."""

    value = m.FloatPOD("value")


class IntegerPropertyValue(PropertyValue):
    """An integer property value."""

    value = m.IntPOD("value")


class StringPropertyValue(PropertyValue):
    """A string property value."""

    value = m.StringPOD("value")


class EnumerationPropertyValue(PropertyValue):
    """An enumeration property value."""

    type = m.Single(m.Association(EnumerationPropertyType, "type"))
    value = m.Single(m.Association(EnumerationPropertyLiteral, "value"))


class PropertyValueGroup(m.ModelElement):
    """A group for PropertyValues."""

    _xmltag = "ownedPropertyValueGroups"

    values = m.DirectProxyAccessor(
        m.ModelElement,
        (
            StringPropertyValue,
            BooleanPropertyValue,
            IntegerPropertyValue,
            FloatPropertyValue,
            EnumerationPropertyValue,
        ),
        aslist=m.ElementList,
        mapkey="name",
        mapvalue="value",
    )


class PropertyValuePkg(m.ModelElement):
    """A Package for PropertyValues."""

    _xmltag = "ownedPropertyValuePkgs"

    enumeration_property_types = m.DirectProxyAccessor(
        EnumerationPropertyType, aslist=m.ElementList
    )
    groups = m.Containment["PropertyValueGroup"](
        "ownedPropertyValueGroups",
        PropertyValueGroup,
        mapkey="name",
        mapvalue="values",
    )
    values = m.DirectProxyAccessor(
        m.ModelElement,
        (
            StringPropertyValue,
            BooleanPropertyValue,
            IntegerPropertyValue,
            FloatPropertyValue,
            EnumerationPropertyValue,
        ),
        aslist=m.ElementList,
        mapkey="name",
        mapvalue="value",
    )


PropertyValuePkg.packages = m.DirectProxyAccessor(
    PropertyValuePkg, aslist=m.ElementList
)
m.ModelElement.extensions = m.Containment(
    "ownedExtensions", aslist=m.ElementList
)
m.ModelElement.constraints = m.DirectProxyAccessor(
    Constraint, aslist=m.ElementList
)

m.ModelElement.property_values = m.DirectProxyAccessor(
    m.ModelElement,
    (
        BooleanPropertyValue,
        EnumerationPropertyValue,
        FloatPropertyValue,
        IntegerPropertyValue,
        StringPropertyValue,
    ),
    aslist=m.MixedElementList,
    mapkey="name",
    mapvalue="value",
)
m.ModelElement.property_value_groups = m.DirectProxyAccessor(
    PropertyValueGroup,
    aslist=m.ElementList,
    mapkey="name",
    mapvalue="values",
)

m.ModelElement.applied_property_values = m.Association(
    None, "appliedPropertyValues"
)
m.ModelElement.applied_property_value_groups = m.Association(
    None, "appliedPropertyValueGroups"
)
