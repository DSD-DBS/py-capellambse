# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import enum
import typing as t

import capellambse.model as m

from .. import capellacore, modellingcore
from .. import namespaces as ns
from . import datavalue

NS = ns.INFORMATION_DATATYPE
NS_DV = ns.INFORMATION_DATAVALUE


@m.stringy_enum
@enum.unique
class NumericTypeKind(enum.Enum):
    """The kind of this numeric data type."""

    INTEGER = "INTEGER"
    FLOAT = "FLOAT"


class DataType(
    capellacore.GeneralizableElement,
    datavalue.DataValueContainer,
    modellingcore.FinalizableElement,
    abstract=True,
):
    _xmltag = "ownedDataTypes"

    is_discrete = m.BoolPOD("discrete")
    """Whether or not this data type characterizes a discrete value."""
    is_min_inclusive = m.BoolPOD("minInclusive")
    is_max_inclusive = m.BoolPOD("maxInclusive")
    pattern = m.StringPOD("pattern")
    """Textual specification of a constraint associated to this data type."""
    visibility = m.EnumPOD("visibility", capellacore.VisibilityKind)
    information_realizations = m.Containment["InformationRealization"](
        "ownedInformationRealizations",
        (ns.INFORMATION, "InformationRealization"),
    )

    if not t.TYPE_CHECKING:
        min_inclusive = m.DeprecatedAccessor("is_min_inclusive")
        max_inclusive = m.DeprecatedAccessor("is_max_inclusive")


class BooleanType(DataType):
    literals = m.Containment["datavalue.LiteralBooleanValue"](
        "ownedLiterals", (NS_DV, "LiteralBooleanValue"), fixed_length=2
    )
    default_value = m.Single["datavalue.AbstractBooleanValue"](
        m.Containment("ownedDefaultValue", (NS_DV, "AbstractBooleanValue"))
    )
    if not t.TYPE_CHECKING:
        default = m.DeprecatedAccessor("default_value")


class Enumeration(DataType):
    owned_literals = m.Containment["datavalue.EnumerationLiteral"](
        "ownedLiterals", (NS_DV, "EnumerationLiteral")
    )
    default_value = m.Single["datavalue.AbstractEnumerationValue"](
        m.Containment("ownedDefaultValue", (NS_DV, "AbstractEnumerationValue"))
    )
    null_value = m.Single["datavalue.AbstractEnumerationValue"](
        m.Containment("ownedNullValue", (NS_DV, "AbstractEnumerationValue"))
    )
    min_value = m.Single["datavalue.AbstractEnumerationValue"](
        m.Containment("ownedMinValue", (NS_DV, "AbstractEnumerationValue"))
    )
    max_value = m.Single["datavalue.AbstractEnumerationValue"](
        m.Containment("ownedMaxValue", (NS_DV, "AbstractEnumerationValue"))
    )
    domain_type = m.Single["DataType"](
        m.Association((NS, "DataType"), "domainType")
    )

    @property
    def literals(self) -> m.ElementList[datavalue.EnumerationLiteral]:
        """Return all owned and inherited literals."""
        return (
            self.owned_literals + self.super.literals
            if isinstance(self.super, Enumeration)
            else self.owned_literals
        )


class StringType(DataType):
    default_value = m.Single["datavalue.AbstractStringValue"](
        m.Containment("ownedDefaultValue", (NS_DV, "AbstractStringValue"))
    )
    null_value = m.Single["datavalue.AbstractStringValue"](
        m.Containment("ownedNullValue", (NS_DV, "AbstractStringValue"))
    )
    min_length = m.Single["datavalue.NumericValue"](
        m.Containment("ownedMinLength", (NS_DV, "NumericValue"))
    )
    max_length = m.Single["datavalue.NumericValue"](
        m.Containment("ownedMaxLength", (NS_DV, "NumericValue"))
    )


class NumericType(DataType):
    kind = m.EnumPOD("kind", NumericTypeKind)
    default_value = m.Single["datavalue.NumericValue"](
        m.Containment("ownedDefaultValue", (NS_DV, "NumericValue"))
    )
    null_value = m.Single["datavalue.NumericValue"](
        m.Containment("ownedNullValue", (NS_DV, "NumericValue"))
    )
    min_value = m.Single["datavalue.NumericValue"](
        m.Containment("ownedMinValue", (NS_DV, "NumericValue"))
    )
    max_value = m.Single["datavalue.NumericValue"](
        m.Containment("ownedMaxValue", (NS_DV, "NumericValue"))
    )


class PhysicalQuantity(NumericType):
    unit = m.Single["Unit"](m.Association((NS, "Unit"), "unit"))


from . import InformationRealization, Unit  # noqa: F401
