# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

__all__ = [
    "Metadata",
    "Viewpoint",
    "ViewpointReferences",
]

import collections.abc as cabc
import typing as t
import weakref

import typing_extensions as te
from lxml import etree

from . import _model, _obj

NS = _obj.Namespace(
    "http://www.polarsys.org/kitalpha/ad/metadata/1.0.0",
    "metadata",
    _obj.CORE_VIEWPOINT,
)


class Viewpoint(_obj.ModelElement):
    name = _obj.StringPOD(name="vpId", required=True)
    version = _obj.StringPOD(name="version", required=True)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Viewpoint):
            return (self.name, self.version) == (other.name, other.version)
        elif isinstance(other, tuple) and len(other) == 2:
            return (self.name, self.version) == other
        else:
            return NotImplemented


class _ViewpointRefDescriptor(_obj.RelationshipDescriptor["Viewpoint"]):
    @t.overload
    def __get__(self, obj: None, _: t.Any) -> te.Self: ...
    @t.overload
    def __get__(
        self, obj: _obj.ModelElement, _: t.Any
    ) -> ViewpointReferences: ...
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        data = obj.__dict__.setdefault("__modeldata", {})
        return data[id(self)]

    def __set__(self, obj: _obj.ModelElement, value):
        data = obj.__dict__.setdefault("__modeldata", {})
        refs = data[id(self)]
        refs.clear()
        if isinstance(value, cabc.Mapping):
            value = value.items()
        for vp in value:
            if isinstance(vp, tuple):
                refs.activate(*vp)
            else:
                refs.activate(vp)

    def from_xml(
        self,
        obj: _obj.ModelElement,
        elem: etree._Element,
        lazy_attributes: cabc.MutableSet[tuple[str, str]],
    ) -> None:
        vps: list[Viewpoint] = []
        for ref in list(elem):
            if ref.tag != "viewpointReferences":
                continue

            vp = Viewpoint._parse_xml(obj._model, ref, lazy_attributes)
            vps.append(vp)
            elem.remove(ref)
        refs = ViewpointReferences(obj._model, vps)
        obj.__dict__.setdefault("__modeldata", {})[id(self)] = refs

    def to_xml(
        self,
        obj: _obj.ModelElement,
        elem: etree._Element,
        namespaces: cabc.MutableMapping[str, str],
    ) -> None:
        refs = getattr(obj, self.__name__)
        for vp in refs:
            vp._to_xml(namespaces)


class ViewpointReferences(_obj.ElementList["Viewpoint"]):
    def __init__(self, model: _model.Model, wrapped: list[Viewpoint]) -> None:
        coupler = _obj._ModelCoupler(model, wrapped)
        super().__init__(coupler, mapkey="name", mapvalue="version")
        self.__model = weakref.ref(model)

    def __repr__(self) -> str:
        vp = {vp.name: vp.version for vp in self}
        return f"{type(self).__name__}({vp!r})"

    @t.overload
    def activate(self, vpname: str, version: str, /) -> None: ...
    @t.overload
    def activate(self, vp: Viewpoint, /) -> None: ...
    def activate(
        self, vp: Viewpoint | str, version: str | None = None
    ) -> None:
        if isinstance(vp, str):
            model = self.__model()
            if model is None:
                raise RuntimeError("Model has been deleted")
            vp = Viewpoint(model, name=vp, version=version)
        if any(vp.name == v.name for v in self):
            raise ValueError(f"Viewpoint {vp.name!r} is already active")
        self.append(vp)

    def deactivate(self, vp: Viewpoint | str, /) -> None:
        if not isinstance(vp, str):
            vp = vp.name
        for i, v in enumerate(self):
            if v.name == vp:
                del self[i]
                return

    def as_dict(self) -> dict[str, str]:
        """Generate a dictionary mapping viewpoints to their versions."""
        return {vp.name: vp.version for vp in self}


class Metadata(_obj.ModelElement):
    """Metadata about a Capella model.

    This class stores metadata about a Capella model, such as the
    Capella version that was used to create it, and the active
    viewpoints and their versions. It is tightly coupled to its parent
    :class:`Model` instance, and should not be used outside of it.
    """

    viewpoints = _ViewpointRefDescriptor()
    """The active viewpoints and their versions in the model."""

    @property
    def capella_version(self) -> str:
        """The Capella version that was used to create the model.

        This may influence which attributes are available on some model
        objects.
        """
        return self.viewpoints[_obj.CORE_VIEWPOINT].version

    def __init__(self, model: _model.Model, capella_version: str) -> None:
        super().__init__(
            model,
            viewpoints={_obj.CORE_VIEWPOINT: capella_version},
        )
