# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import capellambse.model as m

from .. import modeltypes
from . import datavalue


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


@m.xtype_handler(None)
class BooleanType(DataType):
    literals = m.DirectProxyAccessor(
        datavalue.LiteralBooleanValue,
        aslist=m.ElementList,
        fixed_length=2,
    )
    default = m.Containment("ownedDefaultValue")


@m.xtype_handler(None)
class Enumeration(DataType):
    """An Enumeration."""

    domain_type = m.Association(m.ModelElement, "domainType")
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


@m.xtype_handler(None)
class StringType(DataType):
    default_value = m.Containment("ownedDefaultValue")
    null_value = m.Containment("ownedNullValue")
    min_length = m.Containment("ownedMinLength")
    max_length = m.Containment("ownedMaxLength")


@m.xtype_handler(None)
class NumericType(DataType):
    kind = m.EnumPOD("kind", modeltypes.NumericTypeKind, default="INTEGER")
    default_value = m.Containment("ownedDefaultValue")
    null_value = m.Containment("ownedNullValue")
    min_value = m.Containment("ownedMinValue")
    max_value = m.Containment("ownedMaxValue")


@m.xtype_handler(None)
class PhysicalQuantity(NumericType):
    unit = m.Containment("ownedUnit")
