# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

__all__ = [
    "CapellaIncomingRelation",
    "CapellaModule",
    "CapellaOutgoingRelation",
    "CapellaRelation",
    "CapellaTypesFolder",
    "ElementRelationAccessor",
    "RelationsList",
    "RequirementsRelationAccessor",
]

import collections.abc as cabc
import contextlib
import os
import sys
import typing as t
import warnings

from lxml import etree

import capellambse
import capellambse.model as m
from capellambse.metamodel import namespaces as ns

from . import exporter, requirements

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

if t.TYPE_CHECKING:
    from capellambse.metamodel import capellacore  # noqa: F401

NS = m.Namespace(
    "http://www.polarsys.org/capella/requirements",
    "CapellaRequirements",
    "org.polarsys.capella.vp.requirements",
)


class CapellaTypesFolder(requirements.TypesFolder):
    _xmltag = "ownedExtensions"

    @property
    @deprecated(
        (
            "CapellaTypesFolder.module_types is deprecated,"
            " use 'types.by_class(ModuleType)' instead"
        ),
        category=FutureWarning,
    )
    def module_types(self) -> m.ElementList[requirements.ModuleType]:
        return self.types.by_class(requirements.ModuleType)

    @property
    @deprecated(
        (
            "CapellaTypesFolder.relation_types is deprecated,"
            " use 'types.by_class(ModuleType)' instead"
        ),
        category=FutureWarning,
    )
    def relation_types(self) -> m.ElementList[requirements.RelationType]:
        return self.types.by_class(requirements.RelationType)

    @property
    @deprecated(
        (
            "CapellaTypesFolder.requirement_types is deprecated,"
            " use 'types.by_class(ModuleType)' instead"
        ),
        category=FutureWarning,
    )
    def requirement_types(self) -> m.ElementList[requirements.RequirementType]:
        return self.types.by_class(requirements.RequirementType)

    if not t.TYPE_CHECKING:
        data_type_definitions = m.DeprecatedAccessor("definition_types")


class CapellaModule(requirements.Module):
    _xmltag = "ownedExtensions"

    requirement_types_folders = m.Filter["CapellaTypesFolder"](
        "extensions", (NS, "CapellaTypesFolder")
    )

    @property
    @deprecated(
        (
            "CapellaModule.folders is deprecated,"
            " use 'requirements.by_class(Folder)' instead"
        ),
        category=FutureWarning,
    )
    def folders(self) -> m.ElementList[requirements.Folder]:
        return self.requirements.by_class(requirements.Folder)

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


class CapellaRelation(requirements.AbstractRelation, abstract=True):
    pass


class CapellaIncomingRelation(CapellaRelation):
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

    source = m.Single["requirements.Requirement"](
        m.Association((requirements.NS, "Requirement"), "source")
    )
    target = m.Single["capellacore.CapellaElement"](
        m.Association((ns.CAPELLACORE, "CapellaElement"), "target")
    )


class CapellaOutgoingRelation(CapellaRelation):
    _xmltag = "ownedExtensions"

    def __init__(
        self,
        model: m.MelodyModel,
        parent: etree._Element,
        xmltag: str | None = None,
        /,
        **kw: t.Any,
    ) -> None:
        kw.setdefault("target", m.wrap_xml(model, parent))
        super().__init__(model, parent, xmltag, **kw)

    # NOTE: source/target are swapped intentionally here,
    # so that 'some_relation.source' is always a Requirement
    target = m.Single["capellacore.CapellaElement"](
        m.Association((ns.CAPELLACORE, "CapellaElement"), "source")
    )
    source = m.Single["requirements.Requirement"](
        m.Association((requirements.NS, "Requirement"), "target")
    )


