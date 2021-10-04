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

import collections.abc
import itertools
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
XT_REQ_TYPES_F = "CapellaRequirements:CapellaTypesFolder"

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

XT_REQ_TYPE = "Requirements:RequirementType"
XT_RELATION_TYPE = "Requirements:RelationType"
XT_MODULE_TYPE = "Requirements:ModuleType"


class RequirementsRelationAccessor(
    c.WritableAccessor["AbstractRequirementsRelation"]
):
    """Searches for requirement relations in the architecture layer."""

    # pylint: disable=abstract-method  # Only partially implemented for now

    __slots__ = ("aslist",)

    def __init__(self, *args, **kw) -> None:
        super().__init__(*args, **kw, aslist=c.ElementList)

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

        assert self.aslist is not None
        return self.aslist(obj._model, rel_objs, c.GenericElement, parent=obj)

    def create(
        self,
        elmlist: c.ElementListCouplingMixin,
        /,
        *type_hints: t.Optional[str],
        **kw: t.Any,
    ) -> c.T:
        if "target" not in kw:
            raise TypeError("No `target` for new requirement relation")
        cls: t.Type[c.T]
        cls, xtype = self._find_relation_type(kw["target"])
        parent = elmlist._parent._element
        with elmlist._model._loader.new_uuid(parent) as uuid:
            return cls(  # type: ignore[call-arg]
                elmlist._model,
                parent,
                **kw,
                source=elmlist._parent,
                uuid=uuid,
                xtype=xtype,
            )

    def _find_relation_type(
        self, target: c.GenericElement
    ) -> t.Tuple[t.Type[c.T], str]:
        if isinstance(target, Requirement):
            return (
                t.cast(t.Type[c.T], RequirementsIntRelation),
                XT_INT_RELATION,
            )
        elif isinstance(target, ReqIFElement):
            raise TypeError(
                "Cannot create relations to targets of type"
                f" {type(target).__name__}"
            )
        else:
            return (
                t.cast(t.Type[c.T], RequirementsIncRelation),
                XT_INC_RELATION,
            )


class ElementRelationAccessor(
    c.WritableAccessor["AbstractRequirementsRelation"]
):
    """Provides access to RequirementsRelations of a GenericElement."""

    # pylint: disable=abstract-method  # Only partially implemented for now

    __slots__ = ("aslist",)

    def __init__(self) -> None:
        super().__init__(aslist=RequirementRelationsList)

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

        assert self.aslist is not None
        return self.aslist(
            obj._model,
            list(
                itertools.chain(
                    (i for i in inc_int_relations if targetof(i) == obj),
                    (i for i in out_relations if targetof(i) == obj),
                )
            ),
            None,
            parent=obj,
            side="source",
        )

    def create(
        self,
        elmlist: c.ElementListCouplingMixin,
        /,
        *type_hints: t.Optional[str],
        **kw: t.Any,
    ) -> c.T:
        if "target" not in kw:
            raise TypeError("No `target` for new requirement relation")
        if not isinstance(kw["target"], Requirement):
            raise TypeError("`target` must be of type 'Requirement'")
        cls = t.cast(t.Type[c.T], RequirementsOutRelation)
        parent = elmlist._parent
        with parent._model._loader.new_uuid(parent._element) as uuid:
            return cls(  # type: ignore[call-arg]
                elmlist._model,
                parent,
                **kw,
                source=elmlist._parent,
                uuid=uuid,
                xtype=XT_OUT_RELATION,
            )


class RequirementTypeAccessor(c.Accessor):
    """Provides access to requirement and relation types."""

    __slots__ = (
        "attr",
        "xtype",
    )

    def __init__(self, attr, xtype):
        super().__init__()
        self.attr = attr
        self.xtype = xtype

    def __get__(self, obj, objtype):
        del objtype
        if obj is None:  # pragma: no cover
            return self

        type_link = obj._element.get(self.attr)
        if type_link is None:
            return None

        try:
            type_elm = obj._model._loader.follow_link(obj._element, type_link)
        except KeyError:
            return None
        else:
            return type_elm.get("ReqIFLongName")

    def __set__(self, obj, value) -> None:
        # pylint: disable=undefined-loop-variable
        # <https://github.com/PyCQA/pylint/issues/1175>
        if value is None:
            try:
                del obj._element.attrib[self.attr]
            except KeyError:
                pass
        else:
            for type_elm in obj._model._loader.iterall_xt(self.xtype):
                if type_elm.get("ReqIFLongName") == value:
                    break
            else:
                raise ValueError(f"Invalid {self.attr}: {value}")

            obj._element.set(
                self.attr,
                obj._model._loader.create_link(obj._element, type_elm),
            )


