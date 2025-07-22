# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""The 'Requirements' namespace."""

from __future__ import annotations

__all__ = [
    "AbstractRelation",
    "AbstractType",
    "Attribute",
    "AttributeDefinition",
    "AttributeDefinitionEnumeration",
    "AttributeOwner",
    "BooleanValueAttribute",
    "DataTypeDefinition",
    "DateValueAttribute",
    "EnumValue",
    "EnumerationDataTypeDefinition",
    "EnumerationValueAttribute",
    "Folder",
    "IdentifiableElement",
    "IntegerValueAttribute",
    "InternalRelation",
    "Module",
    "ModuleType",
    "RealValueAttribute",
    "RelationType",
    "ReqIFElement",
    "Requirement",
    "RequirementType",
    "SharedDirectAttributes",
    "StringValueAttribute",
    "TypesFolder",
]

import re
import sys
import typing as t

from lxml import etree

import capellambse.model as m
from capellambse import helpers

if t.TYPE_CHECKING:
    import markupsafe

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

NS = m.Namespace(
    "http://www.polarsys.org/kitalpha/requirements",
    "Requirements",
    "org.polarsys.kitalpha.vp.requirements",
)


class IdentifiableElement(m.ModelElement, abstract=True):
    pass


class ReqIFElement(IdentifiableElement, abstract=True):
    identifier = m.StringPOD("ReqIFIdentifier")
    description = m.StringPOD("ReqIFDescription")
    long_name = m.StringPOD("ReqIFLongName")

    def _short_repr_(self) -> str:  # pragma: no cover
        name = (
            self._element.get("ReqIFName")
            or self._element.get("ReqIFChapterName")
            or self._element.get("ReqIFLongName")
            or ""
        )
        return f"<{type(self).__name__} {name!r} ({self.uuid})>"

    def _short_html_(self) -> markupsafe.Markup:
        name = self.long_name
        if isinstance(self, SharedDirectAttributes):
            name = self.name or name
        return helpers.make_short_html(type(self).__name__, self.uuid, name)


class AbstractRelation(ReqIFElement, abstract=True):
    _required_attrs = frozenset({"source", "target"})

    type = m.Single["RelationType"](
        m.Association((NS, "RelationType"), "relationType")
    )
    relation_type_proxy = m.StringPOD("relationTypeProxy")

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


class InternalRelation(AbstractRelation):
    _xmltag = "ownedRelations"

    def __init__(
        self,
        model: m.MelodyModel,
        parent: etree._Element,
        xmltag: str | None = None,
        /,
        **kw: t.Any,
    ) -> None:
        kw.setdefault("source", m.wrap_xml(model, parent))
        super().__init__(model, parent, xmltag, **kw)

    source = m.Single["Requirement"](
        m.Association((NS, "Requirement"), "source")
    )
    target = m.Single["Requirement"](
        m.Association((NS, "Requirement"), "target")
    )


class Attribute(IdentifiableElement, abstract=True):
    _xmltag = "ownedAttributes"

    definition = m.Single["AttributeDefinition"](
        m.Association((NS, "AttributeDefinition"), "definition")
    )
    definition_proxy = m.StringPOD("definitionProxy")

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


class StringValueAttribute(Attribute):
    value = m.StringPOD("value")


class IntegerValueAttribute(Attribute):
    value = m.IntPOD("value")


class BooleanValueAttribute(Attribute):
    value = m.BoolPOD("value")


class RealValueAttribute(Attribute):
    value = m.FloatPOD("value")


class DateValueAttribute(Attribute):
    value = m.DatetimePOD("value")

    def _repr_value(self) -> str:
        if self.value is None:
            return "None"
        return self.value.isoformat()


class SharedDirectAttributes(m.ModelElement, abstract=True):
    name = m.StringPOD("ReqIFName")
    prefix = m.StringPOD("ReqIFPrefix")


class AttributeOwner(ReqIFElement, abstract=True):
    attributes = m.Containment["Attribute"](
        "ownedAttributes",
        (NS, "Attribute"),
        type_hint_map={
            "int": (NS, "IntegerValueAttribute"),
            "integer": (NS, "IntegerValueAttribute"),
            "integervalueattribute": (NS, "IntegerValueAttribute"),
            "str": (NS, "StringValueAttribute"),
            "string": (NS, "StringValueAttribute"),
            "stringvalueattribute": (NS, "StringValueAttribute"),
            "float": (NS, "RealValueAttribute"),
            "real": (NS, "RealValueAttribute"),
            "realvalueattribute": (NS, "RealValueAttribute"),
            "date": (NS, "DateValueAttribute"),
            "datetime": (NS, "DateValueAttribute"),
            "datevalueattribute": (NS, "DateValueAttribute"),
            "bool": (NS, "BooleanValueAttribute"),
            "boolean": (NS, "BooleanValueAttribute"),
            "booleanvalueattribute": (NS, "BooleanValueAttribute"),
            "enum": (NS, "EnumerationValueAttribute"),
            "enumeration": (NS, "EnumerationValueAttribute"),
            "enumerationvalueattribute": (NS, "EnumerationValueAttribute"),
        },
    )