class RequirementsRelationAccessor(
    m.WritableAccessor[requirements.AbstractRelation]
):
    """Searches for requirement relations in the architecture layer."""

    __slots__ = ("aslist",)

    def __init__(self, *args, **kw) -> None:
        super().__init__(
            *args, **kw, aslist=m.ElementList, single_attr="long_name"
        )

    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:  # pragma: no cover
            return self

        return self._make_list(obj, self._find_relations(obj))

    def __set__(self, obj, value: t.Any) -> None:
        if not isinstance(value, cabc.Iterable):
            value = (value,)

        if CapellaOutgoingRelation in [type(i) for i in value]:
            raise NotImplementedError("Cannot insert CapellaOutgoingRelations")

        for i in self._find_relations(obj):
            ip = i.getparent()
            assert ip is not None
            ip.remove(i)
        obj._element.extend(value)

    def __delete__(self, obj) -> None:
        assert self.aslist is not None

        for i in self._find_relations(obj):
            parent = i.getparent()
            assert parent is not None
            parent.remove(i)

    def _find_relations(self, obj) -> list[etree._Element]:
        rels = obj._model.search(
            CapellaIncomingRelation,
            requirements.InternalRelation,
            CapellaOutgoingRelation,
        )
        return [i._element for i in rels if obj in (i.source, i.target)]

    def _make_list(self, parent_obj, elements):
        assert self.aslist is not None
        return self.aslist(
            parent_obj._model, elements, m.ModelElement, parent=parent_obj
        )

    def create(
        self,
        elmlist: m.ElementListCouplingMixin,
        typehint: str | None = None,
        /,
        **kw: t.Any,
    ) -> requirements.InternalRelation | CapellaIncomingRelation:
        del typehint

        warnings.warn(
            (
                "Mutating Requirement.relations directly is deprecated"
                " and will soon no longer affect the model,"
                " mutate the respective Containment feature instead"
                " (e.g. Requirement.owned_relations)"
            ),
            category=FutureWarning,
            stacklevel=2,
        )

        if "target" not in kw:
            raise m.InvalidModificationError(
                "No `target` for new requirement relation"
            )
        cls = self._find_relation_type(kw["target"])
        parent = elmlist._parent._element
        with elmlist._model._loader.new_uuid(parent) as uuid:
            return cls(
                elmlist._model,
                parent,
                **kw,
                source=elmlist._parent,
                uuid=uuid,
            )

    def delete(self, elmlist, obj) -> None:
        warnings.warn(
            (
                "Mutating Requirement.relations directly is deprecated"
                " and will soon no longer affect the model,"
                " mutate the respective Containment feature instead"
                " (e.g. Requirement.owned_relations)"
            ),
            category=FutureWarning,
            stacklevel=2,
        )

        assert self.aslist is not None
        relations = self._find_relations(elmlist._parent)
        for relation in relations:
            if relation == obj._element:
                obj.parent._model._loader.idcache_remove(relation)
                obj.parent._element.remove(relation)
                break
        else:
            raise ValueError("Cannot delete: Target object not in this list")

    def insert(
        self,
        elmlist: m.ElementListCouplingMixin,
        index: int,
        value: m.ModelObject | m.NewObject,
    ) -> None:
        warnings.warn(
            (
                "Mutating Requirement.relations directly is deprecated"
                " and will soon no longer affect the model,"
                " mutate the respective Containment feature instead"
                " (e.g. Requirement.owned_relations)"
            ),
            category=FutureWarning,
            stacklevel=2,
        )

        if isinstance(value, m.NewObject):
            raise NotImplementedError("Cannot insert new objects yet")

        if isinstance(value, CapellaOutgoingRelation):
            if not value.target:
                raise RuntimeError(
                    "Cannot insert outgoing relation without target:"
                    f" {value._short_repr_()}"
                )
            parent = value.target._element
        else:
            assert isinstance(
                value, CapellaIncomingRelation | requirements.InternalRelation
            )
            assert elmlist._parent == value.source
            parent = elmlist._parent._element

        parent.insert(index, value._element)
        elmlist._model._loader.idcache_index(value._element)

    @contextlib.contextmanager
    def purge_references(
        self, obj: m.ModelObject, target: m.ModelObject
    ) -> cabc.Generator[None, None, None]:
        """Do nothing.

        This is a no-op, as this accessor provides a virtual relation.

        The relation objects it handles are cleaned up by removing the
        source or target attribute.
        """
        del obj, target
        yield

    def _find_relation_type(
        self, target: m.ModelElement
    ) -> type[requirements.InternalRelation | CapellaIncomingRelation]:
        if isinstance(target, requirements.Requirement):
            return requirements.InternalRelation
        if isinstance(target, requirements.ReqIFElement):
            raise m.InvalidModificationError(
                "Cannot create relations to targets of type"
                f" {type(target).__name__}"
            )
        return CapellaIncomingRelation


