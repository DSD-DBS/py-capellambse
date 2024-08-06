# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
import capellambse.model as m


class LiteralBooleanValue(m.GenericElement):
    """A Literal Boolean Value."""

    _xmltag = "ownedLiterals"

    value = m.BoolPOD("value")


class LiteralValue(m.GenericElement):
    is_abstract = m.BoolPOD("abstract")
    """Indicates if property is abstract."""
    value = m.StringPOD("value")
    type = m.AttrProxyAccessor(m.GenericElement, "abstractType")


@m.xtype_handler(None)
class LiteralNumericValue(LiteralValue):
    value = m.StringPOD("value")
    unit = m.AttrProxyAccessor(m.GenericElement, "unit")


@m.xtype_handler(None)
class LiteralStringValue(LiteralValue):
    """A Literal String Value."""


@m.xtype_handler(None)
class ValuePart(m.GenericElement):
    """A Value Part of a Complex Value."""

    _xmltag = "ownedParts"

    referenced_property = m.AttrProxyAccessor(
        m.GenericElement, "referencedProperty"
    )
    value = m.RoleTagAccessor("ownedValue")


@m.xtype_handler(None)
class ComplexValue(m.GenericElement):
    """A Complex Value."""

    _xmltag = "ownedDataValues"

    type = m.AttrProxyAccessor(m.GenericElement, "abstractType")
    value_parts = m.DirectProxyAccessor(ValuePart, aslist=m.ElementList)


@m.attr_equal("name")
@m.xtype_handler(None)
class EnumerationLiteral(m.GenericElement):
    _xmltag = "ownedLiterals"

    value = m.RoleTagAccessor("domainValue")

    owner: m.Accessor


@m.xtype_handler(None)
class EnumerationReference(m.GenericElement):
    type = m.AttrProxyAccessor(m.GenericElement, "abstractType")
    value = m.AttrProxyAccessor(m.GenericElement, "referencedValue")
