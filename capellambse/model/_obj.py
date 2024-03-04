# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Infrastructure for representing model objects."""
from __future__ import annotations

__all__ = [
    # Model object types
    "Alien",
    "ModelElement",
    # Plain-old-data descriptors
    "AbstractPOD",
    "BoolPOD",
    "DateTimePOD",
    "EnumPOD",
    "FloatPOD",
    "IntPOD",
    "StringPOD",
    # Model object relationship descriptors
    "Allocation",
    "Association",
    "Backref",
    "Containment",
    "RelationshipDescriptor",
    "Single",
    "Shortcut",
    "TypeFilter",
    # Exceptions and utilities
    "BrokenModelError",
    "CORE_VIEWPOINT",
    "ElementList",
    "MissingValueError",
    "Namespace",
    "RefList",
    "add_descriptor",
    "new_object",
    "reset_entrypoint_caches",
]

import abc
import collections
import collections.abc as cabc
import dataclasses
import datetime
import functools
import importlib
import importlib.metadata as imm
import inspect
import itertools
import logging
import math
import operator
import pathlib
import re
import textwrap
import typing as t
import uuid as uuidlib
import warnings
import weakref

import awesomeversion as av
import markupsafe
import typing_extensions as te
from lxml import etree

from capellambse import helpers

if t.TYPE_CHECKING:
    import enum
    import os

    import capellambse.metamodel as M

    from . import _meta
    from . import _model as _modelmod

_E = t.TypeVar("_E", bound="enum.Enum | enum.Flag")
_O = t.TypeVar("_O", bound="ModelElement")
_O_co = t.TypeVar("_O_co", bound="ModelElement", covariant=True)
_T = t.TypeVar("_T")
_T_co = t.TypeVar("_T_co", covariant=True)

RE_VERSION = re.compile(r"[0-9]+(\.[0-9]+)*")
LOGGER = logging.getLogger(__name__)
CORE_VIEWPOINT = "org.polarsys.capella.core.viewpoint"

_NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"


class MissingValueError(AttributeError):
    """Raised when a non-required Single value is absent."""


class MissingClassError(KeyError):
    """Raised when a class is not found in a namespace."""

    def __init__(
        self,
        ns: Namespace,
        nsver: av.AwesomeVersion | str | None,
        clsname: str,
    ) -> None:
        if isinstance(nsver, str):
            nsver = av.AwesomeVersion(nsver)
        super().__init__(ns, nsver, clsname)

    @property
    def namespace(self) -> Namespace:
        """The namespace that was searched."""
        return self.args[0]

    @property
    def ns_version(self) -> av.AwesomeVersion | None:
        """The namespace version, if the namespace is versioned."""
        return self.args[1]

    @property
    def clsname(self) -> str:
        """The class name that was searched for."""
        return self.args[2]

    def __str__(self) -> str:
        if self.ns_version:
            return (
                f"No class {self.clsname!r} in v{self.ns_version} of"
                f" namespace {self.namespace.uri!r}"
            )
        return f"No class {self.clsname!r} in namespace {self.namespace.uri!r}"


UnresolvedClassName: te.TypeAlias = "tuple[str | Namespace, str]"
"""A tuple of namespace URI and class name.

The special value ``("", "")`` can be used as a wildcard descriptor
argument, to specify that any class is allowed inside this descriptor.
When resolving, it will be replaced by the
:class:`~capellambse.metamodel.modellingcore.ModelElement` class.
"""

ClassName: te.TypeAlias = "tuple[Namespace, str]"
"""A tuple of Namespace object and class name."""


class ResourceName(t.NamedTuple):
    resource_label: str
    """The resource label."""
    filename: pathlib.PurePosixPath
    """Filename of the fragment within the resource."""


ResourceNameIsh: te.TypeAlias = "tuple[str, str | os.PathLike]"
if t.TYPE_CHECKING:  # static assertion
    __rn: ResourceNameIsh = ResourceName("", pathlib.PurePosixPath("."))


@dataclasses.dataclass(init=False, frozen=True)
class Namespace:
    """The interface between the model and a namespace containing classes.

    Instances of this class represent the different namespaces used to
    organize types of Capella model objects. They are also the entry
    point into the namespace when a loaded model has to interact with
    it, e.g. for looking up a class to load or create.

    For a more higher-level overview of the interactions, and how to
    make use of this and related classes, read the documentation on
    `Extending the metamodel <_model-extensions>`__.

    Parameters
    ----------
    uri
        The URI of the namespace. This is used to identify the
        namespace in the XML files. It usually looks like a URL, but
        does not have to be one.
    alias
        The preferred alias of the namespace. This is the type name
        prefix used in an XML file.

        If the preferred alias is not available because another
        namespace already uses it, a numeric suffix will be appended
        to the alias to make it unique.
    maxver
        The maximum version of the namespace that is supported by this
        implementation. If a model uses a higher version, it cannot be
        loaded and an exception will be raised.
    """

    uri: str
    alias: str
    viewpoint: str | None
    maxver: av.AwesomeVersion | None

    def __init__(
        self,
        uri: str,
        alias: str,
        viewpoint: str | None = None,
        maxver: str | None = None,
    ) -> None:
        object.__setattr__(self, "uri", uri)
        object.__setattr__(self, "alias", alias)
        object.__setattr__(self, "viewpoint", viewpoint)

        is_versioned = "{VERSION}" in uri
        if is_versioned and maxver is None:
            raise TypeError(
                "Versioned namespaces must declare their supported 'maxver'"
            )
        if not is_versioned and maxver is not None:
            raise TypeError(
                "Unversioned namespaces cannot declare a supported 'maxver'"
            )

        if maxver is not None:
            maxver = av.AwesomeVersion(maxver)
            object.__setattr__(self, "maxver", maxver)
        else:
            object.__setattr__(self, "maxver", None)

        clstuple: te.TypeAlias = """tuple[
            type[ModelElement],
            av.AwesomeVersion,
            av.AwesomeVersion | None,
        ]"""
        self._classes: dict[str, list[clstuple]]
        object.__setattr__(self, "_classes", collections.defaultdict(list))

    def get_class(
        self, clsname: str, version: str | None = None
    ) -> type[ModelElement]:
        if "{VERSION}" in self.uri and not version:
            raise TypeError(
                f"Versioned namespace, but no version requested: {self.uri}"
            )

        classes = self._classes.get(clsname)
        if not classes:
            raise MissingClassError(self, version, clsname)

        eligible: list[tuple[av.AwesomeVersion, type[ModelElement]]] = []
        for cls, minver, maxver in classes:
            if version and (version < minver or maxver and version > maxver):
                continue
            eligible.append((minver, cls))

        if not eligible:
            raise MissingClassError(self, version, clsname)
        eligible.sort(key=lambda i: i[0], reverse=True)
        return eligible[0][1]

    def register(
        self,
        cls: type[ModelElement],
        minver: str | None,
        maxver: str | None,
    ) -> None:
        classes = self._classes[cls.__name__]
        if minver is not None:
            minver = av.AwesomeVersion(minver)
        else:
            minver = av.AwesomeVersion(0)
        if maxver is not None:
            maxver = av.AwesomeVersion(maxver)
        classes.append((cls, minver, maxver))


NS = Namespace(
    "http://www.polarsys.org/capella/common/core/{VERSION}",
    "org.polarsys.capella.common.data.core",
    CORE_VIEWPOINT,
    "6.0.0",
)


class ElementList(cabc.MutableSequence[_O], t.Generic[_O]):
    """A list of model elements.

    Parameters
    ----------
    wrapped
        Another list to wrap. This list will be used as the underlying
        storage for this list, without copying.
    """

    def __init__(
        self,
        wrapped: cabc.MutableSequence[_O],
        mapkey: str | None = None,
        mapvalue: str | None = None,
    ) -> None:
        self.__wrapped = wrapped
        self.__mapkey = mapkey
        self.__mapvalue = mapvalue

    @property
    def is_coupled(self) -> bool:
        """True if modifying this list means modifying the model.

        ElementList instances that are not coupled do not necessarily
        reflect the current model state, as modifications are not
        automatically synchronized. Most notably, copies made with
        :meth:`copy` and lists that have been filtered with methods like
        ``by_name`` or ``exclude_names`` are no longer coupled.
        """
        return isinstance(self.__wrapped, ModelCoupler)

    def copy(self) -> ElementList[_O]:
        """Make a copy of this list.

        Lists copied this way are decoupled from the model, meaning that
        modifications to the copy will not be propagated to the model.
        """
        return ElementList(list(self.__wrapped))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, cabc.Sequence):
            return NotImplemented
        if isinstance(other, ElementList):
            return self.__wrapped == other.__wrapped
        return self.__wrapped == other

    def __delitem__(self, index: int | slice) -> None:
        del self.__wrapped[index]

    @t.overload
    def __getitem__(self, index: int) -> _O: ...

    @t.overload
    def __getitem__(self, index: slice) -> ElementList[_O]: ...

    @t.overload
    def __getitem__(self, index: str) -> t.Any: ...

    def __getitem__(self, index: int | slice | str) -> t.Any:
        if isinstance(index, slice):
            return ElementList(self.__wrapped[index])
        if isinstance(index, str):
            if self.__mapkey is None or self.__mapvalue is None:
                raise TypeError("This list cannot act like a mapping")
            for i in self:
                if getattr(i, self.__mapkey, None) == index:
                    return getattr(i, self.__mapvalue)
            raise KeyError(index)
        return self.__wrapped[index]

    @t.overload
    def __setitem__(self, index: int, value: _O) -> None: ...

    @t.overload
    def __setitem__(self, index: slice, value: cabc.Iterable[_O]) -> None: ...

    def __setitem__(self, index, value):
        self.__wrapped[index] = value

    def get(self, key: str, default: t.Any = None) -> t.Any:
        if not isinstance(key, str):
            raise TypeError("Mapping-like key indices must be strings")
        try:
            return self[key]
        except KeyError:
            return default

    def __iter__(self) -> cabc.Iterator[_O]:
        return iter(self.__wrapped)

    def __len__(self) -> int:
        return len(self.__wrapped)

    def insert(self, index: int, value: _O) -> None:
        self.__wrapped.insert(index, value)

    def __repr__(self) -> str:
        if not self:
            return "[]"

        items: list[str] = []
        for i, item in enumerate(self):
            if hasattr(item, "_short_repr_"):
                rv = item._short_repr_()
            else:
                rv = repr(item)
            r = rv.splitlines() or [""]
            prefix = f"[{i}] "
            r[0] = prefix + r[0]
            prefix = " " * len(prefix)
            r[1:] = [prefix + l for l in r[1:]]
            items.append("\n".join(r))
        return "\n".join(items)

    def __html__(self) -> markupsafe.Markup:
        if not self:
            return markupsafe.Markup("<p><em>(Empty list)</em></p>")

        fragments = ['<ol start="0" style="text-align: left;">']
        for i in self:
            fragments.append(f"<li>{i._short_html_()}</li>")
        fragments.append("</ol>")
        return markupsafe.Markup("".join(fragments))

    def _repr_html_(self) -> str:
        return self.__html__()

    def __getattr__(self, attr: str) -> _ListFilter[_O]:
        if attr.startswith("by_"):
            attr = attr[3:]
            return _ListFilter(self, attr)

        if attr.startswith("exclude_") and attr.endswith("s"):
            attr = attr[8:-1]
            return _ListFilter(self, attr, inverted=True)

        raise AttributeError(f"ElementList has no attribute {attr!r}")


