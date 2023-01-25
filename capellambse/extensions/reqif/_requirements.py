# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
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

import markupsafe

import capellambse.model.common as c

c.XTYPE_ANCHORS[__name__] = "Requirements"


class ReqIFElement(c.GenericElement):
    """Attributes shared by all ReqIF elements."""

    identifier = c.AttributeProperty("ReqIFIdentifier", optional=True)
    long_name = c.AttributeProperty("ReqIFLongName", optional=True)
    description: str = c.AttributeProperty(  # type: ignore[assignment]
        "ReqIFDescription", optional=True
    )
    name = c.AttributeProperty("ReqIFName", optional=True)
    prefix = c.AttributeProperty("ReqIFPrefix", optional=True)
    type: c.Accessor = property(lambda _: None)  # type: ignore[assignment]

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
            return f'<{mytype} {parent.get("ReqIFLongName")!r} ({self.uuid})>'

        name = (
            parent.get("ReqIFName")
            or parent.get("ReqIFChapterName")
            or parent.get("ReqIFLongName")
            or ""
        )
        return f"<{mytype} {name!r} ({self.uuid})>"

    def _short_html_(self) -> markupsafe.Markup:
        name = markupsafe.Markup.escape(self.name or self.long_name)
        return markupsafe.Markup(self._wrap_short_html(f" &quot;{name}&quot;"))


@c.xtype_handler(None)
class DataTypeDefinition(ReqIFElement):
    """A data type definition for requirement types."""

    _xmltag = "ownedDefinitionTypes"


@c.xtype_handler(None)
class AttributeDefinition(ReqIFElement):
    """An attribute definition for requirement types."""

    _xmltag = "ownedAttributes"

    data_type = c.AttrProxyAccessor(DataTypeDefinition, "definitionType")


class AbstractRequirementsAttribute(c.GenericElement):
    _xmltag = "ownedAttributes"

    definition = c.AttrProxyAccessor(AttributeDefinition, "definition")

    value: c.AttributeProperty | c.AttrProxyAccessor

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
            name = markupsafe.Markup.escape(self.definition.long_name)
        else:
            name = markupsafe.Markup.escape("None")
        return markupsafe.Markup(self._wrap_short_html(f" &quot;{name}&quot;"))

    def _repr_value(self) -> str:
        return repr(self.value)


class AttributeAccessor(c.DirectProxyAccessor[AbstractRequirementsAttribute]):
    def __init__(self) -> None:
        super().__init__(
            c.GenericElement,  # type: ignore[arg-type]
            (
                BooleanValueAttribute,
                DateValueAttribute,
                EnumerationValueAttribute,
                IntegerValueAttribute,
                RealValueAttribute,
                StringValueAttribute,
            ),
            aslist=c.MixedElementList,
            list_extra_args={
                "mapkey": "definition.long_name",
                "mapvalue": "value",
            },
        )

    def _match_xtype(  # type: ignore[override]
        self, type_: str
    ) -> tuple[type, str]:
        type_ = type_.lower()
        try:
            cls = _attr_type_hints[type_]
            return cls, c.build_xtype(cls)
        except KeyError:
            raise ValueError(f"Invalid type hint given: {type_!r}") from None


@c.xtype_handler(None)
class BooleanValueAttribute(AbstractRequirementsAttribute):
    """A string value attribute."""

    value = c.BooleanAttributeProperty("value")


@c.xtype_handler(None)
class DateValueAttribute(AbstractRequirementsAttribute):
    """A value attribute that stores a date and time."""

    value = c.DatetimeAttributeProperty("value", optional=True)

    def _repr_value(self) -> str:
        if self.value is None:
            return "None"
        return self.value.isoformat()


@c.xtype_handler(None)
class IntegerValueAttribute(AbstractRequirementsAttribute):
    """An integer value attribute."""

    value = c.AttributeProperty("value", returntype=int, default=0)


