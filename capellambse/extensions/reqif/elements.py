# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

__all__ = [
    "AbstractRequirementsAttribute",
    "AbstractRequirementsRelation",
    "AbstractType",
    "AttributeDefinition",
    "AttributeDefinitionEnumeration",
    "BooleanValueAttribute",
    "DataTypeDefinition",
    "DateValueAttribute",
    "EnumDataTypeDefinition",
    "EnumValue",
    "EnumerationValueAttribute",
    "IntegerValueAttribute",
    "ModuleType",
    "RealValueAttribute",
    "RelationType",
    "RelationsList",
    "ReqIFElement",
    "Requirement",
    "RequirementType",
    "RequirementsFolder",
    "RequirementsIncRelation",
    "RequirementsIntRelation",
    "RequirementsModule",
    "RequirementsOutRelation",
    "RequirementsTypesFolder",
    "StringValueAttribute",
    "XT_FOLDER",
    "XT_INC_RELATION",
    "XT_INT_RELATION",
    "XT_MODULE",
    "XT_MODULE_TYPE",
    "XT_OUT_RELATION",
    "XT_RELATION_TYPE",
    "XT_REQUIREMENT",
    "XT_REQ_ATTRIBUTES",
    "XT_REQ_ATTR_BOOLEANVALUE",
    "XT_REQ_ATTR_DATEVALUE",
    "XT_REQ_ATTR_ENUMVALUE",
    "XT_REQ_ATTR_INTEGERVALUE",
    "XT_REQ_ATTR_REALVALUE",
    "XT_REQ_ATTR_STRINGVALUE",
    "XT_REQ_TYPE",
    "XT_REQ_TYPES",
    "XT_REQ_TYPES_DATA_DEF",
    "XT_REQ_TYPES_F",
    "XT_REQ_TYPE_ATTR_DEF",
    "XT_REQ_TYPE_ATTR_ENUM",
    "XT_REQ_TYPE_ENUM",
    "XT_REQ_TYPE_ENUM_DEF",
    "init",
]

import collections.abc as cabc
import logging
import os
import re
import typing as t

import markupsafe
from lxml import etree

import capellambse.model
import capellambse.model.common as c
from capellambse.loader import xmltools
from capellambse.model import crosslayer

from . import exporter

XT_REQUIREMENT = "Requirements:Requirement"
XT_REQ_ATTR_STRINGVALUE = "Requirements:StringValueAttribute"
XT_REQ_ATTR_REALVALUE = "Requirements:RealValueAttribute"
XT_REQ_ATTR_INTEGERVALUE = "Requirements:IntegerValueAttribute"
XT_REQ_ATTR_DATEVALUE = "Requirements:DateValueAttribute"
XT_REQ_ATTR_BOOLEANVALUE = "Requirements:BooleanValueAttribute"
XT_REQ_ATTR_ENUMVALUE = "Requirements:EnumerationValueAttribute"
XT_REQ_ATTRIBUTES = {
    XT_REQ_ATTR_ENUMVALUE,
    XT_REQ_ATTR_STRINGVALUE,
    XT_REQ_ATTR_REALVALUE,
    XT_REQ_ATTR_INTEGERVALUE,
    XT_REQ_ATTR_DATEVALUE,
    XT_REQ_ATTR_BOOLEANVALUE,
}
XT_INC_RELATION = "CapellaRequirements:CapellaIncomingRelation"
XT_OUT_RELATION = "CapellaRequirements:CapellaOutgoingRelation"
XT_INT_RELATION = "Requirements:InternalRelation"
XT_MODULE = "CapellaRequirements:CapellaModule"
XT_FOLDER = "Requirements:Folder"