class ModelCoupler(cabc.MutableSequence[_O], t.Generic[_O]):
    """A list of model element coupled to the model.

    Modifications to this list (specifically insertions and deletions)
    will be advertised to the associated :class:~_modelmod.Model`, which
    may result in simultaneous updates to different model objects. This
    behavior is used to make newly created objects known to the model's
    internal indices for quick lookup, and to automatically purge stale
    references when objects are deleted.

    This list is not intended to be used directly, but as underlying
    storage for :class:`ElementList` instances.
    """

    def __init__(
        self, model: _modelmod.Model, initial_objects: cabc.Iterable[_O] = ()
    ) -> None:
        self.__model = model
        self.__container = list(initial_objects)

    def __len__(self) -> int:
        return len(self.__container)

    @t.overload
    def __getitem__(self, index: int, /) -> _O: ...

    @t.overload
    def __getitem__(self, index: slice, /) -> list[_O]: ...

    def __getitem__(self, index: int | slice, /) -> _O | list[_O]:
        return self.__container[index]

    def __delitem__(self, index: int | slice) -> None:
        if isinstance(index, int):
            items: cabc.Sequence[_O] = [self[index]]
        else:
            items = self[index]
        for i in items:
            self.__model._unregister(i)

        del self.__container[index]

    @t.overload
    def __setitem__(self, index: int, value: _O) -> None: ...

    @t.overload
    def __setitem__(self, index: slice, value: cabc.Iterable[_O]) -> None: ...

    def __setitem__(self, index, value):
        if isinstance(index, int):
            items: cabc.Sequence[_O] = [self[index]]
        else:
            items = self[index]
        for i in items:
            self.__model._unregister(i)

        value = list(value)
        for i in value:
            self.__model._register(i)

        self.__container[index] = value

    def insert(self, index: int, value: _O) -> None:
        self.__model._register(value)
        self.__container.insert(index, value)


class RefList(t.Generic[_O]):
    """A list of references to other model objects.

    This list automatically removes references to elements that are
    deleted from the model.
    """

    def __init__(
        self,
        model: _modelmod.Model,
        initial_objects: cabc.Iterable[ModelElement] = (),
        /,
    ) -> None:
        self.__model = model
        self.__container: list[weakref.ref[ModelElement]] = []
        self.extend(initial_objects)

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def __iter__(self) -> cabc.Iterator[ModelElement]:
        """Iterate over the contained objects.

        This method will yield strong references to those contained
        objects that are still alive.
        """
        for i in self.__container:
            strong_i = i()
            if strong_i is not None:
                yield strong_i

    def __reversed__(self) -> cabc.Iterator[ModelElement]:
        """Iterate over the contained objects in reverse order.

        This method will yield strong references to those contained
        objects that are still alive.
        """
        for i in reversed(self.__container):
            strong_i = i()
            if strong_i is not None:
                yield strong_i

    def __getitem__(self, index: int) -> ModelElement:
        """Get the object at the given index."""
        if index >= 0:
            it = iter(self)
        else:
            it = reversed(self)
            index = -index

        try:
            for _ in range(index):
                next(it)
            return next(it)
        except StopIteration:
            raise IndexError(index) from None

    def __delitem__(self, index: int) -> None:
        """Delete the object at the given index."""
        container = [
            strong
            for weak in self.__container
            if (strong := weak()) is not None
        ]
        del container[index]
        self.__container = [weakref.ref(i) for i in container]

    def append(self, obj: ModelElement) -> None:
        """Append an object to the list."""
        assert obj.uuid not in self.__container
        self.__container.append(weakref.ref(obj))

    def extend(self, objs: cabc.Iterable[ModelElement]) -> None:
        """Extend the list with the given objects."""
        for obj in objs:
            self.append(obj)

    def delete(self, obj: ModelElement) -> None:
        """Delete an object from the list."""
        self.__container.remove(weakref.ref(obj))


class _ListFilter(cabc.Iterable[t.Any], t.Generic[_O]):
    """Filters a list based on a set of expected values.

    Parameters
    ----------
    parent
        The ElementList to operate on.
    attr
        The attribute on list members to filter on.
    inverted
        If set to True, inverts the matching logic, i.e. only
        elements where the attribute does not match the given value
        will be returned.
    """

    __slots__ = ("_attr", "_inverted", "_parent", "_single")

    def __init__(
        self,
        parent: ElementList[_O],
        attr: str,
        *,
        inverted: bool = False,
    ) -> None:
        self._parent = parent
        self._attr = attr
        self._inverted = inverted

    @t.overload
    def __call__(self, *values: t.Any, single: t.Literal[True]) -> _O: ...

    @t.overload
    def __call__(
        self, *values: t.Any, single: t.Literal[False]
    ) -> ElementList[_O]: ...

    def __call__(
        self, *v: t.Any, single: bool | None = None
    ) -> _O | ElementList[_O]:
        if single is None:
            single = self._attr.rsplit(".", 1)[-1] in {"id", "name"}

        try:
            values: t.Container[t.Any] = set(v)
        except TypeError:
            values = v

        getter = operator.attrgetter(self._attr)
        matches: list[_O] = []
        for i in self._parent:
            try:
                value = getter(i)
            except (AttributeError, MissingValueError):
                continue
            if (value in values) ^ self._inverted:
                matches.append(i)

        if not single:
            return ElementList(matches)
        if len(matches) > 1:
            value = v[0] if len(v) == 1 else v
            raise KeyError(f"Multiple matches for {value!r}")
        if len(matches) == 0:
            raise KeyError(v[0] if len(v) == 1 else v)
        return matches[0]

    def __iter__(self) -> cabc.Iterator[t.Any]:
        """Yield values that result in a non-empty list when filtered for.

        The returned iterator yields all values that, when given to
        :meth:`__call__`, will result in a non-empty list being
        returned. Consequently, if the original list was empty, this
        iterator will yield no values.

        The order in which the values are yielded is undefined.
        """
        yielded: list[t.Any] = []
        extract = operator.attrgetter(self._attr)
        for elm in self._parent:
            try:
                key = extract(elm)
            except (AttributeError, MissingValueError):
                continue
            if key not in yielded:
                yielded.append(key)
                yield key

    def __getattr__(self, attr: str) -> _ListFilter[_O]:
        if not attr or attr.startswith("_"):
            raise AttributeError(
                f"Invalid filter attribute name: {self._attr}.{attr}"
            )
        return type(self)(
            self._parent,
            f"{self._attr}.{attr}",
            inverted=self._inverted,
        )


class InvalidModificationError(RuntimeError):
    """Raised when a modification would result in an invalid model."""


class BrokenModelError(ValueError):
    """Raised when a model is in an invalid state."""


@t.runtime_checkable
class _Descriptor(t.Generic[_T_co], t.Protocol):
    @t.overload
    def __get__(self, obj: None, objtype: type[ModelElement]) -> te.Self: ...

    @t.overload
    def __get__(
        self, obj: ModelElement, objtype: type[ModelElement]
    ) -> _T_co: ...