class Requirement(AttributeOwner, SharedDirectAttributes):
    _xmltag = "ownedRequirements"

    type = m.Single["RequirementType"](
        m.Association((NS, "RequirementType"), "requirementType")
    )
    owned_relations = m.Containment["AbstractRelation"](
        "ownedRelations", (NS, "AbstractRelation")
    )
    chapter_name = m.StringPOD("ReqIFChapterName")
    foreign_id = m.IntPOD("ReqIFForeignID")
    text = m.HTMLStringPOD("ReqIFText")
    requirement_type_proxy = m.StringPOD("requirementTypeProxy")

    # TODO migrate these to '@property' when removing deprecated features
    relations: m.Accessor[m.ElementList[AbstractRelation]]
    related: m.Accessor[m.ElementList[m.ModelElement]]

    if not t.TYPE_CHECKING:
        owner = m.DeprecatedAccessor("parent")


class Folder(Requirement):
    _xmltag = "ownedRequirements"

    requirements = m.Containment["Requirement"](
        "ownedRequirements", (NS, "Requirement")
    )

    @property
    @deprecated(
        (
            "Folder.folders is deprecated,"
            " use 'requirements.by_class(Folder)' instead"
        ),
        category=FutureWarning,
    )
    def folders(self) -> m.ElementList[Folder]:
        return self.requirements.by_class(Folder)


class Module(AttributeOwner, SharedDirectAttributes):
    type = m.Single["ModuleType"](
        m.Association((NS, "ModuleType"), "moduleType")
    )
    requirements = m.Containment["Requirement"](
        "ownedRequirements", (NS, "Requirement")
    )


class TypesFolder(ReqIFElement):
    definition_types = m.Containment["DataTypeDefinition"](
        "ownedDefinitionTypes", (NS, "DataTypeDefinition")
    )
    types = m.Containment["AbstractType"]("ownedTypes", (NS, "AbstractType"))


class AbstractType(ReqIFElement, abstract=True, eq="long_name"):
    _xmltag = "ownedTypes"

    attributes = m.Containment["AttributeDefinition"](
        "ownedAttributes", (NS, "AttributeDefinition")
    )

    if not t.TYPE_CHECKING:
        attribute_definitions = m.DeprecatedAccessor("attributes")
        owner = m.DeprecatedAccessor("parent")


class ModuleType(AbstractType):
    pass


class RequirementType(AbstractType):
    pass


class RelationType(AbstractType):
    pass


class DataTypeDefinition(ReqIFElement):
    _xmltag = "ownedDefinitionTypes"


class AttributeDefinition(ReqIFElement):
    _xmltag = "ownedAttributes"

    definition_type = m.Single["DataTypeDefinition"](
        m.Association((NS, "DataTypeDefinition"), "definitionType")
    )
    default_value = m.Single["Attribute"](
        m.Containment("defaultValue", (NS, "Attribute"))
    )

    if not t.TYPE_CHECKING:
        data_type = m.DeprecatedAccessor("definition_type")


class AttributeDefinitionEnumeration(AttributeDefinition):
    is_multi_valued = m.BoolPOD("multiValued")

    @property
    @deprecated(
        (
            "AttributeDefinitionEnumeration.multi_valued is deprecated,"
            " use 'is_multi_valued' instead"
        ),
        category=FutureWarning,
    )
    def multi_valued(self) -> bool:
        return self.is_multi_valued

    @multi_valued.setter
    @deprecated(
        (
            "AttributeDefinitionEnumeration.multi_valued is deprecated,"
            " use 'is_multi_valued' instead"
        ),
        category=FutureWarning,
    )
    def multi_valued(self, multi_valued: bool) -> None:
        self.is_multi_valued = multi_valued


class EnumerationValueAttribute(Attribute):
    definition = m.Single["AttributeDefinitionEnumeration"](
        m.Association((NS, "AttributeDefinitionEnumeration"), None)
    )
    values = m.Association["EnumValue"]((NS, "EnumValue"), "values")

    @property
    @deprecated(
        "EnumerationValueAttribute.value is deprecated, use 'values' instead",
        category=FutureWarning,
    )
    def value(self):
        vals = self.values
        if len(vals) > 1:
            raise TypeError("Multi-value enumeration, use `.values` instead")
        if len(vals) == 1:
            return vals[0]
        return None

    def _repr_value(self) -> str:
        return repr([i.long_name for i in self.values])


class EnumerationDataTypeDefinition(DataTypeDefinition):
    values = m.Containment["EnumValue"](
        "specifiedValues", (NS, "EnumValue"), single_attr="long_name"
    )


class EnumValue(ReqIFElement, eq="long_name"):
    _xmltag = "specifiedValues"

    def __str__(self) -> str:
        return self.long_name
