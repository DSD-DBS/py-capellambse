# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
"""Object-level managed property values."""
from __future__ import annotations

__all__ = [
    "ManagedPropertyValueDomain",
    "ManagedPropertyValueGroup",
    "ObjectPVMT",
]

import collections.abc as cabc
import typing as t

import markupsafe
from lxml import etree

import capellambse
import capellambse.model.common as c

_C = t.TypeVar("_C", bound="_PVMTBase")


class _PVMTBase:
    _model: capellambse.MelodyModel
    _element: etree._Element

    owner = c.AlternateAccessor(c.GenericElement)

    def __init__(self, *__: t.Any, **_: t.Any) -> None:
        raise TypeError(f"Cannot instantiate {type(self).__name__} directly")

    @classmethod
    def from_model(
        cls: type[_C], model: capellambse.MelodyModel, element: etree._Element
    ) -> _C:
        """Wrap a model element for accessing its applied PVMT."""
        if not hasattr(model, "pvmt"):
            raise RuntimeError("Cannot access PVMT: Viewpoint not installed")

        self = cls.__new__(cls)
        self._model = model
        self._element = element
        self._constructed = True
        return self


class _PVMTGroupAccessor(c.Accessor):
    ...


class ManagedPropertyValueGroup(_PVMTBase, cabc.MutableMapping):
    """Access a PVMT group that has been applied on a model object."""

    def __delitem__(self, key: str) -> t.NoReturn:
        raise TypeError("Cannot delete individual properties in a PVMT group")

    def __getitem__(self, key: str) -> t.Any:
        raise NotImplementedError()  # TODO

    def __iter__(self) -> cabc.Iterator[str]:
        raise NotImplementedError()  # TODO

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def __setitem__(self, key: str, value: t.Any) -> None:
        raise NotImplementedError()  # TODO


class ManagedPropertyValueGroups(_PVMTBase, cabc.Mapping):
    """Provides a view onto the PVMT groups in a specific domain."""

    @classmethod
    def from_model(
        cls: type[_C],
        model: capellambse.MelodyModel,
        element: etree._Element,
        *,
        domain: str | None = None,
    ) -> _C:
        self = super().from_model(model, element)  # type: ignore[misc]
        self._domain = domain
        return self

    def __getitem__(self, key: str) -> t.Any:
        raise NotImplementedError()  # TODO

    def __iter__(self) -> cabc.Iterator[str]:
        raise NotImplementedError()  # TODO

    def __len__(self) -> int:
        return sum(1 for _ in self)


class ManagedPropertyValueDomain(_PVMTBase):
    """Provides a view onto a specific PVMT domain on a model object."""

    groups = c.AlternateAccessor(ManagedPropertyValueGroups)


class ManagedPropertyValueDomains(_PVMTBase, cabc.Mapping):
    """Provides a view onto the PVMT domains that can apply to an object.

    This class behaves like a dictionary, where the keys are the domain
    names, and the values are objects that provide a view into the
    specific domain and all of its groups.
    """

    def __getitem__(self, key: str) -> t.Any:
        raise NotImplementedError()  # TODO

    def __iter__(self) -> cabc.Iterator[str]:
        raise NotImplementedError()  # TODO

    def __len__(self) -> int:
        return sum(1 for _ in self)


class ObjectPVMT(_PVMTBase):
    """Provides access to managed property values on an element.

    Managed property values can be accessed in different ways.

    1. The simplest way is to treat the 'pvmt' attribute like a
       dictionary, and assign and retrieve property values directly with
       subscripting syntax. To do this, provide the "path" to the
       property value as 'domain.group.property', like this:

       >>> obj = model.by_uuid("08e02248-504d-4ed8-a295-c7682a614f66")
       >>> obj.pvmt["DarkMagic.Power.Max"]
       1600
       >>> obj.pvmt["DarkMagic.Power.Max"] = 2000
       >>> obj.pvmt["DarkMagic.Power.Max"]
       2000

    2. It's also possible to retrieve a managed group with the same
       syntax, by omitting the 'property' part of the path. The
       resulting object can be used like a dictionary to access the
       property values.

       >>> power = obj.pvmt["DarkMagic.Power"]
       >>> power["Max"]
       2000

    3. Both of the above approaches are simple to use, but also have
       some shortcomings. For example, it is not possible to determine
       whether a property value group has been "applied" to an object.

       These more advanced features are available through the "virtual"
       model objects provided through 'obj.pvmt.domains'.

       >>> obj.pvmt.domains
       <ManagedPropertyValueDomains ...>  # TODO

       For detailed information on how to use this API, refer to the
       detailed documentation of the relevant objects:

       - :class:`~capellambse.extensions.pvmt.ManagedPropertyValueDomains`
       - :class:`~capellambse.extensions.pvmt.ManagedPropertyValueGroups`

    Notes
    -----
    Managed property values are only available if the model has the
    Property Value Management viewpoint installed.
    """

    domains = c.AlternateAccessor(ManagedPropertyValueDomains)
    groups = c.AlternateAccessor(ManagedPropertyValueGroups)

    def __getitem__(self, key: str) -> t.Any:
        path = key.split(".")
        if not 2 <= len(path) <= 3:
            raise ValueError("Provide name as 'dom.group' or 'dom.group.prop'")

        domain = self.domains[path[0]]
        group = domain.groups[path[1]]
        if len(path) < 3:
            return group
        return group.properties[path[2]]

    def __setitem__(self, key: str, value: t.Any) -> None:
        path = key.split(".")
        if len(path) != 3:
            raise ValueError("Specify property to set as 'domain.group.prop'")
        dom, group, prop = path
        self.domains[dom].groups[group].properties[prop] = value

    def __repr__(self) -> str:
        return f"<Property Value Management for {self._element}>"

    def __html__(self) -> markupsafe.Markup:
        owner = self.owner._short_html_()
        header = "<h1>Property Value Management <small>for {}</small></h1>"
        fragments: list[str] = [
            markupsafe.Markup(header).format(owner),
        ]
        if self.domains:
            fragments.append("<p>Domains:</p><ul>")
            fragments.extend(
                f"<li>{markupsafe.escape(i.name)}</li>" for i in self.domains
            )
            fragments.append("</ul>")
        else:
            fragments.append("<p><em>No applicable domains found</em></p>")

        return markupsafe.Markup("".join(fragments))

    def _repr_html_(self) -> str:
        return self.__html__()