class _AbstractDescriptor(abc.ABC, t.Generic[_T_co]):
    __doc__: str | None
    __name__: str
    __objclass__: type[ModelElement]
    _required: bool = False

    @property
    def _qualname(self) -> str:
        """Generate the fully qualified name of this descriptor."""
        if not hasattr(self, "__objclass__"):  # pragma: no cover
            return f"(unknown {type(self).__name__} - call __set_name__)"
        module = self.__objclass__.__module__
        clsname = self.__objclass__.__name__
        return f"{module}:{clsname}.{self.__name__}"

    @abc.abstractmethod
    def __get__(self, obj, objtype) -> te.Self | _T_co: ...

    def __set__(self, obj, value) -> None:
        raise TypeError("Setting attributes is not supported yet")

    def __delete__(self, obj) -> None:
        raise TypeError("Deleting attributes is not supported yet")

    def __set_name__(self, owner: type[ModelElement], name: str) -> None:
        """Set the name and owner of the descriptor."""
        self.__name__ = name
        self.__objclass__ = owner
        if not self.__doc__:
            self.__doc__ = f"The {name} of {owner.__name__} model objects."
            if self._required:
                self.__doc__ += " Required."

    def from_xml(
        self,
        obj: ModelElement,
        elem: etree._Element,
        lazy_attributes: cabc.MutableSet[tuple[str, str]],
    ) -> None:
        """Load the data from the XML element into the model object.

        This method must consume all XML elements and attributes that it
        handled. Elements and attributes that it did not handle must be
        left in the element tree.

        Parameters
        ----------
        obj
            The model object to load the data into.
        elem
            The XML element to load the data from.
        lazy_attributes
            A set of ``(uuid, attrname)`` tuples of attributes that
            should be loaded lazily. The descriptor should add itself to
            this set if it needs to be loaded lazily.
        """

    def to_xml(
        self,
        obj: ModelElement,
        elem: etree._Element,
        namespaces: cabc.MutableMapping[str, str],
    ) -> None:
        """Insert the data from the model object into the XML element.

        Parameters
        ----------
        obj
            The model object to serialize.
        elem
            The XML element to insert the data into.
        namespaces
            A mapping from namespaces to their aliases, i.e. the inverse
            of ``etree._Element.nsmap``.

            If a namespace is needed that is not yet part of this
            mapping, it will be added by modifying the mapping in place.
        """

    def resolve(self, obj: ModelElement) -> None:  # pragma: no cover
        """Resolve forward references on the model object.

        This method is called after all model objects have been
        instantiated, if a descriptor registered itself in the
        ``lazy_attributes`` set during :meth:`from_xml`.
        """


class RelationshipDescriptor(_AbstractDescriptor[_O_co], t.Generic[_O_co]):
    @t.overload
    def __get__(self, obj: None, _: t.Any) -> te.Self: ...

    @t.overload
    def __get__(self, obj: ModelElement, _: t.Any) -> ElementList[_O_co]: ...

    @abc.abstractmethod
    def __get__(
        self, obj: ModelElement | None, _: t.Any
    ) -> te.Self | ElementList[_O_co]: ...

    def __set__(
        self, obj: ModelElement, value: cabc.Iterable[_O_co]
    ) -> None: ...

    @abc.abstractmethod
    def from_xml(
        self,
        obj: ModelElement,
        elem: etree._Element,
        lazy_attributes: cabc.MutableSet[tuple[str, str]],
    ) -> None: ...

    @abc.abstractmethod
    def to_xml(
        self,
        obj: ModelElement,
        elem: etree._Element,
        namespaces: cabc.MutableMapping[str, str],
    ) -> None: ...


class Containment(RelationshipDescriptor[_O_co]):
    """A containment relation between model elements.

    When loading, this descriptor will take ownership of all XML
    elements with the given tag, and create model objects from them. The
    ``classes`` argument specifies which model classes are allowed to be
    created. If the XML calls for a class that is not in this list, a
    :exc:`BrokenModelError` will be raised.

    Parameters
    ----------
    tag
        The XML tag to use for storing and loading.
    classes
        The classes that are allowed to be created.
    """

    def __init__(self, tag: str, /, *classes: UnresolvedClassName) -> None:
        """Create a new containment descriptor."""
        if not classes:
            raise TypeError("No valid target class specified")

        self._tag = tag
        self._cls = _resolve_class_names(*classes)
        self._key = ("cont", tag)

    @t.overload
    def __get__(self, obj: None, _: t.Any) -> te.Self: ...

    @t.overload
    def __get__(self, obj: ModelElement, _: t.Any) -> ElementList[_O_co]: ...

    def __get__(self, obj, _) -> te.Self | ElementList[_O_co]:
        """Get the contained objects."""
        if obj is None:
            return self

        data = obj.__dict__.setdefault("__modeldata", {})
        if self._key not in data:
            data[self._key] = ElementList(ModelCoupler(obj._model))
        return data[self._key]

    def from_xml(
        self,
        obj: ModelElement,
        elem: etree._Element,
        lazy_attributes: cabc.MutableSet[tuple[str, str]],
    ) -> None:
        objs: list[ModelElement] = []
        classes = tuple(
            find_class(*_resolve_class(i, obj._model)) for i in self._cls
        )
        for c in elem.getchildren():
            if c.tag != self._tag:
                continue

            objtype = find_objtype(c)
            objclass = find_class(objtype[0], objtype[1])
            if not issubclass(objclass, (Alien, classes)):
                raise BrokenModelError(
                    f"Unexpected xsi:type for {self._qualname} on {obj.uuid}:"
                    f" {objtype[1]} @ {objtype[0]}"
                )
            parsed = t.cast(_O_co, load_object(obj._model, c, lazy_attributes))
            parsed.parent = obj
            objs.append(parsed)
            elem.remove(c)
        data = obj.__dict__.setdefault("__modeldata", {})
        data[self._key] = ElementList(ModelCoupler(obj._model, objs))

    def to_xml(
        self,
        obj: ModelElement,
        elem: etree._Element,
        namespaces: cabc.MutableMapping[str, str],
    ) -> None:
        objs: list[ModelElement] = getattr(obj, self.__name__)
        for i in objs:
            child = i._to_xml(namespaces=namespaces)
            child.attrib[f"{{{_NS_XSI}}}type"] = child.tag
            child.tag = self._tag


class Association(RelationshipDescriptor[_O_co]):
    """An association with one or more other model elements.

    In the XML, associations are stored as attributes containing a
    space-separated list of UUID references. This descriptor takes
    ownership of the attribute named ``attr``.

    Parameters
    ----------
    attr
        The name of the attribute to use for storing and loading.
    classes
        The classes that are allowed to be referenced.
    """

    def __init__(self, attr: str, /, *classes: UnresolvedClassName) -> None:
        if not classes:
            raise TypeError("No valid target class specified")

        self._attr = attr
        self._cls = _resolve_class_names(*classes)
        self._key = ("assoc", attr)

    @t.overload
    def __get__(self, obj: None, _: t.Any) -> te.Self: ...

    @t.overload
    def __get__(self, obj: ModelElement, _: t.Any) -> ElementList[_O_co]: ...

    def __get__(self, obj, _) -> te.Self | ElementList[_O_co]:
        """Retrieve the associated objects."""
        if obj is None:
            return self

        data = obj.__dict__.setdefault("__modeldata", {})
        refs = data.setdefault(self._key, RefList(obj._model))
        return ElementList(refs)

    def from_xml(
        self,
        obj: ModelElement,
        elem: etree._Element,
        lazy_attributes: cabc.MutableSet[tuple[str, str]],
    ) -> None:
        refs = elem.attrib.pop(self._attr, "")
        data = obj.__dict__.setdefault("__modeldata", {})
        data[self._key] = list(helpers.split_links(refs))
        lazy_attributes.add((obj.uuid, self.__name__))

    def to_xml(self, *args, **kw):
        raise NotImplementedError()

    def resolve(self, obj: ModelElement) -> None:
        data = obj.__dict__["__modeldata"]
        refs = data.pop(self._key)

        classes = tuple(
            find_class(*_resolve_class(i, obj._model)) for i in self._cls
        )

        data[self._key] = objs = RefList[ModelElement](obj._model)
        for ref in refs:
            target = obj._model.follow(obj, ref)
            if not isinstance(target, (Alien, classes)):
                expected_names = ", ".join(i.__name__ for i in classes)
                raise BrokenModelError(
                    f"Invalid associated target in {self._qualname!r} on"
                    f" {obj.uuid}: Unexpected type {type(target).__name__},"
                    f" expected one of {expected_names} (or any subclass)"
                )
            objs.append(target)


