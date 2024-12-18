# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
import capellambse.model as m


@m.xtype_handler(None)
class LiteralBooleanValue(m.ModelElement):
    """A Literal Boolean Value."""

    _xmltag = "ownedLiterals"

    value = m.BoolPOD("value")


class LiteralValue(m.ModelElement):
    is_abstract = m.BoolPOD("abstract")
    """Indicates if property is abstract."""
    value = m.StringPOD("value")
    type = m.Association(m.ModelElement, "abstractType")


@m.xtype_handler(None)
class LiteralNumericValue(LiteralValue):
    value = m.StringPOD("value")
    unit = m.Association(m.ModelElement, "unit")


@m.xtype_handler(None)
class LiteralStringValue(LiteralValue):
    """A Literal String Value."""


@m.xtype_handler(None)
class ValuePart(m.ModelElement):
    """A Value Part of a Complex Value."""

    _xmltag = "ownedParts"

    referenced_property = m.Association(m.ModelElement, "referencedProperty")
    value = m.Containment("ownedValue")


@m.xtype_handler(None)
class ComplexValue(m.ModelElement):
    """A Complex Value."""

    _xmltag = "ownedDataValues"

    type = m.Association(m.ModelElement, "abstractType")
    value_parts = m.DirectProxyAccessor(ValuePart, aslist=m.ElementList)


@m.attr_equal("name")
@m.xtype_handler(None)
class EnumerationLiteral(m.ModelElement):
    _xmltag = "ownedLiterals"

    value = m.Containment("domainValue")

    owner = m.ParentAccessor["_dt.Enumeration"]()


@m.xtype_handler(None)
class EnumerationReference(m.ModelElement):
    type = m.Association(m.ModelElement, "abstractType")
    value = m.Association(m.ModelElement, "referencedValue")


from . import datatype as _dt  # noqa: F401
