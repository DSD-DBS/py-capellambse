# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import capellambse.model as m


@m.xtype_handler(None)
class Constraint(m.ModelElement):
    """A constraint."""

    _xmltag = "ownedConstraints"

    constrained_elements = m.Association(
        m.ModelElement,
        "constrainedElements",
        aslist=m.MixedElementList,
    )

    specification = m.SpecificationAccessor()


@m.xtype_handler(None)
class Generalization(m.ModelElement):
    """A Generalization."""

    _xmltag = "ownedGeneralizations"

    super: m.Accessor


@m.xtype_handler(None)
class EnumerationPropertyLiteral(m.ModelElement):
    """A Literal for EnumerationPropertyType."""

    _xmltag = "ownedLiterals"


@m.xtype_handler(None)
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

    value: m.BasePOD | m.Association


@m.xtype_handler(None)
class BooleanPropertyValue(PropertyValue):
    """A boolean property value."""

    value = m.BoolPOD("value")


@m.xtype_handler(None)
class FloatPropertyValue(PropertyValue):
    """A floating point property value."""

    value = m.FloatPOD("value")


@m.xtype_handler(None)
class IntegerPropertyValue(PropertyValue):
    """An integer property value."""

    value = m.IntPOD("value")


@m.xtype_handler(None)
class StringPropertyValue(PropertyValue):
    """A string property value."""

    value = m.StringPOD("value")


@m.xtype_handler(None)
class EnumerationPropertyValue(PropertyValue):
    """An enumeration property value."""

    type = m.Association(EnumerationPropertyType, "type")
    value = m.Association(EnumerationPropertyLiteral, "value")


@m.xtype_handler(None)
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


@m.xtype_handler(None)
class PropertyValuePkg(m.ModelElement):
    """A Package for PropertyValues."""

    _xmltag = "ownedPropertyValuePkgs"

    enumeration_property_types = m.DirectProxyAccessor(
        EnumerationPropertyType, aslist=m.ElementList
    )
    groups = m.DirectProxyAccessor(
        PropertyValueGroup,
        aslist=m.ElementList,
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


m.set_self_references(
    (PropertyValuePkg, "packages"),
)
m.set_accessor(
    m.ModelElement,
    "constraints",
    m.DirectProxyAccessor(Constraint, aslist=m.ElementList),
)

m.set_accessor(
    m.ModelElement,
    "property_values",
    m.DirectProxyAccessor(
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
    ),
)
m.set_accessor(
    m.ModelElement,
    "property_value_groups",
    m.DirectProxyAccessor(
        PropertyValueGroup,
        aslist=m.ElementList,
        mapkey="name",
        mapvalue="values",
    ),
)

m.set_accessor(
    m.ModelElement,
    "applied_property_values",
    m.Association(None, "appliedPropertyValues", aslist=m.ElementList),
)
m.set_accessor(
    m.ModelElement,
    "applied_property_value_groups",
    m.Association(None, "appliedPropertyValueGroups", aslist=m.ElementList),
)