class Allocation(RelationshipDescriptor[_O_co]):
    """An allocation of other model element(s).

    Allocations are links to other model elements, and are stored as
    child elements with a given tag, a specific ``xsi:type``, a unique
    ID, and a link to the target element.

    This descriptor takes ownership of all elements with a matching tag
    and ``xsi:type``.

    The descriptor can be used in two ways. Either a single allocation
    type is specified as the *alloctype*, and a set of allowed classes
    is then passed via the *classes* vararg. Alternatively, a mapping
    from allocation type to class can be passed as the *alloctype*, in
    which case the *classes* argument must not be specified.

    Parameters
    ----------
    alloctype
        The type of the allocation, in the same format used for
        specifying target types. Note however that there does not need
        to exist an actual class for this type.
    allocinfo
        Information about the allocation elements. This is a tuple with
        the XML tag name, the attribute name for the link, and (if
        needed) the attribute name for the backwards facing link.
    classes
        Allowed target classes for the allocation.
    """

    @t.overload
    def __init__(
        self,
        alloctype: UnresolvedClassName,
        allocinfo: tuple[str, str] | tuple[str, str, str],
        /,
        *classes: UnresolvedClassName,
    ) -> None: ...

    @t.overload
    def __init__(
        self,
        alloctype: cabc.Mapping[UnresolvedClassName, UnresolvedClassName],
        allocinfo: tuple[str, str] | tuple[str, str, str],
        /,
    ) -> None: ...

    def __init__(
        self,
        alloctype: (
            UnresolvedClassName
            | cabc.Mapping[UnresolvedClassName, UnresolvedClassName]
        ),
        allocinfo: tuple[str, str] | tuple[str, str, str],
        /,
        *classes: UnresolvedClassName,
    ) -> None:
        """Create a new allocation descriptor."""
        if classes and isinstance(alloctype, cabc.Mapping):
            raise TypeError(
                "Cannot use 'alloctype' mapping and 'classes' at the same time"
            )

        if isinstance(alloctype, cabc.Mapping):
            self._alloctype = {
                _resolve_class_names(k)[0]: _resolve_class_names(v)[0]
                for k, v in alloctype.items()
            }
        else:
            assert isinstance(alloctype, tuple)
            (at_resolved,) = _resolve_class_names(alloctype)
            self._alloctype = {
                at_resolved: i for i in _resolve_class_names(*classes)
            }

        if not isinstance(allocinfo, tuple) or not 2 <= len(allocinfo) <= 3:
            raise TypeError(
                f"Invalid allocinfo, expected a 2- or 3-tuple: {allocinfo!r}"
            )
        ai: t.Any = allocinfo
        if len(ai) == 2:
            self._tag, self._linkattr = ai
            self._backlink = None
        else:
            self._tag, self._linkattr, self._backlink = ai
        self._key = ("alloc", self._tag)

    @t.overload
    def __get__(self, obj: None, _: t.Any) -> te.Self: ...

    @t.overload
    def __get__(self, obj: ModelElement, _: t.Any) -> ElementList[_O_co]: ...

    def __get__(self, obj, _) -> te.Self | ElementList[_O_co]:
        """Retrieve the allocated objects."""
        if obj is None:
            return self

        data = obj.__dict__.setdefault("__modeldata", {})
        refs = data.setdefault(self._key, RefList(obj._model))
        return ElementList(refs)

    def from_xml(
        self,
        obj: ModelElement,
        elem: etree._Element,
        lazy_attributes: cabc.MutableSet[tuple[str, str]],
    ) -> None:
        links: list[tuple[str, tuple[str, str], str]] = []
        for c in elem.getchildren():
            if c.tag != self._tag:
                continue

            xtype = c.get(f"{{{_NS_XSI}}}type")
            if xtype is None:
                raise BrokenModelError("Missing xsi:type attribute on {c!r}")
            xns, xcls = xtype.split(":")
            xns = elem.nsmap[xns]

            try:
                linkid = c.attrib["id"]
                ref = c.attrib[self._linkattr]
            except KeyError as err:
                raise BrokenModelError(
                    f"Missing attribute on Allocation {c!r}: {err.args[0]}"
                    f" (required by {self._qualname})"
                ) from None

            links.append((linkid, (xns, xcls), ref))
            elem.remove(c)

        data = obj.__dict__.setdefault("__modeldata", {})
        data[self._key] = links
        lazy_attributes.add((obj.uuid, self.__name__))

    def to_xml(self, *args, **kw):
        raise NotImplementedError()

    def resolve(self, obj: ModelElement) -> None:
        data = obj.__dict__["__modeldata"]
        links: list[tuple[str, tuple[str, str], str]] = data.pop(self._key)

        classes = {
            _resolve_class(k, obj._model): find_class(
                *_resolve_class(v, obj._model)
            )
            for k, v in self._alloctype.items()
        }

        objs: list[ModelElement] = []
        for linkid, linkcls, ref in links:
            expected_type = classes.get(linkcls)
            if expected_type is None:
                raise BrokenModelError(
                    f"Unexpected allocation class on {linkid!r}:"
                    f" Got {linkcls!r}, expected one of {list(classes)!r}"
                )

            try:
                target = obj._model.follow(obj, ref)
            except KeyError:
                raise BrokenModelError(
                    f"Allocation target for {self._qualname} on {obj.uuid!r}"
                    f" not found: {ref}"
                ) from None
            if not isinstance(target, (Alien, *classes.values())):
                raise BrokenModelError(
                    f"Invalid allocation target for {self._qualname} on"
                    f" {obj.uuid!r}: Unexpected type {type(target).__name__},"
                    f" expected one of {classes}"
                )
            objs.append(target)

        data[self._key] = RefList(obj._model, objs)


class TypeFilter(RelationshipDescriptor[_O_co], t.Generic[_O_co]):
    """Filters another attribute for a specific type of object.

    Parameters
    ----------
    attr
        The attribute to filter.

        If None, filter the superclass attribute with the same name.
    cls
        The class to filter for.
    """

    def __init__(self, attr: str | None, cls: UnresolvedClassName) -> None:
        self._wrapped: t.Any | None = None
        self._attr_name = attr
        (self._cls,) = _resolve_class_names(cls)

    @t.overload
    def __get__(self, obj: None, _: t.Any) -> te.Self: ...

    @t.overload
    def __get__(self, obj: ModelElement, _: t.Any) -> ElementList[_O_co]: ...

    def __get__(
        self, obj: ModelElement | None, _: t.Any
    ) -> te.Self | ElementList[_O_co]:
        if obj is None:
            return self

        if self._wrapped is None:
            raise TypeError(
                f"{self!r} wasn't initialized properly,"
                f"make sure that __set_name__ is called"
            )

        try:
            unfiltered = self._wrapped.__get__(obj, type(obj))
        except MissingValueError:
            return ElementList([])
        if isinstance(unfiltered, ModelElement):
            unfiltered = [unfiltered]
        cls = find_class(*_resolve_class(self._cls, obj._model))
        if cls is Alien:
            return ElementList([])
        rv = ElementList([i for i in unfiltered if isinstance(i, cls)])
        return t.cast(ElementList[_O_co], rv)

    def __find_super(
        self, cls: type[ModelElement], attrname: str
    ) -> _Descriptor:
        for supercls in cls.__mro__[1:]:
            desc = getattr(supercls, attrname, None)
            if desc is None:
                continue
            if isinstance(desc, _Descriptor):
                return desc
            raise TypeError(
                f"Cannot filter attribute {cls.__module__}.{cls.__qualname__}"
                f" with non-descriptor type {type(desc).__name__}"
            )

        raise TypeError(
            f"No superclass of {cls.__module__}.{cls.__qualname__}"
            f" defines the attribute {attrname!r}"
        )

    def __set_name__(self, owner: type[ModelElement], name: str) -> None:
        """Set the name and owner of the descriptor."""
        if self._attr_name == name:
            raise TypeError(
                f"Cannot filter self ({owner.__name__}.{name}),"
                " did you mean to use None?"
            )
        elif self._attr_name:
            self._wrapped = getattr(owner, self._attr_name, None)
            if self._wrapped is None:
                raise TypeError(
                    f"Attribute {self._attr_name!r}"
                    f" not defined on {owner.__name__}"
                )
        else:
            self._wrapped = self.__find_super(owner, name)
        super().__set_name__(owner, name)

    def from_xml(
        self,
        obj: ModelElement,
        elem: etree._Element,
        lazy_attributes: cabc.MutableSet[tuple[str, str]],
    ) -> None:
        if self._wrapped is None:
            raise TypeError(
                f"{self!r} wasn't initialized properly,"
                f"make sure that __set_name__ is called"
            )

        if self._attr_name is None:
            self._wrapped.from_xml(obj, elem, lazy_attributes)

    def to_xml(
        self,
        obj: ModelElement,
        elem: etree._Element,
        namespaces: cabc.MutableMapping[str, str],
    ) -> None:
        raise NotImplementedError()

    def resolve(self, obj: ModelElement) -> None:
        if self._wrapped is None:
            raise TypeError(
                f"{self!r} wasn't initialized properly,"
                f"make sure that __set_name__ is called"
            )

        if self._attr_name is None:
            self._wrapped.resolve(obj)


class Backref(_AbstractDescriptor[_O_co], t.Generic[_O_co]):
    """A back-reference.

    Back-references are virtual relations. As such, they are not read
    from or written to the XML, but are maintained transiently in
    memory. This attribute is most commonly used to implement the
    reverse of :class:Association and :class:Allocation relations.

    Back-references search for any references to the "current" element
    (i.e. the element that the attribute is defined on) on a specified
    set of "reference sources". Consider the following set of classes:

    .. code:: python

        class SomeObj(capellacore.CapellaElement):
            refs = m.Backref( (NS, "Ref"), lookup="some" )

        class Ref(capellacore.CapellaElement):
            some = Association( "some", (NS, "SomeObj") )
            others = Association( "others", (NS, "SomeObj") )

    An instance of *SomeObj* in this example is the "current" element,
    and all instances of the *Ref* class that exist in the same model
    are reference sources, as listed in the *Backref* constructor. On
    the *Ref* instances, only the *some* attribute is looked at to
    determine if a reference should be considered for this *Backref*
    attribute. The *others* attribute, which can also refer to *SomeObj*
    instances, is ignored. In other words: An *SomeObj.refs* contains
    all *Ref* instances which contain that particular *SomeObj* in their
    own *some* attribute.

    You can also read it like this: "In *SomeObj.refs* give me all *Ref*
    instances where we are one of the *some*."

    Parameters
    ----------
    classes
        Model objects of these types are searched as "reference
        sources".
    lookup
        These attributes are inspected for whether they contain the
        "current" element.
    """

    def __init__(
        self,
        *classes: UnresolvedClassName,
        lookup: str | cabc.Iterable[str],
    ) -> None:
        """Create a new back-reference."""
        self._cls = classes
        if isinstance(lookup, str):
            self._lookup: tuple[str, ...] = (lookup,)
        else:
            self._lookup = tuple(lookup)

    def __get__(self, obj, objtype):
        if obj is None:
            return self

        warnings.warn("Backref is not implemented yet", RuntimeWarning)
        return ElementList([])


