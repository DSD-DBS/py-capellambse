# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import collections.abc as cabc
import logging
import typing as t

import typing_extensions as te
from lxml import etree

from capellambse import modelv2 as m

from .. import capellacore, modellingcore, modeltypes
from .. import namespaces as ns

if t.TYPE_CHECKING:
    from . import Property, Unit
    from . import datatype as dt

LOGGER = logging.getLogger(__name__)

NS = ns.INFORMATION_DATAVALUE
INF = ns.INFORMATION
DT = ns.INFORMATION_DATATYPE


class DataValue(
    capellacore.NamedElement,
    modellingcore.ValueSpecification,
    abstract=True,
):
    """Abstract base class for all data values."""

    is_abstract = m.BoolPOD("abstract")
    type = m.Single["capellacore.Type"](
        m.Association(None, (ns.CAPELLACORE, "Type")),
        enforce="max",
    )


class DataValueContainer(capellacore.Structure, abstract=True):
    """Container for DataValue elements."""

    data_values = m.Containment["DataValue"](
        "ownedDataValues", (NS, "DataValue")
    )


class AbstractBooleanValue(DataValue, abstract=True):
    """Base class for custom boolean values."""

    type = m.Single["dt.BooleanType"](
        m.Association(None, (DT, "BooleanType")),
        enforce="max",
    )


class LiteralBooleanValue(AbstractBooleanValue):
    """A literal boolean value."""

    value = m.BoolPOD("value")


class BooleanReference(AbstractBooleanValue):
    """A reference to a boolean value."""

    referenced_value = m.Single(
        m.Association["LiteralBooleanValue | BooleanReference"](
            "referencedValue", (NS, "AbstractBooleanValue")
        ),
        enforce="max",
    )
    referenced_property = m.Single(
        m.Association["Property"]("referencedProperty", (INF, "Property")),
        enforce="max",
    )

    @property
    def value(self) -> bool:
        return self.referenced_value.value


class AbstractEnumerationValue(DataValue, abstract=True):
    """Base class for custom enumeration values."""

    type = m.Single["dt.Enumeration"](
        m.Association(None, (DT, "Enumeration")),
        enforce="max",
    )


class EnumerationLiteral(AbstractEnumerationValue, eq="name"):
    """An enumeration literal."""

    value = m.Single(
        m.Containment["DataValue"]("domainValue", (NS, "DataValue")),
        enforce="max",
    )


class EnumerationReference(AbstractEnumerationValue):
    """A reference to an enumeration value."""

    referenced_value = m.Single(
        m.Association["EnumerationLiteral | EnumerationReference"](
            "referencedValue", (NS, "AbstractEnumerationValue")
        ),
        enforce="max",
    )
    referenced_property = m.Single(
        m.Association["Property"]("referencedProperty", (INF, "Property")),
        enforce="max",
    )


class AbstractStringValue(DataValue, abstract=True):
    """Base class for custom string values."""

    type = m.Single["dt.StringType"](
        m.Association(None, (DT, "StringType")),
        enforce="max",
    )


class LiteralStringValue(AbstractStringValue):
    """A literal string value."""

    value = m.StringPOD("value")


class StringReference(AbstractStringValue):
    """A reference to a string value."""

    referenced_value = m.Single(
        m.Association["LiteralStringValue | StringReference"](
            "referencedValue", (NS, "AbstractStringValue")
        ),
        enforce="max",
    )
    referenced_property = m.Single(
        m.Association["Property"]("referencedProperty", (INF, "Property")),
        enforce="max",
    )

    @property
    def value(self) -> str:
        return self.referenced_value.value


class NumericValue(DataValue, abstract=True):
    """Abstract base class for all numeric values."""

    type = m.Single["dt.NumericType"](
        m.Association(None, (DT, "NumericType")),
        enforce="max",
    )
    unit = m.Association["Unit"]("unit", (INF, "Unit"))


class LiteralNumericValue(NumericValue):
    """A literal numeric value."""

    value = m.StringPOD("value")


class NumericReference(NumericValue):
    """A reference to a numeric value."""

    referenced_value = m.Single["LiteralNumericValue | NumericReference"](
        m.Association("referencedValue", (NS, "NumericValue")),
        enforce="max",
    )
    referenced_property = m.Single["Property"](
        m.Association("referencedProperty", (INF, "Property")),
        enforce="max",
    )

    @property
    def value(self) -> str:
        return self.referenced_value.value


class AbstractComplexValue(DataValue, abstract=True):
    """Base class for custom complex values."""

    type = m.Single["capellacore.Classifier"](
        m.Association(None, (ns.CAPELLACORE, "Classifier")),
        enforce="max",
    )


class ComplexValue(AbstractComplexValue):
    """A complex value."""

    parts = m.Containment["ValuePart"]("ownedParts", (NS, "ValuePart"))


class ComplexValueReference(AbstractComplexValue):
    """A reference to a complex value."""

    referenced_value = m.Single["ComplexValue | ComplexValueReference"](
        m.Association("referencedValue", (NS, "AbstractComplexValue")),
        enforce="max",
    )
    referenced_property = m.Single["Property"](
        m.Association("referencedProperty", (INF, "Property")),
        enforce="max",
    )

    @property
    def parts(self) -> m.ElementList[ValuePart]:
        return self.referenced_value.parts


class ValuePart(capellacore.CapellaElement):
    """A value part of a complex value."""

    referenced_property = m.Association["Property"](
        "referencedProperty", (INF, "Property")
    )
    value = m.Containment["DataValue"]("ownedValue", (NS, "DataValue"))


class AbstractExpressionValue(
    AbstractBooleanValue,
    AbstractComplexValue,
    AbstractEnumerationValue,
    NumericValue,
    AbstractStringValue,
    abstract=True,
):
    """Base class for custom expression values."""

    type = m.Single["dt.DataType"](  # type: ignore[assignment]
        m.Association("abstractType", (DT, "DataType")),
        enforce=False,
    )

    unparsed_expression = m.StringPOD("unparsedExpression")


class BinaryExpression(AbstractExpressionValue):
    """A binary expression."""

    operator = m.EnumPOD(
        "operator", modeltypes.BinaryOperator, default="UNSET"
    )
    left = m.Single(
        m.Containment["DataValue"]("ownedLeftOperand", (NS, "DataValue")),
        enforce="max",
    )
    right = m.Single(
        m.Containment["DataValue"]("ownedRightOperand", (NS, "DataValue")),
        enforce="max",
    )


class UnaryExpression(AbstractExpressionValue):
    """A unary expression."""

    operator = m.EnumPOD("operator", modeltypes.UnaryOperator, default="UNSET")
    operand = m.Single(
        m.Containment["DataValue"]("ownedOperand", (NS, "DataValue")),
        enforce="max",
    )


class OpaqueExpression(
    capellacore.CapellaElement, modellingcore.ValueSpecification
):
    def __init__(self):  # pylint: disable=super-init-not-called
        raise NotImplementedError("Not yet implemented")

    @classmethod
    def _parse_xml(
        cls,
        model: m.Model,
        elem: etree._Element,
        lazy_attributes: cabc.MutableSet[tuple[str, str]],
    ) -> te.Self:
        LOGGER.warning("OpaqueExpression not implemented: %s", elem)
        model._has_aliens = True
        for i in elem.iterchildren("bodies"):
            elem.remove(i)
        for i in elem.iterchildren("languages"):
            elem.remove(i)
        return super()._parse_xml(model, elem, lazy_attributes)
