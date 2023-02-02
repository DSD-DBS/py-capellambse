# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from .. import common as c


@c.xtype_handler(None)
class Constraint(c.GenericElement):
    """A constraint."""

    _xmltag = "ownedConstraints"

    constrained_elements = c.AttrProxyAccessor(
        c.GenericElement,
        "constrainedElements",
        aslist=c.MixedElementList,
    )

    specification = c.SpecificationAccessor()


@c.xtype_handler(None)
class Generalization(c.GenericElement):
    """A Generalization."""

    _xmltag = "ownedGeneralizations"


@c.xtype_handler(None)
class EnumerationPropertyLiteral(c.GenericElement):
    """A Literal for EnumerationPropertyType."""

    _xmltag = "ownedLiterals"


@c.xtype_handler(None)
class EnumerationPropertyType(c.GenericElement):
    """An EnumerationPropertyType."""

    _xmltag = "ownedEnumerationPropertyTypes"

    literals = c.DirectProxyAccessor(
        EnumerationPropertyLiteral, aslist=c.ElementList
    )


class PropertyValue(c.GenericElement):
    """Abstract base class for PropertyValues."""

    _xmltag = "ownedPropertyValues"

    enumerations = c.DirectProxyAccessor(
        EnumerationPropertyType, aslist=c.ElementList
    )

    value: c.AttributeProperty | c.AttrProxyAccessor


@c.xtype_handler(None)
class BooleanPropertyValue(PropertyValue):
    """A boolean property value."""

    value = c.BooleanAttributeProperty("value")


@c.xtype_handler(None)
class FloatPropertyValue(PropertyValue):
    """A floating point property value."""

    value = c.AttributeProperty("value", returntype=float, default=0.0)


@c.xtype_handler(None)
class IntegerPropertyValue(PropertyValue):
    """An integer property value."""

    value = c.AttributeProperty("value", returntype=int, default=0)


@c.xtype_handler(None)
class StringPropertyValue(PropertyValue):
    """A string property value."""

    value = c.AttributeProperty("value", default="")


@c.xtype_handler(None)
class EnumerationPropertyValue(PropertyValue):
    """An enumeration property value."""

    type = c.AttrProxyAccessor(EnumerationPropertyType, "type")
    value = c.AttrProxyAccessor(EnumerationPropertyLiteral, "value")


@c.xtype_handler(None)
class PropertyValueGroup(c.GenericElement):
    """A group for PropertyValues."""

    _xmltag = "ownedPropertyValueGroups"

    values = c.DirectProxyAccessor(
        c.GenericElement,
        (
            StringPropertyValue,
            BooleanPropertyValue,
            IntegerPropertyValue,
            FloatPropertyValue,
            EnumerationPropertyValue,
        ),
        aslist=c.ElementList,
        list_extra_args={"mapkey": "name", "mapvalue": "value"},
    )


@c.xtype_handler(None)
class PropertyValuePkg(c.GenericElement):
    """A Package for PropertyValues."""

    _xmltag = "ownedPropertyValuePkgs"

    enumeration_property_types = c.DirectProxyAccessor(
        EnumerationPropertyType, aslist=c.ElementList
    )
    groups = c.DirectProxyAccessor(
        PropertyValueGroup,
        aslist=c.ElementList,
        list_extra_args={"mapkey": "name", "mapvalue": "values"},
    )
    values = c.DirectProxyAccessor(
        c.GenericElement,
        (
            StringPropertyValue,
            BooleanPropertyValue,
            IntegerPropertyValue,
            FloatPropertyValue,
            EnumerationPropertyValue,
        ),
        aslist=c.ElementList,
        list_extra_args={"mapkey": "name", "mapvalue": "value"},
    )


c.set_self_references(
    (PropertyValuePkg, "packages"),
)
c.set_accessor(
    c.GenericElement,
    "constraints",
    c.DirectProxyAccessor(Constraint, aslist=c.ElementList),
)

c.set_accessor(
    c.GenericElement,
    "property_values",
    c.DirectProxyAccessor(
        c.GenericElement,
        (
            BooleanPropertyValue,
            EnumerationPropertyValue,
            FloatPropertyValue,
            IntegerPropertyValue,
            StringPropertyValue,
        ),
        aslist=c.MixedElementList,
        list_extra_args={"mapkey": "name", "mapvalue": "value"},
    ),
)
c.set_accessor(
    c.GenericElement,
    "property_value_groups",
    c.DirectProxyAccessor(
        PropertyValueGroup,
        aslist=c.ElementList,
        list_extra_args={"mapkey": "name", "mapvalue": "values"},
    ),
)

c.set_accessor(
    c.GenericElement,
    "applied_property_values",
    c.AttrProxyAccessor(None, "appliedPropertyValues", aslist=c.ElementList),
)
c.set_accessor(
    c.GenericElement,
    "applied_property_value_groups",
    c.AttrProxyAccessor(
        None, "appliedPropertyValueGroups", aslist=c.ElementList
    ),
)