class Shortcut(_AbstractDescriptor[_O_co], t.Generic[_O_co]):
    """A shortcut to another model element.

    This class does not represent a physical model element or relation,
    but is used to implement more convenient access to other model
    elements. It is used as a descriptor on model objects.

    The path specification is based on Python-esque dotted name
    notation, but with some slight differences in behavior.

    As normal, each path segment represents accessing a nested
    attribute by default.

    If the path segment can be interpreted as an integer number, it is
    used with ``__getitem__`` (subscripting) instead of ``__getattr__``.

    If a path segment is empty (i.e. nothing between two dots), it means
    to retrieve the first list item (using ``x[0]``), and to also make
    sure that there are no other items in the same list.

    If the last segment should be empty (i.e. you would use a trailing
    dot), use :class:`Shortcut1` instead.

    Parameters
    ----------
    path
        The path to take.
    """

    def __init__(self, path: str):
        """Create a shortcut."""
        if path.endswith("."):
            raise TypeError("Path cannot end with '.'")
        self._path = path.split(".")

    def __get__(self, obj, objtype):
        if obj is None:
            return self

        origin = obj.uuid
        for i, path in enumerate(self._path, start=1):
            if not path:
                if len(obj) != 1:
                    raise BrokenModelError(
                        f"Shortcut {self._qualname!r} on {origin!r} is broken"
                        f" at step {i}: Expected one member, found {len(obj)}"
                    )
                else:
                    obj = obj[0]
                    continue

            try:
                idx = int(path)
            except ValueError:
                try:
                    obj = getattr(obj, path)
                except MissingValueError:
                    obj = ElementList([])
            else:
                try:
                    obj = obj[idx]
                except KeyError:
                    raise BrokenModelError(
                        f"Shortcut {self._qualname!r} on {origin!r} is broken"
                        f" at step {i}: Wanted index {idx} not found"
                    ) from None
        return obj


class Single(_AbstractDescriptor[_O_co], t.Generic[_O_co]):
    """A descriptor wrapper that ensures there is exactly one value.

    This descriptor is used to wrap other descriptors that return
    multiple values, such as :class:`Containment`, :class:`TypeFilter`
    or :class:`Shortcut`. It ensures that the wrapped descriptor returns
    at most one value, and raises a :class:`BrokenModelError` if it
    returns more than one.

    When setting the attribute, the new value will always overwrite the
    old one, if any.

    Getting the attribute will either return the single value if there
    is one, or raise an :class:`AttributeError` if there is none.

    Parameters
    ----------
    wrapped
        The descriptor to wrap. This descriptor must return a list (i.e.
        it is not possible to nest *Single* descriptors). The instance
        passed here should also not be used anywhere else.
    enforce
        How strictly to enforce that there is exactly one value.

        - *no*: Do not enforce anything. Return the first element if
          there is at least one, otherwise raise an
          :class:`AttributeError`.
        - *min*: Enforce that there is **at least one** value. Return
          the first element. The model cannot be loaded if the list is
          empty.
        - *max*: Enforce that there is **at most one** value. Raise an
          :class:`AttributeError` if the list was empty. The model
          cannot be loaded if the list contains more than one element.
        - *exact*: Enforce that there is **exactly one** value. The
          model cannot be loaded in any other case.

        Deleting the attribute using :func:`delattr` or the ``del``
        keyword is only allowed for the *no* and *max* enforcing modes.

        ``True`` and ``False`` are equal to ``exact`` and ``no``,
        respectively.

    Examples
    --------
    >>> class Foo(capellacore.CapellaElement):
    ...     bar = Single(Containment["Bar"]("bar", (NS, "Bar")))
    """

    def __init__(
        self,
        wrapped: _AbstractDescriptor[_O_co],
        enforce: bool | t.Literal["no", "min", "max", "exact"] = True,
    ) -> None:
        """Create a new single-value descriptor."""
        self._wrapped = wrapped
        if enforce is True:
            self._enforcement_level = "exact"
        elif enforce is False:
            self._enforcement_level = "no"
        else:
            self._enforcement_level = enforce

    @t.overload
    def __get__(self, obj: None, _: t.Any) -> te.Self: ...

    @t.overload
    def __get__(self, obj: ModelElement, _: t.Any) -> _O_co: ...

    def __get__(self, obj: ModelElement | None, _: t.Any) -> te.Self | _O_co:
        """Retrieve the value of the attribute."""
        if obj is None:
            return self

        nested = self._get_wrapped(obj)
        if nested is None:
            raise MissingValueError(
                f"No value for {self.__name__!r}"
                f" on {type(obj).__name__} {obj.uuid!r}"
            )
        return nested

    def __set__(self, obj: ModelElement, value: _O_co) -> None:
        """Set the value of the attribute."""
        self._wrapped.__set__(obj, [value])

    def __delete__(self, obj: ModelElement) -> None:
        """Delete the attribute."""
        if self._enforcement_level in ("min", "exact"):
            raise AttributeError(
                f"Cannot delete required attribute {self.__name__!r}"
            )
        self._wrapped.__delete__(obj)

    def __set_name__(self, owner: type[ModelElement], name: str) -> None:
        """Set the name and owner of the descriptor."""
        self._wrapped.__set_name__(owner, name)
        super().__set_name__(owner, name)

    def _get_wrapped(self, obj: ModelElement) -> ModelElement | None:
        try:
            # pylint: disable-next=unnecessary-dunder-call
            objs: t.Any = self._wrapped.__get__(obj, type(obj))
        except MissingValueError:
            objs = ElementList([])

        if isinstance(objs, ModelElement):
            objs = ElementList([objs])
        elif not isinstance(objs, ElementList):
            raise TypeError(
                f"Wrapped descriptor {self._wrapped!r}"
                " did not return an object or list of objects"
            )

        if self._enforcement_level in ("min", "exact") and len(objs) < 1:
            raise BrokenModelError(
                f"Invalid empty list for {self._qualname!r}"
                f" on {type(obj).__name__} {obj.uuid!r}"
            )
        if self._enforcement_level in ("max", "exact") and len(objs) > 1:
            raise BrokenModelError(
                f"Invalid list of length {len(objs)} for {self._qualname!r}"
                f" on {obj.uuid!r}, expected at most one element"
            )

        if len(objs) < 1:
            return None
        return objs[0]

    def from_xml(
        self,
        obj: ModelElement,
        elem: etree._Element,
        lazy_attributes: cabc.MutableSet[tuple[str, str]],
    ) -> None:
        self._wrapped.from_xml(obj, elem, lazy_attributes)
        lazy_attributes.add((obj.uuid, self.__name__))

    def to_xml(
        self,
        obj: ModelElement,
        elem: etree._Element,
        namespaces: cabc.MutableMapping[str, str],
    ) -> None:
        self._wrapped.to_xml(obj, elem, namespaces)

    def resolve(self, obj: ModelElement) -> None:
        self._wrapped.resolve(obj)
        if isinstance(self._wrapped, Backref):
            warnings.warn("Not verifying Backref for being a Single")
            return

        self._get_wrapped(obj)


class AbstractPOD(_AbstractDescriptor, t.Generic[_T]):
    """Plain old data on a model object."""

    def __init__(
        self, name: str, default: _T | None, required: bool, writable: bool
    ):
        self._xmlname = name
        self._default = default
        self._writable = writable
        self._required = required
        self._key = ("pod", name)

    @t.overload
    def __get__(self, obj: None, _: t.Any) -> te.Self: ...

    @t.overload
    def __get__(self, obj: ModelElement, _: t.Any) -> _T: ...

    def __get__(self, obj, _) -> te.Self | _T:
        """Retrieve the value of the attribute."""
        if obj is None:
            return self

        modeldata = obj.__dict__.setdefault("__modeldata", {})
        return modeldata.get(self._key, self._default)

    def __set__(self, obj: ModelElement, value: _T) -> None:
        """Set the value of the attribute."""
        if not self._required and value == self._default:
            self.__delete__(obj)
            return

        modeldata = obj.__dict__.setdefault("__modeldata", {})
        if not self._writable and self._key in modeldata:
            raise AttributeError(
                "Cannot set read-only attribute {self.__name__!r}"
            )
        modeldata[self._key] = value

    def __delete__(self, obj):
        """Delete the attribute."""
        if self._required:
            raise AttributeError(
                "Cannot delete required attribute {self.__name__!r}"
            )

        modeldata = obj.__dict__.setdefault("__modeldata", {})
        if not self._writable and self._key in modeldata:
            raise AttributeError(
                "Cannot delete read-only attribute {self.__name__!r}"
            )
        modeldata.pop(self._key, None)

    def from_xml(
        self,
        obj: ModelElement,
        elem: etree._Element,
        lazy_attributes: cabc.MutableSet[tuple[str, str]],
    ) -> None:
        """Load the data from the XML element into the model object.

        This method must consume all XML elements and attributes that it
        handled. Elements and attributes that it did not handle must be
        left in the element tree.

        Parameters
        ----------
        obj
            The model object to load the data into.
        elem
            The XML element to load the data from.
        lazy_attributes
            A set of ``(uuid, attrname)`` tuples of attributes that
            should be loaded lazily. The descriptor should add itself to
            this set if it needs to be loaded lazily.
        """
        del lazy_attributes

        if self._required:
            try:
                value = elem.attrib.pop(self._xmlname)
            except KeyError:
                raise BrokenModelError(
                    f"Missing required attribute {self._xmlname!r} on {elem!r}"
                ) from None
        else:
            value = elem.attrib.pop(self._xmlname, self._default)

        if value is not None:
            setattr(obj, self.__name__, self._data_from_xml(value))

    def to_xml(
        self,
        obj: ModelElement,
        elem: etree._Element,
        namespaces: cabc.MutableMapping[str, str],
    ) -> None:
        """Insert the data from the model object into the XML element.

        Parameters
        ----------
        obj
            The model object to serialize.
        elem
            The XML element to insert the data into.
        namespaces
            A mapping from namespaces to their aliases, i.e. the inverse
            of ``etree._Element.nsmap``.

            If a namespace is needed that is not yet part of this
            mapping, it will be added by modifying the mapping in place.
        """
        del namespaces
        value = getattr(obj, self.__name__)
        elem.attrib[self._xmlname] = self._data_to_xml(value)

    @abc.abstractmethod
    def _data_from_xml(self, value: str) -> _T:
        """Convert the XML value to the correct data type."""

    @abc.abstractmethod
    def _data_to_xml(self, data: _T) -> str:
        """Convert the data to XML.

        Only called for non-default values, as default values do not get
        serialized at all.
        """


