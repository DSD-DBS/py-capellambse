# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import typing as t

from capellambse import modelv2 as m

from . import capellacore
from . import information_datavalue as dv
from . import modellingcore, modeltypes
from . import namespaces as ns

if t.TYPE_CHECKING:
    from . import information as inf

NS = ns.INFORMATION_DATATYPE
DV = ns.INFORMATION_DATAVALUE


class DataType(
    capellacore.GeneralizableElement,
    dv.DataValueContainer,
    modellingcore.FinalizableElement,
    abstract=True,
):
    """Abstract superclass for all data types."""

    is_discrete = m.BoolPOD("discrete")
    """Whether this data type characterizes a discrete value.

    True means this data type characterizes a discrete value, False
    means a continuous value.
    """
    min_inclusive = m.BoolPOD("minInclusive")
    """Whether the minimum value is included in the value range."""
    max_inclusive = m.BoolPOD("maxInclusive")
    """Whether the maximum value is included in the value range."""
    pattern = m.StringPOD("pattern")
    """Textual specification of a constraint associated to this data type."""
    visibility = m.EnumPOD(
        "visibility", modeltypes.VisibilityKind, default="UNSET"
    )


class BooleanType(DataType):
    literals = m.Containment["dv.LiteralBooleanValue"](
        "ownedLiterals", (DV, "LiteralBooleanValue")
    )
    default = m.Single(
        m.Containment["dv.LiteralBooleanValue"](
            "ownedDefaultValue", (DV, "LiteralBooleanValue")
        ),
        enforce="max",
    )


class Enumeration(DataType):
    """An enumeration."""

    literals = m.Containment["dv.EnumerationLiteral"](
        "ownedLiterals", (DV, "EnumerationLiteral")
    )

    sub = m.Backref["Enumeration"]((NS, "Enumeration"), lookup="super")
    super = m.Single(
        m.Allocation["Enumeration"](
            (ns.CAPELLACORE, "Generalization"),
            ("ownedGeneralizations", "super"),
            (NS, "Enumeration"),
        ),
        enforce="max",
    )

    @property
    def available_literals(self) -> m.ElementList[dv.EnumerationLiteral]:
        """Return all literals available in this enumeration.

        This includes both owned literals (see `literals`) and ones
        inherited from super enumerations (recursively).
        """
        if hasattr(self.super, "available_literals"):
            super_literals = self.super.available_literals
        else:
            super_literals = []
        return super_literals + self.literals


class StringType(DataType):
    default_value = m.Single(
        m.Containment["dv.LiteralStringValue"](
            "ownedDefaultValue", (DV, "LiteralStringValue")
        ),
        enforce="max",
    )
    null_value = m.Single(
        m.Containment["dv.LiteralStringValue"](
            "ownedNullValue", (DV, "LiteralStringValue")
        ),
        enforce="max",
    )
    min_length = m.Single(
        m.Containment["dv.LiteralNumericValue"](
            "ownedMinLength", (DV, "LiteralNumericValue")
        ),
        enforce="max",
    )
    max_length = m.Single(
        m.Containment["dv.LiteralNumericValue"](
            "ownedMaxLength", (DV, "LiteralNumericValue")
        ),
        enforce="max",
    )


class NumericType(DataType):
    kind = m.EnumPOD("kind", modeltypes.NumericTypeKind, default="INTEGER")
    default_value = m.Single(
        m.Containment["dv.NumericValue"](
            "ownedDefaultValue", (DV, "NumericValue")
        ),
        enforce="max",
    )
    null_value = m.Single(
        m.Containment["dv.NumericValue"](
            "ownedNullValue", (DV, "NumericValue")
        ),
        enforce="max",
    )
    min_value = m.Single(
        m.Containment["dv.NumericValue"](
            "ownedMinValue", (DV, "NumericValue")
        ),
        enforce="max",
    )
    max_value = m.Single(
        m.Containment["dv.NumericValue"](
            "ownedMaxValue", (DV, "NumericValue")
        ),
        enforce="max",
    )


class PhysicalQuantity(NumericType):
    unit = m.Single(
        m.Containment["inf.Unit"]("ownedUnit", (ns.INFORMATION, "Unit")),
        enforce="max",
    )
