# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0


from ... import common as c


class LiteralBooleanValue(c.GenericElement):
    """A Literal Boolean Value."""

    _xmltag = "ownedLiterals"

    value = c.BooleanAttributeProperty("value")


class LiteralValue(c.GenericElement):
    is_abstract = c.BooleanAttributeProperty(
        "abstract", __doc__="Indicates if property is abstract"
    )
    value = c.AttributeProperty("value", optional=True, returntype=str)
    type = c.AttrProxyAccessor(c.GenericElement, "abstractType")


@c.xtype_handler(None)
class LiteralNumericValue(LiteralValue):
    value = c.AttributeProperty("value", optional=True)
    unit = c.AttrProxyAccessor(c.GenericElement, "unit")


@c.xtype_handler(None)
class LiteralStringValue(LiteralValue):
    """A Literal String Value."""


@c.xtype_handler(None)
class ValuePart(c.GenericElement):
    """A Value Part of a Complex Value."""

    _xmltag = "ownedParts"

    referenced_property = c.AttrProxyAccessor(
        c.GenericElement, "referencedProperty"
    )
    value = c.RoleTagAccessor("ownedValue")


@c.xtype_handler(None)
class ComplexValue(c.GenericElement):
    """A Complex Value."""

    _xmltag = "ownedDataValues"

    type = c.AttrProxyAccessor(c.GenericElement, "abstractType")
    value_parts = c.DirectProxyAccessor(ValuePart, aslist=c.ElementList)


@c.attr_equal("name")
@c.xtype_handler(None)
class EnumerationLiteral(c.GenericElement):
    """An EnumerationLiteral (proxy link)."""

    _xmltag = "ownedLiterals"

    name = c.AttributeProperty("name", returntype=str)
    value = c.RoleTagAccessor("domainValue")

    owner: c.Accessor

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.name == other
        return super().__eq__(other)


@c.xtype_handler(None)
class EnumerationReference(c.GenericElement):
    name = c.AttributeProperty("name", returntype=str)
    type = c.AttrProxyAccessor(c.GenericElement, "abstractType")
    value = c.AttrProxyAccessor(c.GenericElement, "referencedValue")