class StringPOD(AbstractPOD[str]):
    """A POD containing arbitrary string user data.

    Parameters
    ----------
    name
        The name of the XML attribute.
    required
        Whether this attribute is required.
    writable
        Whether this attribute can be changed after the object has been
        created or loaded.
    """

    def __init__(
        self, /, name: str, *, required: bool = False, writable: bool = True
    ) -> None:
        super().__init__(name, "", required, writable)

    @staticmethod
    def _data_from_xml(value: str) -> str:
        return value

    @staticmethod
    def _data_to_xml(data: str) -> str:
        return data


class IntPOD(AbstractPOD[int]):
    """A POD containing a number.

    Parameters
    ----------
    name
        The name of the XML attribute.
    required
        Whether this attribute is required.
    writable
        Whether this attribute can be changed after the object has been
        created or loaded.
    """

    def __init__(
        self, /, name: str, *, required: bool = False, writable: bool = True
    ) -> None:
        super().__init__(name, 0, required, writable)

    @staticmethod
    def _data_from_xml(value: str) -> int:
        return int(value)

    @staticmethod
    def _data_to_xml(data: int) -> str:
        return str(data)


class FloatPOD(AbstractPOD[float]):
    """A POD containing a floating-point number.

    Positive infinity is stored in XML as `*`. Negative infinity and NaN
    values cannot be stored, and are therefore rejected when trying to
    set them.

    Parameters
    ----------
    name
        The name of the XML attribute.
    required
        Whether this attribute is required.
    writable
        Whether this attribute can be changed after the object has been
        created or loaded.
    """

    def __init__(
        self, /, name: str, *, required: bool = False, writable: bool = True
    ) -> None:
        super().__init__(name, 0.0, required, writable)

    def __set__(self, obj: ModelElement, value: float) -> None:
        if math.isnan(value) or math.isinf(value) and value < 0:
            raise ValueError(f"Invalid value for {self._qualname}: {value!r}")
        super().__set__(obj, value)

    @staticmethod
    def _data_from_xml(value: str) -> float:
        if value == "*":
            return math.inf
        return float(value)

    @staticmethod
    def _data_to_xml(data: float) -> str:
        if math.isinf(data):
            return "*"
        return str(data)