class RelationsList(m.ElementList[requirements.AbstractRelation]):
    def __init__(
        self,
        model: capellambse.MelodyModel,
        elements: list[etree._Element],
        elemclass: type[t.Any] | None = None,
        *,
        source: m.ModelObject,
    ) -> None:
        del elemclass
        super().__init__(model, elements)
        self._source = source

    @t.overload
    def __getitem__(self, idx: int) -> requirements.AbstractRelation: ...
    @t.overload
    def __getitem__(self, idx: slice) -> RelationsList: ...
    @t.overload
    def __getitem__(self, idx: str) -> t.Any: ...
    def __getitem__(self, idx: int | slice | str) -> t.Any:
        rel = super().__getitem__(idx)
        if isinstance(rel, m.ElementList):
            return rel

        assert isinstance(rel, requirements.AbstractRelation)
        assert self._source in (rel.source, rel.target)
        if self._source == rel.source:
            return rel.target
        return rel.source

    def by_relation_type(self, reltype: str) -> RelationsList:
        warnings.warn(
            (
                "Requirement.related.by_relation_type is deprecated,"
                "use 'Requirement.relations.by_type(...)'"
                " or 'ModelElement.requirements_relations.by_type(...)' instead"
            ),
            category=FutureWarning,
            stacklevel=2,
        )

        matches = []
        for elm in self._elements:
            rel_elm = m.wrap_xml(self._model, elm)
            assert isinstance(rel_elm, requirements.AbstractRelation)
            if rel_elm.type is not None and rel_elm.type.long_name == reltype:
                matches.append(elm)
        return self._newlist(matches)

    def by_relation_class(
        self, class_: t.Literal["incoming", "outgoing", "internal"]
    ) -> RelationsList:
        warnings.warn(
            (
                "Requirement.related.by_relation_class is deprecated,"
                "use 'Requirement.relations.by_class(...)' instead"
            ),
            category=FutureWarning,
            stacklevel=2,
        )

        relation_types = {
            "incoming": CapellaIncomingRelation,
            "outgoing": CapellaOutgoingRelation,
            "internal": requirements.InternalRelation,
        }
        matches: list[etree._Element] = []
        for elm in self._elements:
            rel_elm = m.wrap_xml(self._model, elm)
            if isinstance(rel_elm, relation_types[class_]):
                matches.append(rel_elm._element)
        return self._newlist(matches)

    def _newlist(self, elements: list[etree._Element]) -> RelationsList:
        listtype = self._newlist_type()
        assert issubclass(listtype, RelationsList)
        return listtype(self._model, elements, source=self._source)


class ElementRelationAccessor(m.WritableAccessor[m.ModelElement]):
    """Provides access to RequirementsRelations of a ModelElement."""

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
            requirements.InternalRelation,
            CapellaOutgoingRelation,
        ):
            if None in (relation.source, relation.target):
                continue
            if obj in (relation.source, relation.target):
                relations.append(relation._element)
        return self._make_list(obj, relations)

    @contextlib.contextmanager
    def purge_references(
        self, obj: m.ModelObject, target: m.ModelObject
    ) -> cabc.Generator[None, None, None]:
        """Do nothing.

        This is a no-op, as this accessor provides a virtual relation.

        The relation objects it handles are cleaned up by removing the
        source or target attribute.
        """
        del obj, target
        yield

    def _make_list(self, parent_obj, elements):
        assert self.aslist is not None
        return self.aslist(
            parent_obj._model,
            elements,
            None,
            parent=parent_obj,
            source=parent_obj,
        )


requirements.Requirement.relations = RequirementsRelationAccessor()  # type: ignore[deprecated]
requirements.Requirement.related = ElementRelationAccessor()  # type: ignore[deprecated]
