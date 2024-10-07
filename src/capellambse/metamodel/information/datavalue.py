# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import enum
import typing as t
import warnings

import capellambse.model as m

from .. import capellacore, modellingcore
from .. import namespaces as ns

if t.TYPE_CHECKING:
    from . import Property  # noqa: F401

NS = ns.INFORMATION_DATAVALUE


@m.stringy_enum
@enum.unique
class BinaryOperator(enum.Enum):
    """Specifies the kind of this binary operator."""

    UNSET = "UNSET"
    """The binary operator is not initialized."""
    ADD = "ADD"
    """The binary operator refers to an addition."""
    MUL = "MUL"
    """The binary operator refers to a multiplication."""
    SUB = "SUB"
    """The binary operator refers to a substraction."""
    DIV = "DIV"
    """The binary operator refers to a division."""
    POW = "POW"
    """The binary operator refers to a power operation."""
    MIN = "MIN"
    """The binary operator refers to a min operation."""
    MAX = "MAX"
    """The binary operator refers to a max operation."""
    EQU = "EQU"
    """The binary operator refers to an equal operation."""
    IOR = "IOR"
    """The binary operator refers to a logical inclusive OR operation."""
    XOR = "XOR"
    """The binary operator refers to a logical exclusive OR operation."""
    AND = "AND"
    """The binary operator refers to a logical AND operation."""


@m.stringy_enum
@enum.unique
class UnaryOperator(enum.Enum):
    """Specifies the kind of this unary operator."""

    UNSET = "UNSET"
    """The unary operator is not initialized."""
    NOT = "NOT"
    """The unary operator refers to a NOT operation."""
    POS = "POS"
    """The unary operator refers to a position operation."""
    VAL = "VAL"
    """The unary operator refers to a value operation."""
    SUC = "SUC"
    """The unary operator refers to a successor operation."""
    PRE = "PRE"
    """The unary operator refers to a predecessor operation."""


class DataValue(
    capellacore.NamedElement, modellingcore.ValueSpecification, abstract=True
):
    is_abstract = m.BoolPOD("abstract")


class DataValueContainer(capellacore.Structure, abstract=True):
    data_values = m.Containment["DataValue"](
        "ownedDataValues", (NS, "DataValue")
    )

    @property
    def complex_values(self) -> m.ElementList[AbstractComplexValue]:
        warnings.warn(
            (
                f"{type(self).__name__}.complex_values is deprecated,"
                " use '.data_values.by___class__(AbstractComplexValue)' instead"
            ),
            DeprecationWarning,
            stacklevel=2,
        )
        return self.data_values.by___class__(AbstractComplexValue)


class AbstractBooleanValue(DataValue, abstract=True):
    pass


class LiteralBooleanValue(AbstractBooleanValue):
    _xmltag = "ownedLiterals"

    value = m.BoolPOD("value")


class BooleanReference(AbstractBooleanValue):
    value = m.Single["AbstractBooleanValue"](
        m.Association((NS, "AbstractBooleanValue"), "referencedValue")
    )
    property = m.Single["Property"](
        m.Association((NS, "Property"), "referencedProperty")
    )


class AbstractEnumerationValue(DataValue, abstract=True):
    pass


class EnumerationLiteral(AbstractEnumerationValue, eq="name"):
    _xmltag = "ownedLiterals"

    value = m.Single["DataValue"](
        m.Containment("domainValue", (NS, "DataValue"))
    )

    owner = m.DeprecatedAccessor["m.ModelElement"]("parent")


class EnumerationReference(AbstractEnumerationValue):
    value = m.Single["AbstractEnumerationValue"](
        m.Association(m.ModelElement, "referencedValue")
    )
    property = m.Single["Property"](
        m.Association((NS, "Property"), "referencedProperty")
    )


class AbstractStringValue(DataValue, abstract=True):
    pass


class LiteralStringValue(AbstractStringValue):
    value = m.StringPOD("value")


class StringReference(AbstractStringValue):
    value = m.Single["AbstractStringValue"](
        m.Association((NS, "AbstractStringValue"), "referencedValue")
    )
    property = m.Single["Property"](
        m.Association((NS, "Property"), "referencedProperty")
    )


class NumericValue(DataValue, abstract=True):
    unit = m.Single["Unit"](m.Association((NS, "Unit"), "unit"))


class LiteralNumericValue(NumericValue):
    value = m.StringPOD("value")


class NumericReference(NumericValue):
    value = m.Single["NumericValue"](
        m.Association((NS, "NumericValue"), "referencedValue")
    )
    property = m.Single["Property"](
        m.Association((NS, "Property"), "referencedProperty")
    )


class AbstractComplexValue(DataValue, abstract=True):
    pass


class ComplexValue(AbstractComplexValue):
    _xmltag = "ownedDataValues"

    parts = m.Containment["ValuePart"]("ownedParts", (NS, "ValuePart"))
    value_parts = m.DeprecatedAccessor["ValuePart"]("parts")


class ComplexValueReference(AbstractComplexValue):
    value = m.Single["AbstractComplexValue"](
        m.Association((NS, "AbstractComplexValue"), "referencedValue")
    )
    property = m.Single["Property"](
        m.Association((NS, "Property"), "referencedProperty")
    )


class ValuePart(capellacore.CapellaElement):
    _xmltag = "ownedParts"

    referenced_property = m.Single["Property"](
        m.Association((NS, "Property"), "referencedProperty")
    )
    value = m.Single["DataValue"](
        m.Containment("ownedValue", (NS, "DataValue"))
    )


class AbstractExpressionValue(
    AbstractBooleanValue,
    AbstractComplexValue,
    AbstractEnumerationValue,
    NumericValue,
    AbstractStringValue,
    abstract=True,
):
    expression = m.StringPOD("expression")
    unparsed_expression = m.StringPOD("unparsedExpression")


class BinaryExpression(AbstractExpressionValue):
    operator = m.EnumPOD("operator", BinaryOperator)
    left_operand = m.Containment["DataValue"](
        "ownedLeftOperand", (NS, "DataValue")
    )
    right_operand = m.Containment["DataValue"](
        "ownedRightOperand", (NS, "DataValue")
    )


class UnaryExpression(AbstractExpressionValue):
    operator = m.EnumPOD("operator", UnaryOperator)
    operand = m.Containment["DataValue"]("ownedOperand", (NS, "DataValue"))


class OpaqueExpression(
    capellacore.CapellaElement, modellingcore.ValueSpecification
):
    # TODO reimplement specification stuff
    bodies = m.StringPOD("bodies")
    languages = m.StringPOD("languages")


if t.TYPE_CHECKING:

    def __getattr__(name):
        if name == "LiteralValue":
            warnings.warn(
                (
                    "LiteralValue has been dissolved,"
                    " use the DataValue ABC or a concrete subclass instead"
                ),
                DeprecationWarning,
                stacklevel=2,
            )
            return DataValue
        raise AttributeError(name)
