# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import typing as t

import capellambse.model as m

from .. import modeltypes
from .. import namespaces as ns
from . import datavalue

NS = ns.INFORMATION_DATATYPE


class DataType(m.ModelElement):
    _xmltag = "ownedDataTypes"

    is_discrete = m.BoolPOD("discrete")
    """Whether or not this data type characterizes a discrete value."""
    min_inclusive = m.BoolPOD("minInclusive")
    max_inclusive = m.BoolPOD("maxInclusive")
    pattern = m.StringPOD("pattern")
    """Textual specification of a constraint associated to this data type."""
    visibility = m.EnumPOD(
        "visibility", modeltypes.VisibilityKind, default="UNSET"
    )


class BooleanType(DataType):
    literals = m.DirectProxyAccessor(
        datavalue.LiteralBooleanValue,
        aslist=m.ElementList,
        fixed_length=2,
    )
    default = m.Single[t.Any](m.Containment("ownedDefaultValue"))


class Enumeration(DataType):
    """An Enumeration."""

    domain_type = m.Single(m.Association(m.ModelElement, "domainType"))
    owned_literals = m.DirectProxyAccessor(
        datavalue.EnumerationLiteral, aslist=m.ElementList
    )

    sub: m.Accessor
    super: m.Accessor[Enumeration]

    @property
    def literals(self) -> m.ElementList[datavalue.EnumerationLiteral]:
        """Return all owned and inherited literals."""
        return (
            self.owned_literals + self.super.literals
            if isinstance(self.super, Enumeration)
            else self.owned_literals
        )


class StringType(DataType):
    default_value = m.Single[t.Any](m.Containment("ownedDefaultValue"))
    null_value = m.Single[t.Any](m.Containment("ownedNullValue"))
    min_length = m.Single[t.Any](m.Containment("ownedMinLength"))
    max_length = m.Single[t.Any](m.Containment("ownedMaxLength"))


class NumericType(DataType):
    kind = m.EnumPOD("kind", modeltypes.NumericTypeKind, default="INTEGER")
    default_value = m.Single[t.Any](m.Containment("ownedDefaultValue"))
    null_value = m.Single[t.Any](m.Containment("ownedNullValue"))
    min_value = m.Single[t.Any](m.Containment("ownedMinValue"))
    max_value = m.Single[t.Any](m.Containment("ownedMaxValue"))


class PhysicalQuantity(NumericType):
    unit = m.Single[t.Any](m.Containment("ownedUnit"))