class RequirementRelationsList(c.ElementList["AbstractRequirementsRelation"]):
    def __init__(
        self,
        model: capellambse.MelodyModel,
        elements: t.List[etree._Element],
        elemclass: t.Type[t.Any] = None,
        *,
        side: str = None,
    ) -> None:
        del elemclass
        assert side in {"source", "target"}
        super().__init__(model, elements, c.GenericElement)  # type: ignore[arg-type]
        self._side = side

    def __getitem__(self, idx: int) -> c.GenericElement:  # type: ignore[override]
        return getattr(
            c.GenericElement.from_model(self._model, self._elements[idx]),
            self._side,
        )

    def by_relation_type(self, reltype: str) -> RequirementRelationsList:
        matches = []
        for elm in self._elements:
            rel_elm = c.GenericElement.from_model(self._model, elm)
            assert isinstance(rel_elm, ReqIFElement)
            if rel_elm.type == reltype:
                matches.append(elm)
        return type(self)(self._model, matches, None, side=self._side)

    def _newlist(self, elements):
        listtype = self._newlist_type()
        assert issubclass(listtype, RequirementRelationsList)
        return listtype(self._model, elements, side=self._side)


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
    type: RequirementTypeAccessor = property(lambda _: None)  # type: ignore[assignment]

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


# TODO: Document and refactor attributes
class RequirementsAttributes(collections.abc.Mapping):
    """Handles extension attributes on Requirements."""

    _model: capellambse.MelodyModel
    _element: etree._Element

    @classmethod
    def from_model(
        cls,
        model: capellambse.MelodyModel,
        element: etree._Element,
    ) -> RequirementsAttributes:
        """Create RequirementsAttributes for a model Requirement."""
        self = cls.__new__(cls)
        self._model = model
        self._element = element
        return self

    def __init__(self) -> None:
        raise TypeError("Cannot create RequirementsAttributes this way")

    def __len__(self) -> int:
        return sum(1 for i in self)

    def __iter__(self) -> t.Iterator[str]:
        for child in self._element.iterchildren():
            if child.get(helpers.ATT_XT) not in XT_REQ_ATTRIBUTES:
                continue
            try:
                definition = self._model._loader[child.attrib["definition"]]
            except KeyError:
                continue

            name = definition.get("ReqIFLongName") or definition.get(
                "ReqIFName"
            )
            if name:
                yield name

    def __getitem__(self, key: str) -> t.Optional[str]:
        for child in self._element.iterchildren():
            if child.get(helpers.ATT_XT) not in XT_REQ_ATTRIBUTES:
                continue

            try:
                definition = self._model._loader[child.attrib["definition"]]
            except KeyError:
                continue
            if not (
                definition.get("ReqIFLongName") == key
                or definition.get("ReqIFName") == key
            ):
                continue

            if child.get(helpers.ATT_XT) == XT_REQ_ATTR_ENUMVALUE:
                elm = self._model._loader[child.get("values")]
                return elm.get("ReqIFLongName") or elm.get("ReqIFName") or None
            elif child.get(helpers.ATT_XT) == XT_REQ_ATTR_STRINGVALUE:
                return child.get("value")
            else:
                break
        raise KeyError(key)


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
    attributes = c.AlternateAccessor(RequirementsAttributes)
    relations = RequirementsRelationAccessor()
    type = RequirementTypeAccessor("requirementType", XT_REQ_TYPE)


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
    type = RequirementTypeAccessor("moduleType", XT_MODULE_TYPE)


class AbstractRequirementsRelation(ReqIFElement):
    _required_attrs = frozenset({"source", "target"})
    type = RequirementTypeAccessor("relationType", XT_RELATION_TYPE)


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

    source = c.AttrProxyAccessor(Requirement, "source")
    target = c.AttrProxyAccessor(c.GenericElement, "target")


@c.xtype_handler(None, XT_INT_RELATION)
class RequirementsIntRelation(AbstractRequirementsRelation):
    """A Relation between two requirements."""

    _xmltag = "ownedRelations"

    source = c.AttrProxyAccessor(Requirement, "source")
    target = c.AttrProxyAccessor(Requirement, "target")


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
            aslist=c.ElementList,
            rootelem=XT_MODULE,
            deep=True,
        ),
    )
