# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""The 'Requirements' namespace."""

from __future__ import annotations

__all__ = [
    "AbstractRequirementsAttribute",
    "AbstractRequirementsRelation",
    "AbstractType",
    "AttributeAccessor",
    "AttributeDefinition",
    "AttributeDefinitionEnumeration",
    "BooleanValueAttribute",
    "DataTypeDefinition",
    "DateValueAttribute",
    "EnumValue",
    "EnumerationDataTypeDefinition",
    "EnumerationValueAttribute",
    "Folder",
    "IntegerValueAttribute",
    "InternalRelation",
    "ModuleType",
    "RealValueAttribute",
    "RelationType",
    "ReqIFElement",
    "Requirement",
    "RequirementType",
    "StringValueAttribute",
]

import re
import typing as t

import capellambse.model as m
from capellambse import helpers

if t.TYPE_CHECKING:
    import markupsafe

NS = m.Namespace(
    "http://www.polarsys.org/kitalpha/requirements",
    "Requirements",
    "org.polarsys.kitalpha.vp.requirements",
)


class ReqIFElement(m.ModelElement):
    """Attributes shared by all ReqIF elements."""

    identifier = m.StringPOD("ReqIFIdentifier")
    long_name = m.StringPOD("ReqIFLongName")
    description: str = m.StringPOD("ReqIFDescription")  # type: ignore[assignment]
    name = m.StringPOD("ReqIFName")
    prefix = m.StringPOD("ReqIFPrefix")
    type: m.Accessor = property(lambda _: None)  # type: ignore[assignment]

    def _short_repr_(self) -> str:  # pragma: no cover
        mytype = type(self).__name__
        parent = self._element
        if self.xtype in {  # FIXME remove this shit
            "CapellaRequirements:CapellaTypesFolder",
            "Requirements:DataTypeDefinition",
            "Requirements:RequirementType",
            "Requirements:RelationType",
            "Requirements:ModuleType",
            "Requirements:EnumerationDataTypeDefinition",
            "Requirements:EnumValue",
            "Requirements:AttributeDefinition",
            "Requirements:AttributeDefinitionEnumeration",
        }:
            return f"<{mytype} {parent.get('ReqIFLongName')!r} ({self.uuid})>"

        name = (
            parent.get("ReqIFName")
            or parent.get("ReqIFChapterName")
            or parent.get("ReqIFLongName")
            or ""
        )
        return f"<{mytype} {name!r} ({self.uuid})>"

    def _short_html_(self) -> markupsafe.Markup:
        name = self.name or self.long_name
        return helpers.make_short_html(type(self).__name__, self.uuid, name)


class DataTypeDefinition(ReqIFElement):
    """A data type definition for requirement types."""

    _xmltag = "ownedDefinitionTypes"


class AttributeDefinition(ReqIFElement):
    """An attribute definition for requirement types."""

    _xmltag = "ownedAttributes"

    data_type = m.Single(m.Association(DataTypeDefinition, "definitionType"))


class AbstractRequirementsAttribute(m.ModelElement, abstract=True):
    _xmltag = "ownedAttributes"

    definition = m.Single(m.Association(AttributeDefinition, "definition"))

    value: t.Any

    def __repr__(self) -> str:
        return self._short_repr_()

    def _short_repr_(self) -> str:
        mytype = type(self).__name__
        if self.definition is not None:
            defname = self.definition.long_name
        else:
            defname = re.sub(r"(?<!^)([A-Z])", r" \1", mytype)
        return f"<{mytype} [{defname}] {self._repr_value()} ({self.uuid})>"

    def _short_html_(self) -> markupsafe.Markup:
        if self.definition is not None:
            name = self.definition.long_name
        else:
            name = "None"
        return helpers.make_short_html(type(self).__name__, self.uuid, name)

    def _repr_value(self) -> str:
        return repr(self.value)


class AttributeAccessor(m.DirectProxyAccessor[AbstractRequirementsAttribute]):
    def __init__(self) -> None:
        super().__init__(
            m.ModelElement,  # type: ignore[arg-type]
            (
                BooleanValueAttribute,
                DateValueAttribute,
                EnumerationValueAttribute,
                IntegerValueAttribute,
                RealValueAttribute,
                StringValueAttribute,
            ),
            aslist=m.MixedElementList,
            mapkey="definition.long_name",
            mapvalue="value",
        )

    def _match_xtype(
        self, type_: str, /
    ) -> tuple[type[AbstractRequirementsAttribute], str]:
        type_ = type_.lower()
        try:
            cls = _attr_type_hints[type_]
            return cls, m.build_xtype(cls)
        except KeyError:
            raise ValueError(f"Invalid type hint given: {type_!r}") from None


class BooleanValueAttribute(AbstractRequirementsAttribute):
    """A string value attribute."""

    value = m.BoolPOD("value")


class DateValueAttribute(AbstractRequirementsAttribute):
    """A value attribute that stores a date and time."""

    value = m.DatetimePOD("value")

    def _repr_value(self) -> str:
        if self.value is None:
            return "None"
        return self.value.isoformat()