XT_REQ_TYPES_F = "CapellaRequirements:CapellaTypesFolder"
XT_REQ_TYPES_DATA_DEF = "Requirements:DataTypeDefinition"
XT_REQ_TYPE = "Requirements:RequirementType"
XT_RELATION_TYPE = "Requirements:RelationType"
XT_MODULE_TYPE = "Requirements:ModuleType"
XT_REQ_TYPE_ENUM = "Requirements:EnumerationDataTypeDefinition"
XT_REQ_TYPE_ATTR_ENUM = "Requirements:EnumValue"
XT_REQ_TYPE_ATTR_DEF = "Requirements:AttributeDefinition"
XT_REQ_TYPE_ENUM_DEF = "Requirements:AttributeDefinitionEnumeration"
XT_REQ_TYPES = {
    XT_REQ_TYPES_F,
    XT_REQ_TYPES_DATA_DEF,
    XT_REQ_TYPE,
    XT_RELATION_TYPE,
    XT_MODULE_TYPE,
    XT_REQ_TYPE_ENUM,
    XT_REQ_TYPE_ATTR_ENUM,
    XT_REQ_TYPE_ATTR_DEF,
    XT_REQ_TYPE_ENUM_DEF,
}
DATE_VALUE_FORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"

logger = logging.getLogger("reqif")


class RequirementsRelationAccessor(
    c.WritableAccessor["AbstractRequirementsRelation"]
):
    """Searches for requirement relations in the architecture layer."""

    # pylint: disable=abstract-method  # Only partially implemented for now

    __slots__ = ("aslist",)

    def __init__(self, *args, **kw) -> None:
        super().__init__(
            *args, **kw, aslist=c.ElementList, single_attr="long_name"
        )

    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:  # pragma: no cover
            return self

        rel_objs = list(
            obj._model._loader.iterchildren_xt(obj._element, XT_INC_RELATION)
        )

        for i in obj._model._loader.iterall_xt(XT_OUT_RELATION):
            if RequirementsOutRelation.from_model(obj._model, i).source == obj:
                rel_objs.append(i)

        for i in obj._model._loader.iterall_xt(XT_INT_RELATION):
            rel = RequirementsIntRelation.from_model(obj._model, i)
            if obj in (rel.source, rel.target):
                rel_objs.append(i)
        return self._make_list(obj, rel_objs)

    def _make_list(self, parent_obj, elements):
        assert self.aslist is not None
        return self.aslist(
            parent_obj._model, elements, c.GenericElement, parent=parent_obj
        )

    def create(
        self,
        elmlist: c.ElementListCouplingMixin,
        /,
        *type_hints: str | None,
        **kw: t.Any,
    ) -> RequirementsIntRelation | RequirementsIncRelation:
        if "target" not in kw:
            raise TypeError("No `target` for new requirement relation")
        cls, xtype = self._find_relation_type(kw["target"])
        parent = elmlist._parent._element
        with elmlist._model._loader.new_uuid(parent) as uuid:
            return cls(
                elmlist._model,
                parent,
                **kw,
                source=elmlist._parent,
                uuid=uuid,
                xtype=xtype,
            )

    def _find_relation_type(
        self, target: c.GenericElement
    ) -> tuple[type[RequirementsIntRelation | RequirementsIncRelation], str]:
        if isinstance(target, Requirement):
            return (
                RequirementsIntRelation,
                XT_INT_RELATION,
            )
        elif isinstance(target, ReqIFElement):
            raise TypeError(
                "Cannot create relations to targets of type"
                f" {type(target).__name__}"
            )
        else:
            return (
                RequirementsIncRelation,
                XT_INC_RELATION,
            )


class ElementRelationAccessor(
    c.WritableAccessor["AbstractRequirementsRelation"]
):
    """Provides access to RequirementsRelations of a GenericElement."""

    # pylint: disable=abstract-method  # Only partially implemented for now

    __slots__ = ("aslist",)

    def __init__(self) -> None:
        super().__init__(aslist=RelationsList, single_attr="long_name")

    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:  # pragma: no cover
            return self

        relations: list[etree._Element] = []
        for relation in obj._model.search(
            XT_INC_RELATION, XT_INT_RELATION, XT_OUT_RELATION
        ):
            if obj in (relation.source, relation.target):
                relations.append(relation._element)
        return self._make_list(obj, relations)

    def _make_list(self, parent_obj, elements):
        assert self.aslist is not None
        return self.aslist(
            parent_obj._model,
            elements,
            None,
            parent=parent_obj,
            source=parent_obj,
        )


