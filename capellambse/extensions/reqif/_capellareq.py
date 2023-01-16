# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""The 'CapellaRequirements' namespace."""
from __future__ import annotations

__all__ = [
    "CapellaIncomingRelation",
    "CapellaModule",
    "CapellaOutgoingRelation",
    "CapellaTypesFolder",
    "ElementRelationAccessor",
    "RelationsList",
    "RequirementsRelationAccessor",
]

import collections.abc as cabc
import os
import typing as t

from lxml import etree

import capellambse
import capellambse.model.common as c

from . import _requirements as rq
from . import exporter

c.XTYPE_ANCHORS[__name__] = "CapellaRequirements"


@c.xtype_handler(None)
class CapellaModule(rq.ReqIFElement):
    """A ReqIF Module that bundles multiple Requirement folders."""

    _xmltag = "ownedExtensions"

    folders = c.DirectProxyAccessor(rq.Folder, aslist=c.ElementList)
    requirements = c.DirectProxyAccessor(rq.Requirement, aslist=c.ElementList)
    type = c.AttrProxyAccessor(rq.ModuleType, "moduleType")
    attributes = rq.AttributeAccessor()

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


@c.xtype_handler(None)
class CapellaIncomingRelation(rq.AbstractRequirementsRelation):
    """A Relation between a requirement and an object."""

    _xmltag = "ownedRelations"


@c.xtype_handler(None)
class CapellaOutgoingRelation(rq.AbstractRequirementsRelation):
    """A Relation between an object and a requirement."""

    _xmltag = "ownedExtensions"

    source = c.AttrProxyAccessor(rq.Requirement, "target")
    target = c.AttrProxyAccessor(c.GenericElement, "source")


@c.xtype_handler(None)
class CapellaTypesFolder(rq.ReqIFElement):
    _xmltag = "ownedExtensions"

    data_type_definitions = c.DirectProxyAccessor(
        c.GenericElement,
        (rq.DataTypeDefinition, rq.EnumerationDataTypeDefinition),
        aslist=c.MixedElementList,
    )
    module_types = c.DirectProxyAccessor(rq.ModuleType, aslist=c.ElementList)
    relation_types = c.DirectProxyAccessor(
        rq.RelationType, aslist=c.ElementList
    )
    requirement_types = c.DirectProxyAccessor(
        rq.RequirementType, aslist=c.ElementList
    )


class RequirementsRelationAccessor(
    c.WritableAccessor["rq.AbstractRequirementsRelation"]
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
            obj._model._loader.iterchildren_xt(
                obj._element, c.build_xtype(CapellaIncomingRelation)
            )
        )

        for i in obj._model._loader.iterall_xt(
            c.build_xtype(CapellaOutgoingRelation)
        ):
            if CapellaOutgoingRelation.from_model(obj._model, i).source == obj:
                rel_objs.append(i)

        for i in obj._model._loader.iterall_xt(
            c.build_xtype(rq.InternalRelation)
        ):
            rel = rq.InternalRelation.from_model(obj._model, i)
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
    ) -> rq.InternalRelation | CapellaIncomingRelation:
        if "target" not in kw:
            raise TypeError("No `target` for new requirement relation")
        cls = self._find_relation_type(kw["target"])
        parent = elmlist._parent._element
        with elmlist._model._loader.new_uuid(parent) as uuid:
            return cls(
                elmlist._model,
                parent,
                **kw,
                source=elmlist._parent,
                uuid=uuid,
                xtype=c.build_xtype(cls),
            )

    def _find_relation_type(
        self, target: c.GenericElement
    ) -> type[rq.InternalRelation | CapellaIncomingRelation]:
        if isinstance(target, rq.Requirement):
            return rq.InternalRelation
        elif isinstance(target, rq.ReqIFElement):
            raise TypeError(
                "Cannot create relations to targets of type"
                f" {type(target).__name__}"
            )
        else:
            return rq.InternalRelation


class RelationsList(c.ElementList["rq.AbstractRequirementsRelation"]):
    def __init__(
        self,
        model: capellambse.MelodyModel,
        elements: list[etree._Element],
        elemclass: type[t.Any] | None = None,
        *,
        source: c.ModelObject,
    ) -> None:
        del elemclass
        super().__init__(model, elements, rq.AbstractRequirementsRelation)
        self._source = source

    @t.overload
    def __getitem__(self, idx: int | str) -> rq.AbstractRequirementsRelation:
        ...

    @t.overload
    def __getitem__(
        self, idx: slice
    ) -> c.ElementList[rq.AbstractRequirementsRelation]:
        ...

    def __getitem__(self, idx):
        rel = super().__getitem__(idx)
        if isinstance(rel, c.ElementList):
            return rel

        assert isinstance(rel, rq.AbstractRequirementsRelation)
        assert self._source in (rel.source, rel.target)
        if self._source == rel.source:
            return rel.target
        else:
            return rel.source

    def by_relation_type(self, reltype: str) -> RelationsList:
        matches = []
        for elm in self._elements:
            rel_elm = c.GenericElement.from_model(self._model, elm)
            assert isinstance(rel_elm, rq.AbstractRequirementsRelation)
            if rel_elm.type is not None and rel_elm.type.name == reltype:
                matches.append(elm)
        return self._newlist(matches)

    def by_relation_class(
        self, class_: t.Literal["incoming", "outgoing", "internal"]
    ) -> RelationsList:
        relation_types = {
            "incoming": CapellaIncomingRelation,
            "outgoing": CapellaOutgoingRelation,
            "internal": rq.InternalRelation,
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


class ElementRelationAccessor(
    c.WritableAccessor["rq.AbstractRequirementsRelation"]
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
            CapellaIncomingRelation,
            rq.InternalRelation,
            CapellaOutgoingRelation,
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


c.set_accessor(rq.Requirement, "relations", RequirementsRelationAccessor())
c.set_accessor(rq.Requirement, "related", ElementRelationAccessor())