class IntegerValueAttribute(AbstractRequirementsAttribute):
    """An integer value attribute."""

    value = m.IntPOD("value")


class RealValueAttribute(AbstractRequirementsAttribute):
    """A floating-point number value attribute."""

    value = m.FloatPOD("value")


class StringValueAttribute(AbstractRequirementsAttribute):
    """A string value attribute."""

    value = m.StringPOD("value")


class EnumValue(ReqIFElement, eq="long_name"):
    """An enumeration value for :class:`.EnumerationDataTypeDefinition`."""

    _xmltag = "specifiedValues"

    def __str__(self) -> str:
        return self.long_name


class EnumerationDataTypeDefinition(DataTypeDefinition):
    """An enumeration data type definition for requirement types."""

    values = m.DirectProxyAccessor(
        EnumValue, aslist=m.ElementList, single_attr="long_name"
    )


class AttributeDefinitionEnumeration(AttributeDefinition):
    """An enumeration attribute definition for requirement types."""

    data_type = m.Single(
        m.Association(EnumerationDataTypeDefinition, "definitionType")
    )
    multi_valued = m.BoolPOD("multiValued")
    """Whether to allow setting multiple values on this attribute."""


class EnumerationValueAttribute(AbstractRequirementsAttribute):
    """An enumeration attribute."""

    definition = m.Single(
        m.Association(AttributeDefinitionEnumeration, "definition")
    )
    values = m.Association(EnumValue, "values", aslist=m.ElementList)

    @property
    def value(self):
        vals = self.values
        if len(vals) > 1:
            raise TypeError("Multi-value enumeration, use `.values` instead")
        if len(vals) == 1:
            return vals[0]
        return None  # TODO return a default value?

    def _repr_value(self) -> str:
        return repr([i.long_name for i in self.values])


class AbstractType(ReqIFElement, eq="long_name"):
    owner = m.ParentAccessor()
    attribute_definitions = m.DirectProxyAccessor(
        m.ModelElement,
        (AttributeDefinition, AttributeDefinitionEnumeration),
        aslist=m.MixedElementList,
    )


class ModuleType(AbstractType):
    """A requirement-module type."""

    _xmltag = "ownedTypes"


class RelationType(AbstractType):
    """A requirement-relation type."""

    _xmltag = "ownedTypes"


class RequirementType(AbstractType):
    """A requirement type."""

    _xmltag = "ownedTypes"


class Requirement(ReqIFElement):
    """A ReqIF Requirement."""

    _xmltag = "ownedRequirements"

    owner = m.ParentAccessor()

    chapter_name = m.StringPOD("ReqIFChapterName")
    foreign_id = m.IntPOD("ReqIFForeignID")
    text = m.HTMLStringPOD("ReqIFText")
    attributes = AttributeAccessor()
    type = m.Single(m.Association(RequirementType, "requirementType"))

    relations: m.Accessor[m.ElementList[AbstractRequirementsRelation]]
    related: m.Accessor[m.ElementList[AbstractRequirementsRelation]]


class Folder(Requirement):
    """A folder that stores Requirements."""

    _xmltag = "ownedRequirements"

    folders: m.Accessor
    requirements = m.DirectProxyAccessor(Requirement, aslist=m.ElementList)


class AbstractRequirementsRelation(ReqIFElement):
    _required_attrs = frozenset({"source", "target"})

    type = m.Single(m.Association(RelationType, "relationType"))
    source = m.Single(m.Association(Requirement, "source"))
    target = m.Single(m.Association(m.ModelElement, "target"))

    def _short_repr_(self) -> str:
        direction = ""
        if self.source is not None:
            direction += f" from {self.source._short_repr_()}"
        if self.target is not None:
            direction += f" to {self.target._short_repr_()}"
        return (
            f"<{type(self).__name__} {self.long_name!r}{direction} "
            f"({self.uuid})>"
        )


class InternalRelation(AbstractRequirementsRelation):
    """A Relation between two requirements."""

    _xmltag = "ownedRelations"


_attr_type_hints = {
    "int": IntegerValueAttribute,
    "integer": IntegerValueAttribute,
    "integervalueattribute": IntegerValueAttribute,
    "str": StringValueAttribute,
    "string": StringValueAttribute,
    "stringvalueattribute": StringValueAttribute,
    "float": RealValueAttribute,
    "real": RealValueAttribute,
    "realvalueattribute": RealValueAttribute,
    "date": DateValueAttribute,
    "datetime": DateValueAttribute,
    "datevalueattribute": DateValueAttribute,
    "bool": BooleanValueAttribute,
    "boolean": BooleanValueAttribute,
    "booleanvalueattribute": BooleanValueAttribute,
    "enum": EnumerationValueAttribute,
    "enumeration": EnumerationValueAttribute,
    "enumerationvalueattribute": EnumerationValueAttribute,
}