class ReqIFElement(c.GenericElement):
    """Attributes shared by all ReqIF elements."""

    identifier = xmltools.AttributeProperty(
        "_element", "ReqIFIdentifier", optional=True
    )
    long_name = xmltools.AttributeProperty(
        "_element", "ReqIFLongName", optional=True
    )
    description: str = xmltools.AttributeProperty(  # type: ignore[assignment]
        "_element", "ReqIFDescription", optional=True
    )
    name = xmltools.AttributeProperty("_element", "ReqIFName", optional=True)
    prefix = xmltools.AttributeProperty(
        "_element", "ReqIFPrefix", optional=True
    )
    type: c.Accessor = property(lambda _: None)  # type: ignore[assignment]

    def _short_repr_(self) -> str:  # pragma: no cover
        mytype = type(self).__name__
        parent = self._element
        if self.xtype in XT_REQ_TYPES:
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


@c.xtype_handler(None, XT_REQ_TYPES_DATA_DEF)
class DataTypeDefinition(ReqIFElement):
    """A data type definition for requirement types."""

    _xmltag = "ownedDefinitionTypes"


@c.xtype_handler(None, XT_REQ_TYPE_ATTR_DEF)
class AttributeDefinition(ReqIFElement):
    """An attribute definition for requirement types."""

    _xmltag = "ownedAttributes"

    data_type = c.AttrProxyAccessor(DataTypeDefinition, "definitionType")


class AbstractRequirementsAttribute(c.GenericElement):
    _xmltag = "ownedAttributes"

    definition = c.AttrProxyAccessor(AttributeDefinition, "definition")

    value: xmltools.AttributeProperty | c.AttrProxyAccessor

    def __repr__(self) -> str:
        return self._short_repr_()

    def _short_repr_(self) -> str:
        mytype = type(self).__name__
        if self.definition is not None:
            return f"<{mytype} {self.definition.long_name!r} ({self.uuid})>"
        default_name = re.sub(r"(?<!^)([A-Z])", r" \1", mytype)
        return f"<{mytype} [{default_name}] ({self.uuid})>"

    def _short_html_(self) -> markupsafe.Markup:
        if self.definition is not None:
            name = markupsafe.Markup.escape(self.definition.long_name)
        else:
            name = markupsafe.Markup.escape("None")
        return markupsafe.Markup(self._wrap_short_html(f" &quot;{name}&quot;"))


