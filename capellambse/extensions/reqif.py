# Copyright 2021 DB Netz AG
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tools for handling ReqIF Requirements.

.. diagram:: [CDB] Requirements ORM
"""
from __future__ import annotations

import itertools
import logging
import typing as t

from lxml import etree

import capellambse.model
import capellambse.model.common as c
from capellambse import helpers
from capellambse.loader import xmltools
from capellambse.model import crosslayer

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

logger = logging.getLogger("reqif")
attr_type_map = {
    XT_REQ_ATTR_STRINGVALUE: str,
    XT_REQ_ATTR_REALVALUE: float,
    XT_REQ_ATTR_INTEGERVALUE: int,
    XT_REQ_ATTR_DATEVALUE: str,
    XT_REQ_ATTR_BOOLEANVALUE: bool,
}
undefined_value = "undefined"


class ElementRelationAccessor(c.Accessor["AbstractRequirementsRelation"]):
    """Provides access to RequirementsRelations of a GenericElement."""

    __slots__ = ()

    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:  # pragma: no cover
            return self

        loader = obj._model._loader
        layertypes = list(filter(None, c.XTYPE_HANDLERS.keys()))
        assert layertypes
        syseng = next(
            loader.iterchildren_xt(
                obj._model._element, capellambse.model.XT_SYSENG
            ),
            None,
        )
        layers = loader.iterchildren_xt(syseng, *layertypes)
        modules = itertools.chain.from_iterable(
            loader.iterchildren_xt(i, XT_MODULE) for i in layers
        )
        inc_int_relations = itertools.chain.from_iterable(
            loader.iterdescendants_xt(i, XT_INC_RELATION, XT_INT_RELATION)
            for i in modules
        )
        out_relations = loader.iterchildren_xt(obj._element, XT_OUT_RELATION)

        def targetof(i: etree._Element) -> c.GenericElement:
            rel = c.GenericElement.from_model(obj._model, i)
            assert isinstance(
                rel,
                (
                    RequirementsOutRelation,
                    RequirementsIncRelation,
                    RequirementsIntRelation,
                ),
            )
            return rel.target

        return RelationsList(
            obj._model,
            list(
                itertools.chain(
                    (i for i in inc_int_relations if targetof(i) == obj),
                    (i for i in out_relations if targetof(i) == obj),
                )
            ),
            None,
            parent=None,
            side="source",
        )


class ReqIFElement(c.GenericElement):
    """Attributes shared by all ReqIF elements."""

    identifier = xmltools.AttributeProperty(
        "_element", "ReqIFIdentifier", optional=True
    )
    long_name = xmltools.AttributeProperty(
        "_element", "ReqIFLongName", optional=True
    )
    description = xmltools.AttributeProperty(
        "_element", "ReqIFDescription", optional=True
    )
    name = xmltools.AttributeProperty("_element", "ReqIFName", optional=True)
    prefix = xmltools.AttributeProperty(
        "_element", "ReqIFPrefix", optional=True
    )
    type = property(lambda _: None)

    def __repr__(self) -> str:  # pragma: no cover
        mytype = type(self).__name__
        path = []
        parent = self._element
        if isinstance(
            self,
            (
                RequirementsOutRelation,
                RequirementsIncRelation,
                RequirementsIntRelation,
            ),
        ):
            return (
                f"<{mytype} from {self.source!r} to {self.target!r} "
                f"({self.uuid})>"
            )
        elif self.xtype in XT_REQ_TYPES:
            return f'<{mytype} {parent.get("ReqIFLongName")!r} ({self.uuid})>'
        while parent is not None:
            path.append(
                parent.get("ReqIFText")
                or parent.get("ReqIFName")
                or parent.get("ReqIFChapterName")
                or parent.get("ReqIFLongName")
                or "..."
            )
            if helpers.xtype_of(parent) == XT_MODULE:
                break
            parent = parent.getparent()

        return f'<{mytype} {"/".join(reversed(path))!r} ({self.uuid})>'

    @property
    def name(self) -> str:
        if (name := self._element.get("ReqIFName")) is None:
            return self.long_name
        return name


@c.xtype_handler(None, XT_REQ_TYPES_DATA_DEF)
class DataTypeDefinition(ReqIFElement):
    """A data type definition for requirement types"""

    _xmltag = "ownedDefinitionTypes"


@c.xtype_handler(None, XT_REQ_TYPE_ATTR_DEF)
class AttributeDefinition(ReqIFElement):
    """An attribute definition for requirement types"""

    _xmltag = "ownedAttributes"

    data_type = c.AttrProxyAccessor(DataTypeDefinition, "definitionType")


class AbstractRequirementsAttribute(c.GenericElement):
    _xmltag = "ownedAttributes"

    definition = c.AttrProxyAccessor(AttributeDefinition, "definition")

    def __repr__(self) -> str:
        mytype = self.xtype.rsplit(":", maxsplit=1)[-1]
        try:
            name = self.definition.long_name
        except AttributeError:
            logger.warning(
                "This requirement(%s) attribute has no definition.",
                self._element.getparent().get("id"),
            )
            name = undefined_value
        return f"<{mytype} [{name}] ({self.uuid})>"


class AttributeAccessor(c.PhysicalAccessor):
    def __init__(self) -> None:
        ...

    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:  # pragma: no cover
            return self

        elm: etree._Element = obj._element
        xmltag = AbstractRequirementsAttribute._xmltag
        attrs = [attr for attr in elm.iterchildren(xmltag)]
        enums = elm.xpath(
            f"./{xmltag}[@xsi:type='{XT_REQ_ATTR_ENUMVALUE}']",
            namespaces=capellambse.NAMESPACES,
        )

        if not enums:
            return c.ElementList(
                obj._model, attrs, RequirementsAttribute, parent=elm
            )

        return c.MixedElementList(
            obj._model,
            attrs,
            (RequirementsAttribute, EnumerationValueAttribute),
            parent=elm,
        )


class RelationsList(c.ElementList["AbstractRequirementsRelation"]):
    def __init__(
        self,
        model: capellambse.MelodyModel,
        elements: t.List[etree._Element],
        elemclass: t.Type[t.Any] = None,
        *,
        parent: t.Optional[etree._Element],
        side: str = "source",
    ) -> None:
        del elemclass
        assert side in {"source", "target"}
        super().__init__(model, elements, c.GenericElement, parent=parent)
        self._side = side

    def __getitem__(self, idx: int | slice) -> c.GenericElement:
        if isinstance(idx, slice):
            return self._newlist(self._elements[idx])
        return getattr(
            c.GenericElement.from_model(self._model, self._elements[idx]),
            self._side,
        )

    def by_relation_type(self, reltype: str) -> RelationsList:
        matches = []
        for elm in self._elements:
            rel_elm = c.GenericElement.from_model(self._model, elm)
            assert isinstance(
                rel_elm,
                (
                    RequirementsIncRelation,
                    RequirementsOutRelation,
                    RequirementsIntRelation,
                ),
            )
            if rel_elm.type is not None and rel_elm.type.name == reltype:
                matches.append(elm)
        return type(self)(
            self._model, matches, None, side=self._side, parent=None
        )

    @property
    def incoming(self) -> RelationsList:
        return self._filter_by_relcls(RequirementsIncRelation)

    @property
    def outgoing(self) -> RelationsList:
        return self._filter_by_relcls(RequirementsOutRelation)

    def _newlist(self, elements):
        return type(self)(
            self._model, elements, None, side=self._side, parent=None
        )

    def _filter_by_relcls(
        self,
        relcls: t.Type[
            RequirementsIncRelation
            | RequirementsOutRelation
            | RequirementsIntRelation
        ],
    ):
        matches = [
            rel_elm._element
            for elm in self._elements
            if isinstance(
                rel_elm := c.GenericElement.from_model(self._model, elm),
                relcls,
            )
        ]
        return type(self)(
            self._model, matches, None, side=self._side, parent=None
        )


@c.xtype_handler(None, *(XT_REQ_ATTRIBUTES - {XT_REQ_ATTR_ENUMVALUE}))
class RequirementsAttribute(AbstractRequirementsAttribute):
    """Handles attributes on Requirements."""

    definition = c.AttrProxyAccessor(AttributeDefinition, "definition")

    @property
    def value(self) -> int | float | str | bool:
        if not (value := self._element.get("value", "")):
            logger.warning("This requirement(%s) attribute has no value set.")
            return undefined_value
        return attr_type_map[self.xtype](value)


@c.xtype_handler(None, XT_REQ_TYPE_ENUM)
class EnumDataTypeDefinition(ReqIFElement):
    """An enumeration data type definition for requirement types"""

    _xmltag = "ownedDefinitionTypes"

    enum_values = c.ProxyAccessor(
        None, XT_REQ_TYPE_ENUM_DEF, aslist=c.DecoupledElementList
    )


@c.xtype_handler(None, XT_REQ_TYPE_ENUM_DEF)
class AttributeDefinitionEnumeration(ReqIFElement):
    """An enumeration attribute definition for requirement types"""

    _xmltag = "enumeration"

    data_type = c.AttrProxyAccessor(EnumDataTypeDefinition, "definitionType")
    multi_valued = xmltools.AttributeProperty(
        "_element",
        "multiValued",
        optional=True,
        default=False,
        returntype=bool,
    )


@c.xtype_handler(None, XT_REQ_ATTR_ENUMVALUE)
class EnumerationValueAttribute(AbstractRequirementsAttribute):
    """An enumeration attribute."""

    definition = c.AttrProxyAccessor(
        AttributeDefinitionEnumeration, "definition"
    )

    @property
    def values(self) -> str | tuple[str]:
        def aslist(
            model: capellambse.MelodyModel,
            elems: t.Sequence[etree._Element],
            class_: t.Type[c.T],
            *,
            parent: t.Any = None,
        ) -> tuple[str] | str:
            assert elems
            if len(elems) > 1:
                return tuple(
                    (e.get("ReqIFLongName", undefined_value) for e in elems)
                )
            return elems[0].get("ReqIFLongName", undefined_value)

        return c.AttrProxyAccessor(str, "values", aslist=aslist).__get__(self)


class AbstractType(ReqIFElement):
    attribute_definitions = c.ProxyAccessor(
        AttributeDefinition,
        XT_REQ_TYPE_ATTR_DEF,
        aslist=c.DecoupledElementList,
    )
    enum_definitions = c.ProxyAccessor(
        AttributeDefinitionEnumeration,
        XT_REQ_TYPE_ENUM_DEF,
        aslist=c.DecoupledElementList,
    )


@c.xtype_handler(None, XT_MODULE_TYPE)
class ModuleType(AbstractType):
    """A requirement-module type"""


@c.xtype_handler(None, XT_RELATION_TYPE)
class RelationType(AbstractType):
    """A requirement-relation type"""


@c.xtype_handler(None, XT_REQ_TYPE)
class RequirementType(AbstractType):
    """A requirement type"""


@c.xtype_handler(None, XT_REQUIREMENT)
class Requirement(ReqIFElement):
    """A ReqIF Requirement."""

    _xmltag = "ownedRequirements"

    chapter_name = xmltools.AttributeProperty(
        "_element", "ReqIFChapterName", optional=True
    )
    foreign_id = xmltools.AttributeProperty(
        "_element", "ReqIFForeignID", optional=True, returntype=int
    )
    text = xmltools.AttributeProperty(
        "_element", "ReqIFText", optional=True, returntype=c.markuptype
    )
    attributes = AttributeAccessor()
    relations = c.ProxyAccessor(
        c.GenericElement,
        (XT_INC_RELATION, XT_OUT_RELATION, XT_INT_RELATION),
        aslist=c.ElementList,
    )
    type = c.AttrProxyAccessor(RequirementType, "requirementType")


@c.xtype_handler(None, XT_FOLDER)
class RequirementsFolder(Requirement):
    """A folder that stores Requirements."""

    _xmltag = "ownedRequirements"

    folders: c.Accessor
    requirements = c.ProxyAccessor(
        Requirement, XT_REQUIREMENT, aslist=c.ElementList
    )


@c.xtype_handler(None, XT_MODULE)
class RequirementsModule(ReqIFElement):
    """A ReqIF Module that bundles multiple Requirement folders."""

    _xmltag = "ownedExtensions"

    folders = c.ProxyAccessor(
        RequirementsFolder, XT_FOLDER, aslist=c.ElementList
    )
    requirements = c.ProxyAccessor(
        Requirement, XT_REQUIREMENT, aslist=c.ElementList
    )
    type = c.AttrProxyAccessor(ModuleType, "moduleType")
    attributes = AttributeAccessor()


class AbstractRequirementsRelation(ReqIFElement):
    _xmltag = "ownedRelations"

    type = c.AttrProxyAccessor(RelationType, "relationType")
    source = c.AttrProxyAccessor(Requirement, "source")
    target = c.AttrProxyAccessor(c.GenericElement, "target")


@c.xtype_handler(None, XT_OUT_RELATION)
class RequirementsOutRelation(AbstractRequirementsRelation):
    """A Relation between an object and a requirement."""

    _xmltag = "ownedExtensions"

    source = c.AttrProxyAccessor(Requirement, "target")
    target = c.AttrProxyAccessor(c.GenericElement, "source")


@c.xtype_handler(None, XT_INC_RELATION)
class RequirementsIncRelation(AbstractRequirementsRelation):
    """A Relation between a requirement and an object."""


@c.xtype_handler(None, XT_INT_RELATION)
class RequirementsIntRelation(AbstractRequirementsRelation):
    """A Relation between two requirements."""


@c.xtype_handler(None, XT_REQ_TYPES_F)
class RequirementsTypesFolder(ReqIFElement):
    data_type_definitions = c.ProxyAccessor(
        DataTypeDefinition,
        XT_REQ_TYPES_DATA_DEF,
        aslist=c.DecoupledElementList,
    )
    enum_data_type_definitions = c.ProxyAccessor(
        EnumDataTypeDefinition, XT_REQ_TYPE_ENUM, aslist=c.DecoupledElementList
    )
    module_types = c.ProxyAccessor(
        ModuleType, XT_MODULE_TYPE, aslist=c.DecoupledElementList
    )
    relation_types = c.ProxyAccessor(
        RelationType, XT_RELATION_TYPE, aslist=c.DecoupledElementList
    )
    requirement_types = c.ProxyAccessor(
        RequirementType, XT_REQ_TYPE, aslist=c.DecoupledElementList
    )


def init() -> None:
    c.set_accessor(
        RequirementsFolder,
        "folders",
        c.ProxyAccessor(RequirementsFolder, XT_FOLDER, aslist=c.ElementList),
    )
    c.set_accessor(c.GenericElement, "requirements", ElementRelationAccessor())
    c.set_accessor(
        crosslayer.BaseArchitectureLayer,
        "requirement_modules",
        c.ProxyAccessor(RequirementsModule, XT_MODULE, aslist=c.ElementList),
    )
    c.set_accessor(
        crosslayer.BaseArchitectureLayer,
        "all_requirements",
        c.ProxyAccessor(
            Requirement,
            XT_REQUIREMENT,
            aslist=c.DecoupledElementList,
            rootelem=XT_MODULE,
            deep=True,
        ),
    )
    c.set_accessor(
        crosslayer.BaseArchitectureLayer,
        "requirement_types_folders",
        c.ProxyAccessor(
            RequirementsTypesFolder,
            XT_REQ_TYPES_F,
            aslist=c.DecoupledElementList,
        ),
    )
    c.set_accessor(
        crosslayer.BaseArchitectureLayer,
        "all_requirement_types",
        c.ProxyAccessor(
            RequirementType,
            XT_REQ_TYPE,
            aslist=c.ElementList,
            rootelem=XT_MODULE,
            deep=True,
        ),
    )
    c.set_accessor(
        crosslayer.BaseArchitectureLayer,
        "all_module_types",
        c.ProxyAccessor(
            ModuleType,
            XT_MODULE_TYPE,
            aslist=c.ElementList,
            rootelem=XT_MODULE,
            deep=True,
        ),
    )
    c.set_accessor(
        crosslayer.BaseArchitectureLayer,
        "all_relation_types",
        c.ProxyAccessor(
            RelationType,
            XT_RELATION_TYPE,
            aslist=c.ElementList,
            rootelem=XT_MODULE,
            deep=True,
        ),
    )