@c.xtype_handler(None)
class RealValueAttribute(AbstractRequirementsAttribute):
    """A floating-point number value attribute."""

    value = c.AttributeProperty("value", returntype=float, default=0.0)


@c.xtype_handler(None)
class StringValueAttribute(AbstractRequirementsAttribute):
    """A string value attribute."""

    value = c.AttributeProperty("value", default="")


@c.xtype_handler(None)
@c.attr_equal("long_name")
class EnumValue(ReqIFElement):
    """An enumeration value for :class:`EnumDataTypeDefinition`."""

    _xmltag = "specifiedValues"

    def __str__(self) -> str:
        return self.long_name


@c.xtype_handler(None)
class EnumerationDataTypeDefinition(ReqIFElement):
    """An enumeration data type definition for requirement types."""

    _xmltag = "ownedDefinitionTypes"

    values = c.DirectProxyAccessor(
        EnumValue, aslist=c.ElementList, single_attr="long_name"
    )


@c.xtype_handler(None)
class AttributeDefinitionEnumeration(ReqIFElement):
    """An enumeration attribute definition for requirement types."""

    _xmltag = "ownedAttributes"

    data_type = c.AttrProxyAccessor(
        EnumerationDataTypeDefinition, "definitionType"
    )
    multi_valued = c.BooleanAttributeProperty(
        "multiValued",
        __doc__=(
            "Boolean flag for setting multiple enumeration values on"
            " the attribute"
        ),
    )


@c.xtype_handler(None)
class EnumerationValueAttribute(AbstractRequirementsAttribute):
    """An enumeration attribute."""

    definition = c.AttrProxyAccessor(
        AttributeDefinitionEnumeration, "definition"  # type: ignore[arg-type]
    )
    values = c.AttrProxyAccessor(EnumValue, "values", aslist=c.ElementList)

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


@c.attr_equal("long_name")
class AbstractType(ReqIFElement):
    owner = c.ParentAccessor(c.GenericElement)
    attribute_definitions = c.DirectProxyAccessor(
        c.GenericElement,
        (AttributeDefinition, AttributeDefinitionEnumeration),
        aslist=c.MixedElementList,
    )


@c.xtype_handler(None)
class ModuleType(AbstractType):
    """A requirement-module type."""

    _xmltag = "ownedTypes"


@c.xtype_handler(None)
class RelationType(AbstractType):
    """A requirement-relation type."""

    _xmltag = "ownedTypes"


@c.xtype_handler(None)
class RequirementType(AbstractType):
    """A requirement type."""

    _xmltag = "ownedTypes"


@c.xtype_handler(None)
class Requirement(ReqIFElement):
    """A ReqIF Requirement."""

    _xmltag = "ownedRequirements"

    owner = c.ParentAccessor(c.GenericElement)

    chapter_name = c.AttributeProperty("ReqIFChapterName", optional=True)
    foreign_id = c.AttributeProperty(
        "ReqIFForeignID", optional=True, returntype=int
    )
    text = c.HTMLAttributeProperty("ReqIFText", optional=True)
    attributes = AttributeAccessor()
    type = c.AttrProxyAccessor(RequirementType, "requirementType")

    relations: c.Accessor[AbstractRequirementsRelation]
    related: c.Accessor[c.GenericElement]


@c.xtype_handler(None)
class Folder(Requirement):
    """A folder that stores Requirements."""

    _xmltag = "ownedRequirements"

    folders: c.Accessor
    requirements = c.DirectProxyAccessor(Requirement, aslist=c.ElementList)


class AbstractRequirementsRelation(ReqIFElement):
    _required_attrs = frozenset({"source", "target"})

    type = c.AttrProxyAccessor(RelationType, "relationType")
    source = c.AttrProxyAccessor(Requirement, "source")
    target = c.AttrProxyAccessor(c.GenericElement, "target")

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


@c.xtype_handler(None)
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