class AttributeAccessor(c.DirectProxyAccessor[AbstractRequirementsAttribute]):
    def __init__(self) -> None:
        super().__init__(
            c.GenericElement,  # type: ignore[arg-type]
            XT_REQ_ATTRIBUTES,
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
            return _attr_type_hints[type_]
        except KeyError:
            raise ValueError(f"Invalid type hint given: {type_!r}") from None


class RelationsList(c.ElementList["AbstractRequirementsRelation"]):
    def __init__(
        self,
        model: capellambse.MelodyModel,
        elements: list[etree._Element],
        elemclass: type[t.Any] | None = None,
        *,
        source: c.ModelObject,
    ) -> None:
        del elemclass
        super().__init__(model, elements, AbstractRequirementsRelation)
        self._source = source

    @t.overload
    def __getitem__(self, idx: int | str) -> AbstractRequirementsRelation:
        ...

    @t.overload
    def __getitem__(
        self, idx: slice
    ) -> c.ElementList[AbstractRequirementsRelation]:
        ...

    def __getitem__(self, idx):
        rel = super().__getitem__(idx)
        if isinstance(rel, c.ElementList):
            return rel

        assert isinstance(rel, AbstractRequirementsRelation)
        assert self._source in (rel.source, rel.target)
        if self._source == rel.source:
            return rel.target
        else:
            return rel.source

    def by_relation_type(self, reltype: str) -> RelationsList:
        matches = []
        for elm in self._elements:
            rel_elm = c.GenericElement.from_model(self._model, elm)
            assert isinstance(rel_elm, AbstractRequirementsRelation)
            if rel_elm.type is not None and rel_elm.type.name == reltype:
                matches.append(elm)
        return self._newlist(matches)

    def by_relation_class(
        self, class_: t.Literal["incoming", "outgoing", "internal"]
    ) -> RelationsList:
        relation_types = {
            "incoming": RequirementsIncRelation,
            "outgoing": RequirementsOutRelation,
            "internal": RequirementsIntRelation,
        }
        matches: list[etree._Element] = []
        for elm in self._elements:
            rel_elm = c.GenericElement.from_model(self._model, elm)
            if isinstance(rel_elm, relation_types[class_]):
                matches.append(rel_elm._element)
        return self._newlist(matches)

    def _newlist(self, elements: list[etree._Element]) -> RelationsList:
        listtype = self._newlist_type()
        assert issubclass(listtype, RelationsList)
        return listtype(self._model, elements, source=self._source)


@c.xtype_handler(None, XT_REQ_ATTR_BOOLEANVALUE)
class BooleanValueAttribute(AbstractRequirementsAttribute):
    """A string value attribute."""

    value = xmltools.BooleanAttributeProperty("_element", "value")


@c.xtype_handler(None, XT_REQ_ATTR_DATEVALUE)
class DateValueAttribute(AbstractRequirementsAttribute):
    """A value attribute that stores a date and time."""

    value = xmltools.DatetimeAttributeProperty(
        "_element", "value", format=DATE_VALUE_FORMAT, optional=True
    )


@c.xtype_handler(None, XT_REQ_ATTR_INTEGERVALUE)
class IntegerValueAttribute(AbstractRequirementsAttribute):
    """An integer value attribute."""

    value = xmltools.AttributeProperty(
        "_element", "value", returntype=int, default=0
    )


@c.xtype_handler(None, XT_REQ_ATTR_REALVALUE)
class RealValueAttribute(AbstractRequirementsAttribute):
    """A floating-point number value attribute."""

    value = xmltools.AttributeProperty(
        "_element", "value", returntype=float, default=0.0
    )


@c.xtype_handler(None, XT_REQ_ATTR_STRINGVALUE)
class StringValueAttribute(AbstractRequirementsAttribute):
    """A string value attribute."""

    value = xmltools.AttributeProperty("_element", "value", default="")


@c.xtype_handler(None, XT_REQ_TYPE_ATTR_ENUM)
@c.attr_equal("long_name")
class EnumValue(ReqIFElement):
    """An enumeration value for :class:`EnumDataTypeDefinition`."""

    _xmltag = "specifiedValues"

    def __str__(self) -> str:
        return self.long_name


@c.xtype_handler(None, XT_REQ_TYPE_ENUM)
class EnumDataTypeDefinition(ReqIFElement):
    """An enumeration data type definition for requirement types."""

    _xmltag = "ownedDefinitionTypes"

    values = c.DirectProxyAccessor(
        EnumValue,
        XT_REQ_TYPE_ATTR_ENUM,
        aslist=c.ElementList,
        single_attr="long_name",
    )


@c.xtype_handler(None, XT_REQ_TYPE_ENUM_DEF)
class AttributeDefinitionEnumeration(ReqIFElement):
    """An enumeration attribute definition for requirement types."""

    _xmltag = "ownedAttributes"

    data_type = c.AttrProxyAccessor(EnumDataTypeDefinition, "definitionType")
    multi_valued = xmltools.BooleanAttributeProperty(
        "_element",
        "multiValued",
        __doc__=(
            "Boolean flag for setting multiple enumeration values on"
            " the attribute"
        ),
    )


@c.xtype_handler(None, XT_REQ_ATTR_ENUMVALUE)
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


@c.attr_equal("long_name")
class AbstractType(ReqIFElement):
    owner = c.ParentAccessor(c.GenericElement)
    attribute_definitions = c.DirectProxyAccessor(
        c.GenericElement,
        (XT_REQ_TYPE_ATTR_DEF, XT_REQ_TYPE_ENUM_DEF),
        aslist=c.MixedElementList,
    )


@c.xtype_handler(None, XT_MODULE_TYPE)
class ModuleType(AbstractType):
    """A requirement-module type."""

    _xmltag = "ownedTypes"


@c.xtype_handler(None, XT_RELATION_TYPE)
class RelationType(AbstractType):
    """A requirement-relation type."""

    _xmltag = "ownedTypes"


@c.xtype_handler(None, XT_REQ_TYPE)
class RequirementType(AbstractType):
    """A requirement type."""

    _xmltag = "ownedTypes"


@c.xtype_handler(None, XT_REQUIREMENT)
class Requirement(ReqIFElement):
    """A ReqIF Requirement."""

    _xmltag = "ownedRequirements"

    owner = c.ParentAccessor(c.GenericElement)

    chapter_name = xmltools.AttributeProperty(
        "_element", "ReqIFChapterName", optional=True
    )
    foreign_id = xmltools.AttributeProperty(
        "_element", "ReqIFForeignID", optional=True, returntype=int
    )
    text = xmltools.HTMLAttributeProperty(
        "_element", "ReqIFText", optional=True
    )
    attributes = AttributeAccessor()
    relations = RequirementsRelationAccessor()
    related = ElementRelationAccessor()
    type = c.AttrProxyAccessor(RequirementType, "requirementType")


@c.xtype_handler(None, XT_FOLDER)
class RequirementsFolder(Requirement):
    """A folder that stores Requirements."""

    _xmltag = "ownedRequirements"

    folders: c.Accessor
    requirements = c.DirectProxyAccessor(
        Requirement, XT_REQUIREMENT, aslist=c.ElementList
    )


@c.xtype_handler(None, XT_MODULE)
class RequirementsModule(ReqIFElement):
    """A ReqIF Module that bundles multiple Requirement folders."""

    _xmltag = "ownedExtensions"

    folders = c.DirectProxyAccessor(
        RequirementsFolder, XT_FOLDER, aslist=c.ElementList
    )
    requirements = c.DirectProxyAccessor(
        Requirement, XT_REQUIREMENT, aslist=c.ElementList
    )
    type = c.AttrProxyAccessor(ModuleType, "moduleType")
    attributes = AttributeAccessor()

    def to_reqif(
        self,
        to: str | os.PathLike | t.IO[bytes],
        *,
        metadata: cabc.Mapping[str, t.Any] | None = None,
        pretty: bool = False,
        compress: bool | None = None,
    ) -> None:
        """Export this module as ReqIF XML.

        You can override some auto-generated metadata placed in the header
        section by passing a dictionary as ``metadata``. The following keys
        are supported. Unsupported keys are silently ignored.

        -   ``creation_time``: A ``datetime.datetime`` object that specifies
            this document's creation time. Default to the current time.
        -   ``comment``: Override the ReqIF file's comment. Defaults to a
            text derived from the model and module names.
        -   ``title``: Specify the document title. Defaults to the module's
            ``long_name``.

        Parameters
        ----------
        to
            Where to export to. Can be the name of a file, or a file-like
            object opened in binary mode.
        metadata
            A dictionary with additional metadata (see above).
        pretty
            Format the XML human-readable.
        compress
            Write compressed data (``*.reqifz``). Defaults to ``True``
            if ``target`` is a string or path-like and its name ends in
            ``.reqifz``, otherwise defaults to ``False``.
        """
        exporter.export_module(
            self, to, metadata=metadata, pretty=pretty, compress=compress
        )


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


@c.xtype_handler(None, XT_OUT_RELATION)
class RequirementsOutRelation(AbstractRequirementsRelation):
    """A Relation between an object and a requirement."""

    _xmltag = "ownedExtensions"

    source = c.AttrProxyAccessor(Requirement, "target")
    target = c.AttrProxyAccessor(c.GenericElement, "source")


@c.xtype_handler(None, XT_INC_RELATION)
class RequirementsIncRelation(AbstractRequirementsRelation):
    """A Relation between a requirement and an object."""

    _xmltag = "ownedRelations"


@c.xtype_handler(None, XT_INT_RELATION)
class RequirementsIntRelation(AbstractRequirementsRelation):
    """A Relation between two requirements."""

    _xmltag = "ownedRelations"


@c.xtype_handler(None, XT_REQ_TYPES_F)
class RequirementsTypesFolder(ReqIFElement):
    _xmltag = "ownedExtensions"

    data_type_definitions = c.DirectProxyAccessor(
        c.GenericElement,
        (XT_REQ_TYPES_DATA_DEF, XT_REQ_TYPE_ENUM),
        aslist=c.MixedElementList,
    )
    module_types = c.DirectProxyAccessor(
        ModuleType, XT_MODULE_TYPE, aslist=c.ElementList
    )
    relation_types = c.DirectProxyAccessor(
        RelationType, XT_RELATION_TYPE, aslist=c.ElementList
    )
    requirement_types = c.DirectProxyAccessor(
        RequirementType, XT_REQ_TYPE, aslist=c.ElementList
    )


def init() -> None:
    c.set_accessor(
        RequirementsFolder,
        "folders",
        c.DirectProxyAccessor(
            RequirementsFolder, XT_FOLDER, aslist=c.ElementList
        ),
    )
    c.set_accessor(c.GenericElement, "requirements", ElementRelationAccessor())
    c.set_accessor(
        crosslayer.BaseArchitectureLayer,
        "requirement_modules",
        c.DirectProxyAccessor(
            RequirementsModule, XT_MODULE, aslist=c.ElementList
        ),
    )
    c.set_accessor(
        crosslayer.BaseArchitectureLayer,
        "all_requirements",
        c.DeepProxyAccessor(
            Requirement,
            XT_REQUIREMENT,
            aslist=c.ElementList,
            rootelem=XT_MODULE,
        ),
    )
    c.set_accessor(
        crosslayer.BaseArchitectureLayer,
        "requirement_types_folders",
        c.DirectProxyAccessor(
            RequirementsTypesFolder,
            XT_REQ_TYPES_F,
            aslist=c.ElementList,
        ),
    )
    c.set_accessor(
        RequirementsModule,
        "requirement_types_folders",
        c.DirectProxyAccessor(
            RequirementsTypesFolder,
            XT_REQ_TYPES_F,
            aslist=c.ElementList,
        ),
    )
    c.set_accessor(
        crosslayer.BaseArchitectureLayer,
        "all_requirement_types",
        c.DeepProxyAccessor(
            RequirementType,
            XT_REQ_TYPE,
            aslist=c.ElementList,
            rootelem=XT_REQ_TYPES_F,
        ),
    )
    c.set_accessor(
        crosslayer.BaseArchitectureLayer,
        "all_module_types",
        c.DeepProxyAccessor(
            ModuleType,
            XT_MODULE_TYPE,
            aslist=c.ElementList,
            rootelem=XT_REQ_TYPES_F,
        ),
    )
    c.set_accessor(
        crosslayer.BaseArchitectureLayer,
        "all_relation_types",
        c.DeepProxyAccessor(
            RelationType,
            XT_RELATION_TYPE,
            aslist=c.ElementList,
            rootelem=XT_REQ_TYPES_F,
        ),
    )


_attr_type_hints = {
    "int": (IntegerValueAttribute, XT_REQ_ATTR_INTEGERVALUE),
    "integer": (IntegerValueAttribute, XT_REQ_ATTR_INTEGERVALUE),
    "integervalueattribute": (IntegerValueAttribute, XT_REQ_ATTR_INTEGERVALUE),
    "str": (StringValueAttribute, XT_REQ_ATTR_STRINGVALUE),
    "string": (StringValueAttribute, XT_REQ_ATTR_STRINGVALUE),
    "stringvalueattribute": (StringValueAttribute, XT_REQ_ATTR_STRINGVALUE),
    "float": (RealValueAttribute, XT_REQ_ATTR_REALVALUE),
    "real": (RealValueAttribute, XT_REQ_ATTR_REALVALUE),
    "realvalueattribute": (RealValueAttribute, XT_REQ_ATTR_REALVALUE),
    "date": (DateValueAttribute, XT_REQ_ATTR_DATEVALUE),
    "datevalueattribute": (DateValueAttribute, XT_REQ_ATTR_DATEVALUE),
    "bool": (BooleanValueAttribute, XT_REQ_ATTR_BOOLEANVALUE),
    "boolean": (BooleanValueAttribute, XT_REQ_ATTR_BOOLEANVALUE),
    "booleanvalueattribute": (BooleanValueAttribute, XT_REQ_ATTR_BOOLEANVALUE),
    "enum": (EnumerationValueAttribute, XT_REQ_ATTR_ENUMVALUE),
    "enumeration": (EnumerationValueAttribute, XT_REQ_ATTR_ENUMVALUE),
    "enumerationvalueattribute": (
        EnumerationValueAttribute,
        XT_REQ_ATTR_ENUMVALUE,
    ),
}