class BoolPOD(AbstractPOD[bool]):
    """A POD containing a boolean.

    Parameters
    ----------
    name
        The name of the XML attribute.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, False, False, True)

    @staticmethod
    def _data_from_xml(value: str) -> bool:
        return value == "true"

    @staticmethod
    def _data_to_xml(data: bool) -> str:
        assert data is True
        return "true"


class DateTimePOD(AbstractPOD["datetime.datetime | None"]):
    """A POD for a timestamp field.

    The XML format is almost the same as ISO8601; the only difference is
    that the timezone does not contain a colon.

    This POD always uses millisecond precision. Microseconds are
    truncated when setting a value.

    Timezone-unaware datetimes are converted to the local timezone when
    being set. Timezone-aware datetimes are preserved as-is.

    Parameters
    ----------
    name
        The name of the XML attribute.
    required
        Whether this attribute is required. If it is required, the
        attribute cannot be set to ``None``.
    writable
        Whether this attribute can be changed after the object has been
        created or loaded.
    """

    re_set = re.compile(r"(?<=[+-]\d\d):(?=\d\d$)")
    re_get = re.compile(r"(?<=[+-]\d\d)(?=\d\d$)")

    def __init__(
        self, /, name: str, *, required: bool = False, writable: bool = True
    ) -> None:
        super().__init__(name, None, required, writable)

    def __set__(
        self, obj: ModelElement, value: datetime.datetime | None
    ) -> None:
        if value is None:
            super().__delete__(obj)
            return

        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            value = value.astimezone()

        value = value.replace(
            microsecond=value.microsecond - value.microsecond % 1000
        )
        super().__set__(obj, value)

    def _data_from_xml(self, value: str) -> datetime.datetime:
        value = self.re_get.sub(":", value)
        return datetime.datetime.fromisoformat(value)

    def _data_to_xml(self, data: datetime.datetime | None) -> str:
        assert data is not None
        value = data.isoformat(timespec="milliseconds")
        return self.re_set.sub("", value)


class EnumPOD(AbstractPOD[_E]):
    """A string-like POD which can take one of the values of a given Enum.

    During construction, this POD takes an :class:~enum.Enum or
    :class:~enum.Flag class. The keys defined in that class become the
    possible values for this POD. The Enum's values are not used by this
    implementation.

    When setting the value of this POD, you can either pass an instance
    of the Enum class, or the name of one of its members. When getting
    the value, you will always get an instance of the Enum class.

    The ``default`` value is not written out to the XML. If no default
    was explicitly specified, the first value of the passed Enum
    implicitly becomes the default.

    .. note::

       :class:enum.Flag does not enumerate the null member or named
       combinations:

       >>> import enum
       >>> class MyFlag(enum.Flag):
       ...     O = 0
       ...     A = 1
       ...     B = 2
       ...     AB = A|B
       ...
       >>> [i.name for i in MyFlag]
       ["A", "B"]

       If one of these cases should be the default, you must always
       explicitly pass the ``default`` parameter, e.g.:

       >>> m.EnumPOD("myflag", MyFlag, default="AB")

    Parameters
    ----------
    name
        The name of the XML attribute.
    enumcls
        The enum class to use.
    default
        The default value. Either an instance of the enum class, or
        the name of one of its members.
    writable
        Whether the attribute can be changed after instantiation.
    """

    def __init__(
        self,
        /,
        name: str,
        enumcls: type[_E],
        *,
        default: str | _E | None = None,
        writable: bool = True,
    ) -> None:
        """Create a new enum POD."""
        if isinstance(default, str):
            default = t.cast(_E, enumcls[default])
        elif default is None:
            default = next(iter(t.cast("cabc.Iterable[_E]", enumcls)), None)
            if default is None:
                raise TypeError(f"Enum class has no members: {enumcls!r}")
        elif not isinstance(default, enumcls):
            raise TypeError(
                f"default must be an instance of the passed enumcls,"
                f" not {default!r}"
            )
        super().__init__(name, default, False, writable)
        self._enumcls = enumcls

    def __set__(self, obj: ModelElement, value: str | _E) -> None:
        if isinstance(value, str):
            value = t.cast(_E, self._enumcls[value])
        super().__set__(obj, value)

    def _data_from_xml(self, value: str) -> _E:
        return t.cast(_E, self._enumcls[value])

    def _data_to_xml(self, data: _E) -> str:
        assert data.name is not None
        return data.name


class _ModelElementMeta(abc.ABCMeta):
    def __setattr__(cls, attr, value):
        LOGGER.log(5, "setattr(%r, %r, %r)", cls, attr, value)
        super().__setattr__(attr, value)
        setname = getattr(value, "__set_name__", None)
        if setname is not None:
            setname(cls, attr)

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, t.Any],
        *,
        ns: Namespace | None = None,
        minver: str | None = None,
        maxver: str | None = None,
        eq: str | None = None,
        abstract: bool = False,
    ) -> type[ModelElement]:
        """Create a new model object class.

        This method automatically registers the class with the
        namespace, taking care of the ``minver`` and ``maxver``
        constraints.

        Parameters
        ----------
        name
            The name of the class.
        bases
            The base classes of the class.
        namespace
            The class' namespace, as defined by Python.
        ns
            The metamodel namespace to register the class in. If not
            specified, the namespace is looked up in the module that
            defines the class.
        minver
            The minimum version of the namespace that this class is
            compatible with. If not specified, the minimum version is
            assumed to be 0.
        maxver
            The maximum version of the namespace that this class is
            compatible with. If not specified, there is no maximum
            version.
        eq
            When comparing instances of this class with non-model
            classes, this attribute is used to determine equality. If
            not specified, the standard Python equality rules apply.
        abstract
            Mark the class as abstract. Only subclasses of abstract
            classes can be instantiated, not the abstract class itself.
        """
        del abstract  # FIXME prohibit instantiation of abstract classes
        if eq is not None:
            if "__eq__" in namespace:
                raise TypeError(
                    f"Cannot generate __eq__ for {name!r}:"
                    f" method already defined in class body"
                )

            def __eq__(self, other):
                if not isinstance(other, ModelElement):
                    value = getattr(self, eq)  # type: ignore[arg-type]
                    return value.__eq__(other)
                # pylint: disable-next=bad-super-call
                return super(cls, self).__eq__(other)  # type: ignore[misc]

            namespace["__eq__"] = __eq__

        cls = t.cast(
            "type[ModelElement]",
            super().__new__(mcs, name, bases, namespace),
        )

        if ns is None:
            modname = cls.__module__
            cls_mod = importlib.import_module(modname)
            auto_ns = getattr(cls_mod, "NS", None)
            if not isinstance(auto_ns, Namespace):
                raise TypeError(
                    f"Cannot create class {cls.__name__!r}: No namespace\n"
                    "\n"
                    f"No Namespace found at {modname}.NS,\n"
                    "and no `ns` passed explicitly while subclassing.\n"
                    "\n"
                    "Declare a module-wide namespace with:\n"
                    "\n"
                    f"    # {modname.replace('.', '/')}.py\n"
                    "    from capellambse import Namespace\n"
                    "    NS = Namespace(...)\n"
                    "\n"
                    "Or specify it explicitly for each class:\n"
                    "\n"
                    "    from capellambse import Namespace\n"
                    "    MY_NS = Namespace(...)\n"
                    f"    class {cls.__name__}(..., ns=MY_NS): ...\n"
                )
            ns = auto_ns

        ns.register(cls, minver=minver, maxver=maxver)
        return cls


class ModelElement(metaclass=_ModelElementMeta):
    """A model element.

    This is the common base class for all elements of a model. In terms
    of the metamodel, it combines the role of
    ``modellingcore.ModelElement`` and all its superclasses; references
    to any superclass should be modified to use this class instead.

    This class has a symbiotic relationship with the various subclasses
    of :class:`ElementAttributeDescriptor` and :class:`AbstractPOD`.
    These classes are used to define the available attributes on a
    given model object type, and implement means to serialize and
    deserialize to the Capella XML format. The :class:`ModelElement`
    class itself is responsible for keeping track of the model it
    belongs to, cleaning up after itself when it is deleted from the
    model, and for ensuring that all required attributes are defined
    when instantiating a new object.

    For this to work, these class hierarchies have the following
    contract:

    - All attributes on a model object that have an XML representation
      must be defined as class attributes on the corresponding subclass
      of :class:`ModelElement`.
    - All attributes must be defined as either an instance of
      :class:`ElementAttributeDescriptor` or :class:`AbstractPOD`.
    - :class:`ElementAttributeDescriptor` and :class:`AbstractPOD` have
      to register themselves on their owner class' ``_required_``
      attribute, which is a set of all required attributes. This logic
      is already implemented by these classes' ``__set_name__`` methods,
      and must be kept intact in subclasses.

    Parameters
    ----------
    model
        The model this object belongs to.
    uuid
        The UUID of the object. If not given, a new UUID will be
        generated. If a ``model`` is also given, the generated UUID
        is guaranteed to not collide with an existing object in that
        model.
    **kw
        Keyword arguments to set on the object.

        Depending on the type of object, some attributes may be required.
    """

    uuid = StringPOD(name="id", required=True, writable=False)
    """The universally unique identifier of this object.

    This attribute is automatically populated when the object is
    instantiated, and cannot be changed afterwards. It is however
    possible to specify the UUID when instantiating the object, in which
    case it will be used instead of generating a new one.

    The UUID may be used in hashmaps and the like, as it is guaranteed
    to not change during the object's lifetime and across model
    save/reload cycles.
    """

    sid = StringPOD(name="sid")
    """The unique system identifier of this object."""

    extensions: Containment["ModelElement"]
    constraints: Backref["M.modellingcore.AbstractConstraint"]
    owned_constraints: Containment["M.modellingcore.AbstractConstraint"]
    migrated_elements: Containment["ModelElement"]

    __hash__ = None  # type: ignore[assignment]
    """Disable hashing by default on the base class.

    The ``__hash__`` contract states that two objects that compare equal
    must have the same hash value, and that the hash value must not
    change over an object's lifetime.

    Some subclasses of ``ModelElement`` which encapsulate a piece of
    plain old data compare the same as one of their attributes, which
    means they would have to also hash to the same value as that
    attribute.

    However, since ModelElement instances are mutable, that attribute
    could change at any time, which would result in those instances
    ending up in the wrong hash bucket, thus breaking lookups.

    For this reason, and to avoid inconsistent behavior where some
    classes are hashable and some are not, hashing of ModelObjects is
    generally disabled.
    """

    _unhandled_children: dict[str, list[ModelElement]]
    """Children that were not handled by any of the registered descriptors.

    This dictionary collects all children that were not handled by any
    proper descriptor. The attribute only exists if there were any such
    children, and will raise an AttributeError on access otherwise.

    The dictionary keys are the tag names (i.e. relationships) of the
    unhandled children, and the values are lists of the corresponding
    :class:`ModelElement` instances. Those instances may or may not be
    :class:`Alien` instances, depending on whether the child's
    ``xsi:type`` could be resolved or not.
    """

    __model: weakref.ReferenceType[_modelmod.Model] | None
    __fragment: ResourceName | None
    __parent: cabc.Callable[[], ModelElement | None]

    @property
    def _model(self) -> _modelmod.Model:
        """The model this object belongs to.

        If this object is not part of a model, or the model has already
        been garbage collected, an AttributeError is raised.
        """
        if self.__model is None:
            raise AttributeError(
                f"{self._short_repr_()} is not part of a model"
            )
        model = self.__model()
        if model is None:  # pragma: no cover
            raise AttributeError(
                f"The model of {self._short_repr_()}"
                " has been garbage collected"
            )
        return model

    @_model.setter
    def _model(self, model: _modelmod.Model) -> None:
        """Set the model this object belongs to."""
        model._register(self)
        self.__model = weakref.ref(model)

    @_model.deleter
    def _model(self) -> None:
        """Remove this object from its model."""
        self.__model = None

    @property
    def _fragment(self) -> ResourceName | None:
        """The fragment this object is in.

        If this object is a fragment root, this property contains the
        name of that fragment. If it is not a fragment root, this
        property contains None; in this case this object should be
        serialized nested within its parent.

        If the object is not currently part of a model, accessing this
        property will raise an AttributeError.

        An object that is part of a model must always either have a
        parent or be a fragment root or both.

        :meta public:
        """
        if not hasattr(self, "_model"):
            raise AttributeError(f"{self!r} is not part of a model")
        return self.__fragment

    @_fragment.setter
    def _fragment(self, fragment: ResourceNameIsh | None) -> None:
        if not hasattr(self, "_model"):
            raise AttributeError(
                f"Cannot set fragment: {self!r} is not part of a model"
            )
        if fragment is None:
            self.__fragment = None
        else:
            label, filename = fragment
            filepath = pathlib.PurePosixPath(filename)
            self.__fragment = ResourceName(label, filepath)

    @_fragment.deleter
    def _fragment(self) -> None:
        if not hasattr(self, "_model"):
            raise AttributeError(
                f"Cannot set fragment: {self!r} is not part of a model"
            )
        self.__fragment = None

    @property
    def parent(self) -> ModelElement | None:
        """Return the parent of this object."""
        return self.__parent()

    @parent.setter
    def parent(self, parent: ModelElement | None) -> None:
        if parent is not None:
            self.__parent = weakref.ref(parent)
        else:
            self.__parent = lambda: None

    @parent.deleter
    def parent(self) -> None:
        self.__parent = lambda: None

    def _walk_parents(self) -> cabc.Iterator[ModelElement]:
        """Iterate over this object and all its parents.

        :meta public:
        """
        obj: ModelElement | None = self
        while obj is not None:
            yield obj
            obj = obj.parent

    @property
    def _required_(self) -> set[str]:
        """A set of all required attributes.

        The attributes in this set are required to be set in order for
        an instance of this class to be valid.

        The set computation takes into account all descriptors defined
        on this class and all its superclasses; an attribute is
        considered required if its descriptor defines an attribute
        ``_required`` with a truthy value.
        """
        return {
            i
            for i in dir(type(self))
            if getattr(getattr(type(self), i, None), "_required", False)
        }

    def __init__(
        self,
        model: _modelmod.Model | None = None,
        uuid: str | uuidlib.UUID | None = None,
        **kw: t.Any,
    ) -> None:
        """Create a new model object."""
        self.__model = None
        if model is not None:
            self._model = model
        self.parent = kw.pop("parent", None)

        if missing := self._required_ - kw.keys() - {"uuid"}:
            raise TypeError(
                f"Missing required attributes for {type(self).__name__}:"
                f" {', '.join(missing)}"
            )

        if uuid is not None:
            if not isinstance(uuid, str):
                uuid = str(uuid)
            self.uuid = uuid
        elif model is not None:
            self.uuid = model._generate_uuid()
        else:
            self.uuid = str(uuidlib.uuid4())

        for attr, value in kw.items():
            descriptor = getattr(type(self), attr, None)
            if isinstance(descriptor, _AbstractDescriptor):
                descriptor.__set__(self, value)
            else:
                raise TypeError(
                    f"Invalid attribute for {type(self).__name__}: {attr}"
                )

    def __repr__(self) -> str:
        header = self._short_repr_()

        attrs: list[str] = []
        for attr in dir(self):
            if attr.startswith("_"):
                continue

            try:
                value = getattr(self, attr)
            except AttributeError:
                continue
            except Exception as err:
                value = f"<{type(err).__name__}: {err}>"
            else:
                if inspect.ismethod(value):
                    continue

                if hasattr(value, "_short_repr_"):
                    value_repr = f"{value._short_repr_()}"
                else:
                    value_repr = textwrap.shorten(repr(value), 250)

            firstprefix = f".{attr} = "
            followprefix = " " * len(firstprefix)
            prefix = (firstprefix, followprefix)
            value_repr = "\n".join(
                prefix[bool(i)] + line
                for i, line in enumerate(value_repr.splitlines() or [""])
            )
            attrs.append(value_repr)

        attr_text = "\n".join(attrs)
        return f"{header}\n{attr_text}"

    def _short_repr_(self) -> str:
        mytype = type(self).__name__
        if myname := getattr(self, "name", None):
            myname = " " + repr(myname)
        else:
            myname = ""
        myuuid = getattr(self, "uuid", "<no uuid>")
        return f"<{mytype}{myname} ({myuuid})>"

    def __setattr__(self, attr, value):
        if attr.startswith("_") or hasattr(type(self), attr):
            super().__setattr__(attr, value)
        else:
            raise AttributeError(
                f"Invalid attribute for {type(self).__name__}: {attr}"
            )

    @classmethod
    def _parse_xml(
        cls,
        model: _modelmod.Model,
        elem: etree._Element,
        lazy_attributes: cabc.MutableSet[tuple[str, str]],
    ) -> te.Self:
        """Parse an XML element into a model object.

        Parameters
        ----------
        model
            The model that is being loaded.
        elem
            The XML element currently being parsed.
        lazy_attributes
            A set that may be populated with (UUID, attribute) tuples.
            Descriptors register themselves with this set if they cannot
            yet be fully resolved, and need to be loaded in the second
            pass.

            Descriptors that want to use this facility must implement
            the :meth:`ElementAttributeDescriptor.resolve` method. That
            method is then called for each object (identified by their
            UUIDs) that was registered with this set.

            Descriptors must still consume all XML elements that belong
            to them, even if they cannot yet be resolved. They also must
            store enough information to fully reconstruct the object
            during the second pass, as it will not have access to the
            original XML tree anymore.

        Returns
        -------
        Instance of ``cls``
            The model object that was parsed from the passed XML
            element, populated with its child objects and attributes.
        """
        self = cls.__new__(cls)
        self.__model = weakref.ref(model)
        self.__parent = lambda: None
        complex_attributes: list[RelationshipDescriptor | Single] = []
        for attr in dir(cls):
            descriptor = getattr(cls, attr)

            if isinstance(descriptor, AbstractPOD):
                descriptor.from_xml(self, elem, lazy_attributes)
            elif isinstance(descriptor, (RelationshipDescriptor, Single)):
                complex_attributes.append(descriptor)

        for descriptor in complex_attributes:
            descriptor.from_xml(self, elem, lazy_attributes)

        if len(elem) > 0:
            tags = "\n".join(f" - {child!r}" for child in elem)
            LOGGER.warning(
                "%s contains unhandled children:\n%s",
                self._short_repr_(),
                tags,
            )
            model._has_aliens = True
            self._unhandled_children = {}
            for child in elem:
                cobj = load_object(model, child, lazy_attributes)
                cobj.parent = self
                self._unhandled_children.setdefault(child.tag, []).append(cobj)

        if len(elem.attrib) > 0:
            attrs = ", ".join(sorted(elem.attrib))
            LOGGER.warning(
                "%s contains unhandled attributes: %s",
                self._short_repr_(),
                attrs,
            )
            model._has_aliens = True

        if elem.text is not None and (text := elem.text.strip()):
            LOGGER.warning(
                "%s contains unhandled text: %r", self._short_repr_(), text
            )
            model._has_aliens = True

        model._register(self)
        return self

    def _to_xml(
        self,
        *,
        namespaces: cabc.MutableMapping[str, str] | None = None,
    ) -> etree._Element:
        """Generate an XML tree from this model element.

        The returned tree contains this element, as well as all its
        attributes and children.

        Parameters
        ----------
        namespaces
            A mapping from namespaces to their aliases, i.e. the inverse
            of ``etree._Element.nsmap``.

            If a namespace is needed that is not yet part of this
            mapping, it will be added by modifying the mapping in place.
        relation
            Name of the relation between this element and its parent, if
            it has one. If passed, this will cause the generated root
            XML element's tag to be set to the relation name, and this
            element's type to be recorded as the ``xsi:type`` attribute.
            If not given, the tag will be used for the element type and
            there will be no ``xsi:type`` attribute.
        """
        if namespaces is None:
            namespaces = {}
        elem = etree.Element(type(self).__name__)
        for attr in dir(type(self)):
            acc = getattr(type(self), attr)
            if not isinstance(acc, (AbstractPOD, RelationshipDescriptor)):
                continue
            acc.to_xml(self, elem, namespaces)
        return elem


class Alien(ModelElement):
    """A model object whose type is not properly handled yet.

    If this class has been instantiated for a model, modifying and
    saving the model will be disabled.
    """

    attributes: dict[str, str]
    children: list[ModelElement]

    def __init__(self) -> None:  # pylint: disable=super-init-not-called
        raise TypeError("Cannot instantiate Alien objects directly")

    @classmethod
    def _parse_xml(
        cls,
        model: _modelmod.Model,
        elem: etree._Element,
        lazy_attributes: cabc.MutableSet[tuple[str, str]],
    ) -> te.Self:
        model._has_aliens = True
        self = cls.__new__(cls)
        object.__setattr__(self, "attributes", dict(elem.attrib))
        object.__setattr__(self, "children", [])
        for child in elem:
            obj = load_object(model, child, lazy_attributes)
            obj.parent = self
            self.children.append(obj)
        cls.uuid.from_xml(self, elem, lazy_attributes)
        cls.sid.from_xml(self, elem, lazy_attributes)
        self._model = model
        self.parent = None
        return self


def add_descriptor(
    cls: type[ModelElement],
    attr: str,
    descriptor: _Descriptor,
) -> None:
    setattr(cls, attr, descriptor)
    set_name = getattr(descriptor, "__set_name__", None)
    if set_name is not None:
        set_name(cls, attr)


def new_object(*type_hint: str, **kw: t.Any) -> ModelElement:
    raise NotImplementedError("NYI")  # TODO


def load_object(
    model: _modelmod.Model,
    elem: etree._Element,
    lazy_attributes: cabc.MutableSet[tuple[str, str]],
) -> ModelElement:
    """Load a model object from an XML element.

    Parameters
    ----------
    model
        The model that is being loaded.
    elem
        The XML element currently being parsed.
    lazy_attributes
        A set of (UUID, attribute) tuples used to lazily resolve forward
        references to model objects. See :meth:`ModelElement._parse_xml`
        for details.
    """
    objtypename = find_objtype(elem)
    objtype = find_class(*objtypename)
    elem.attrib.pop(f"{{{_NS_XSI}}}type", None)
    obj = objtype._parse_xml(model, elem, lazy_attributes)
    return obj


def find_objtype(elem: etree._Element) -> tuple[str, str]:
    """Find the type name for an XML element.

    This looks at either the ``xsi:type`` attribute or the element's tag
    name to find the namespace and class name of the object.

    Parameters
    ----------
    elem
        The XML element.

    Returns
    -------
    UnresolvedClassName
        A tuple with the found namespace and class name.

        The namespace is always passed out as string URI, not as
        Namespace object.
    """
    ns: str | None = None
    if xtype := elem.get(f"{{{_NS_XSI}}}type"):
        ns, clsname = xtype.split(":")
        if ns not in elem.nsmap:
            raise BrokenModelError(f"Bad XML: Undefined namespace {ns!r}")
        ns = elem.nsmap[ns]
    elif nsmatch := re.match(r"{(.+)}(.+)$", elem.tag):
        ns, clsname = nsmatch.groups()
    else:
        raise BrokenModelError(f"Bad XML: Missing xsi:type for {elem!r}")
    assert isinstance(ns, str)
    assert isinstance(clsname, str)
    return (ns, clsname)


@functools.cache
def find_namespace(ns_uri: str) -> tuple[Namespace, av.AwesomeVersion | None]:
    match = [
        (ns, ver)
        for ep in imm.entry_points(group="capellambse.namespaces")
        if (ver := _ns_matches_uri((ns := ep.load()), ns_uri)) is not None
    ]
    if not match:
        raise KeyError(ns_uri)
    elif len(match) > 1:
        raise RuntimeError(f"Multiple namespaces matching URI {ns_uri!r}")
    ((ns, ns_version),) = match
    if ns_version == "{VERSION}":
        return (ns, None)
    return (ns, av.AwesomeVersion(ns_version or "0.0.0"))


@functools.cache
def find_class(ns_uri: str, clsname: str) -> type[ModelElement]:
    if isinstance(ns_uri, Namespace):
        raise TypeError("Invalid namespace: use URI string, not Namespace")
    try:
        (ns, ns_version) = find_namespace(ns_uri)
    except KeyError:
        return Alien

    try:
        return ns.get_class(clsname, ns_version or None)
    except MissingClassError as err:
        LOGGER.warning("%s", err)
        return Alien


def reset_entrypoint_caches() -> None:
    """Reset all cached data from entry points.

    After this function is called, all defined entry points will be
    iterated again to find relevant namespaces and viewpoints.

    This might be necessary after changes to the runtime module search
    path, in order for changes to become known to capellambse.
    """
    find_namespace.cache_clear()
    find_class.cache_clear()


def _ns_matches_uri(ns: Namespace, ns_uri: str) -> str | None:
    if "{VERSION}" not in ns.uri:
        return (None, "")[ns.uri == ns_uri]
    prefix, _, postfix = ns.uri.partition("{VERSION}")
    if (
        ns_uri.startswith(prefix)
        and ns_uri.endswith(postfix)
        and len(ns_uri) > len(prefix) + len(postfix)
    ):
        version = ns_uri[len(prefix) : -len(postfix) or None]
        if version == "{VERSION}" or RE_VERSION.match(version):
            return version
    return None


def _resolve_class_names(
    *clsnames: UnresolvedClassName,
) -> tuple[ClassName, ...]:
    rnames: list[ClassName] = []
    is_wildcard = False
    for ns, clsname in clsnames:
        if ns == "":
            ns, clsname = NS, ModelElement.__name__
            is_wildcard = True
        elif not isinstance(ns, Namespace):
            raise TypeError("NYI")
        rnames.append((ns, clsname))
    if is_wildcard and len(rnames) > 1:
        raise TypeError(
            'Cannot combine wildcard ("", "") with real class names'
        )
    return tuple(rnames)


def _resolve_class(cls: ClassName, model: _modelmod.Model) -> tuple[str, str]:
    ns, clsname = cls
    if "{VERSION}" not in ns.uri:
        return (ns.uri, clsname)

    try:
        vps = model.metadata.viewpoints
    except RuntimeError as err:
        if "metadata object" not in err.args[0]:
            raise
        version = "0.0.0"
    else:
        version = vps.get(ns.viewpoint or "") or "0.0.0"
    uri = ns.uri.format(VERSION=version)
    return (uri, clsname)
