# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
import typing as t

import capellambse.model as m

from .. import namespaces as ns

NS = ns.INFORMATION_DATAVALUE


class LiteralBooleanValue(m.ModelElement):
    """A Literal Boolean Value."""

    _xmltag = "ownedLiterals"

    value = m.BoolPOD("value")


class LiteralValue(m.ModelElement):
    is_abstract = m.BoolPOD("abstract")
    """Indicates if property is abstract."""
    value = m.StringPOD("value")
    type = m.Single(m.Association(m.ModelElement, "abstractType"))


class LiteralNumericValue(LiteralValue):
    value = m.StringPOD("value")
    unit = m.Single(m.Association(m.ModelElement, "unit"))


class LiteralStringValue(LiteralValue):
    """A Literal String Value."""


class ValuePart(m.ModelElement):
    """A Value Part of a Complex Value."""

    _xmltag = "ownedParts"

    referenced_property = m.Single(
        m.Association(m.ModelElement, "referencedProperty")
    )
    value = m.Single[t.Any](m.Containment("ownedValue"))


class ComplexValue(m.ModelElement):
    """A Complex Value."""

    _xmltag = "ownedDataValues"

    type = m.Single(m.Association(m.ModelElement, "abstractType"))
    value_parts = m.DirectProxyAccessor(ValuePart, aslist=m.ElementList)


class EnumerationLiteral(m.ModelElement, eq="name"):
    _xmltag = "ownedLiterals"

    value = m.Single[t.Any](m.Containment("domainValue"))

    owner = m.ParentAccessor()


class EnumerationReference(m.ModelElement):
    type = m.Single(m.Association(m.ModelElement, "abstractType"))
    value = m.Single(m.Association(m.ModelElement, "referencedValue"))


from . import datatype as _dt  # noqa: F401
