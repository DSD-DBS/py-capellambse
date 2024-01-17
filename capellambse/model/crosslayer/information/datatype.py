# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from ... import common as c
from ... import modeltypes
from . import datavalue


class DataType(c.GenericElement):
    _xmltag = "ownedDataTypes"

    is_discrete = c.BooleanAttributeProperty(
        "discrete",
        __doc__=(
            "Specifies whether or not this data type characterizes a discrete"
            " value (versus continuous value)"
        ),
    )
    min_inclusive = c.BooleanAttributeProperty("minInclusive")
    max_inclusive = c.BooleanAttributeProperty("maxInclusive")
    pattern = c.AttributeProperty(
        "pattern",
        __doc__=(
            "Textual specification of a constraint associated to this data"
            " type"
        ),
    )
    visibility = c.EnumAttributeProperty(
        "visibility", modeltypes.VisibilityKind, default="UNSET"
    )


@c.xtype_handler(None)
class BooleanType(DataType):
    literals = c.DirectProxyAccessor(
        datavalue.LiteralBooleanValue,
        aslist=c.ElementList,
        list_extra_args={"fixed_length": 2},
    )
    default = c.RoleTagAccessor("ownedDefaultValue")


@c.xtype_handler(None)
class Enumeration(DataType):
    """An Enumeration."""

    owned_literals = c.DirectProxyAccessor(
        datavalue.EnumerationLiteral, aslist=c.ElementList
    )

    sub: c.Accessor
    super: c.Accessor[Enumeration]

    @property
    def literals(self) -> c.ElementList[datavalue.EnumerationLiteral]:
        """Return all owned and inherited literals."""
        return (
            self.owned_literals + self.super.literals
            if isinstance(self.super, Enumeration)
            else self.owned_literals
        )


@c.xtype_handler(None)
class StringType(DataType):
    default_value = c.RoleTagAccessor("ownedDefaultValue")
    null_value = c.RoleTagAccessor("ownedNullValue")
    min_length = c.RoleTagAccessor("ownedMinLength")
    max_length = c.RoleTagAccessor("ownedMaxLength")


@c.xtype_handler(None)
class NumericType(DataType):
    kind = c.EnumAttributeProperty(
        "kind", modeltypes.NumericTypeKind, default="INTEGER"
    )
    default_value = c.RoleTagAccessor("ownedDefaultValue")
    null_value = c.RoleTagAccessor("ownedNullValue")
    min_value = c.RoleTagAccessor("ownedMinValue")
    max_value = c.RoleTagAccessor("ownedMaxValue")


@c.xtype_handler(None)
class PhysicalQuantity(NumericType):
    unit = c.RoleTagAccessor("ownedUnit")
