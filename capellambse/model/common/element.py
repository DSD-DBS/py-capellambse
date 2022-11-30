# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

__all__ = [
    "ModelObject",
    "GenericElement",
    "ElementList",
    "CachedElementList",
    "MixedElementList",
    "attr_equal",
]

import collections.abc as cabc
import enum
import functools
import inspect
import operator
import re
import textwrap
import typing as t

import markupsafe
from lxml import etree

import capellambse
from capellambse import helpers
from capellambse.loader import xmltools

from . import XTYPE_HANDLERS, T, U, accessors

_NOT_SPECIFIED = object()
"Used to detect unspecified optional arguments"


def attr_equal(attr: str) -> cabc.Callable[[type[T]], type[T]]:
    def add_wrapped_eq(cls: type[T]) -> type[T]:
        orig_eq = cls.__eq__
        orig_hash = cls.__hash__

        @functools.wraps(orig_eq)
        def new_eq(self, other: object) -> bool:
            # pylint: disable=unnecessary-dunder-call
            try:
                cmpkey = getattr(self, attr)
            except AttributeError:
                pass
            else:
                if isinstance(other, type(cmpkey)):
                    result = cmpkey.__eq__(other)
                else:
                    result = other.__eq__(cmpkey)
                if result is not NotImplemented:
                    return result
            return orig_eq(self, other)

        @functools.wraps(orig_hash)
        def new_hash(self) -> int:
            import warnings

            # <https://github.com/DSD-DBS/py-capellambse/issues/52>
            warnings.warn(
                "Hashing of this type is broken and will likely be removed in"
                f" the future. Please use the `.uuid` or `.{attr}` directly"
                " instead.",
                category=FutureWarning,
                stacklevel=2,
            )

            return orig_hash(self)

        cls.__eq__ = new_eq  # type: ignore[assignment]
        cls.__hash__ = new_hash  # type: ignore[assignment]

        return cls

    return add_wrapped_eq


class ModelObject(t.Protocol):
    """A class that wraps a specific model object.

    Most of the time, you'll want to subclass the concrete
    ``GenericElement`` class.  However, some special classes (e.g. AIRD
    diagrams) provide a compatible interface, but it doesn't make sense
    to wrap a specific XML element.  This protocol class is used in type
    annotations to catch both "normal" GenericElement subclasses and the
    mentioned special cases.
    """

    _model: capellambse.MelodyModel
    _element: etree._Element

    def __init__(self, **kw: t.Any) -> None:
        if kw:
            raise TypeError(f"Unconsumed keyword arguments: {kw}")
        super().__init__()

    @classmethod
    def from_model(
        cls, model: capellambse.MelodyModel, element: t.Any
    ) -> ModelObject:
        """Instantiate a ModelObject from existing model elements."""


class GenericElement:
    """Provides high-level access to a single model element."""

    uuid = xmltools.AttributeProperty("_element", "id", writable=False)
    xtype = property(lambda self: helpers.xtype_of(self._element))
    name = xmltools.AttributeProperty(
        "_element", "name", optional=True, default="(Unnamed {self.xtype})"
    )
    description = xmltools.HTMLAttributeProperty(
        "_element", "description", optional=True
    )
    summary = xmltools.HTMLAttributeProperty(
        "_element", "summary", optional=True
    )
    diagrams = property(
        lambda self: self._model.diagrams.by_target_uuid(self.uuid)
    )

    constraints: accessors.Accessor
    parent: accessors.ParentAccessor

    _required_attrs = frozenset({"uuid", "xtype"})
    _xmltag: str | None = None

    @property
    def progress_status(self) -> xmltools.AttributeProperty | str:
        uuid = self._element.get("status")
        if uuid is None:
            return "NOT_SET"

        return self.from_model(self._model, self._model._loader[uuid]).name

    @classmethod
    def from_model(
        cls: type[T], model: capellambse.MelodyModel, element: etree._Element
    ) -> T:
        """Wrap an existing model object.

        Parameters
        ----------
        model
            The MelodyModel instance
        element
            The XML element to wrap

        Returns
        -------
        obj
            An instance of GenericElement (or a more appropriate
            subclass, if any) that wraps the given XML element.
        """
        class_ = cls
        if class_ is GenericElement:
            xtype = helpers.xtype_of(element)
            if xtype is not None:
                ancestors = model._loader.iterancestors(element)
                for ancestor in ancestors:
                    anc_xtype = helpers.xtype_of(ancestor)
                    try:
                        class_ = XTYPE_HANDLERS[anc_xtype][xtype]
                    except KeyError:
                        pass
                    else:
                        break
                else:
                    try:
                        class_ = XTYPE_HANDLERS[None][xtype]
                    except KeyError:
                        pass
        self = class_.__new__(class_)
        self._model = model
        self._element = element
        return self

    def __init__(
        self,
        model: capellambse.MelodyModel,
        parent: etree._Element,
        /,
        **kw: t.Any,
    ) -> None:
        all_required_attrs: set[str] = set()
        for basecls in type(self).mro():
            all_required_attrs |= getattr(
                basecls, "_required_attrs", frozenset()
            )
        missing_attrs = all_required_attrs - frozenset(kw)
        if missing_attrs:
            mattrs = ", ".join(sorted(missing_attrs))
            raise TypeError(f"Missing required keyword arguments: {mattrs}")

        super().__init__()
        if self._xmltag is None:
            raise TypeError(
                f"Cannot instantiate {type(self).__name__} directly"
            )
        self._model = model
        self._element: etree._Element = etree.Element(self._xmltag)
        parent.append(self._element)
        try:
            for key, val in kw.items():
                if key == "xtype":
                    self._element.set(helpers.ATT_XT, val)
                elif not isinstance(
                    getattr(type(self), key),
                    (accessors.Accessor, xmltools.AttributeProperty),
                ):
                    raise TypeError(
                        f"Cannot set {key!r} on {type(self).__name__}"
                    )
                else:
                    setattr(self, key, val)
            self._model._loader.idcache_index(self._element)
        except BaseException:
            parent.remove(self._element)
            raise

    def __getattr__(self, attr: str) -> t.Any:
        raise AttributeError(f"{attr} isn't defined on {type(self).__name__}")

    def __setattr__(self, attr: str, value: t.Any) -> None:
        if attr.startswith("_") or hasattr(type(self), attr):
            super().__setattr__(attr, value)
        else:
            raise AttributeError(
                f"{attr!r} isn't defined on {type(self).__name__}"
            )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._element is other._element

    def __hash__(self):
        return hash(self._element)

    def __repr__(self) -> str:  # pragma: no cover
        header = self._short_repr_()

        attrs: list[str] = []
        for attr in dir(self):
            if attr.startswith("_"):
                continue
            try:
                value = getattr(self, attr)
            except Exception:
                continue

            if inspect.ismethod(value):
                continue

            if hasattr(value, "_short_repr_"):
                value_repr = f"{value._short_repr_()}"
            else:
                value_repr = textwrap.shorten(repr(value), 250)

            prefix = f".{attr} = "
            blankprefix = " " * len(prefix)
            value_repr = "\n".join(
                (prefix, blankprefix)[bool(i)] + line
                for i, line in enumerate(value_repr.splitlines() or [""])
            )
            attrs.append(value_repr)

        attr_text = "\n".join(attrs)
        return f"{header}\n{attr_text}"

    def _short_repr_(self) -> str:
        # pylint: disable=unidiomatic-typecheck
        if type(self) is GenericElement:
            mytype = f"Model element ({self.xtype})"
        else:
            mytype = type(self).__name__
        return f"<{mytype} {self.name!r} ({self.uuid})>"

    def __html__(self) -> markupsafe.Markup:
        fragments: list[str] = []
        escape = markupsafe.Markup.escape

        # pylint: disable=unidiomatic-typecheck
        if type(self) is GenericElement:
            fragments.append("<h1>Model element")
        else:
            fragments.append("<h1>")
            fragments.append(escape(type(self).__name__))
        fragments.append(' <span style="font-size: 70%;">(')
        fragments.append(escape(self.xtype))
        fragments.append(")</span>")
        fragments.append("</h1>")

        fragments.append("<table>")
        for attr in dir(self):
            if attr.startswith("_"):
                continue
            try:
                value = getattr(self, attr)
            except Exception:
                continue

            if inspect.ismethod(value):
                continue

            fragments.append('<tr><th style="text-align: right;">')
            fragments.append(escape(attr))
            fragments.append('</th><td style="text-align: left;">')

            if hasattr(value, "_short_html_"):
                fragments.append(value._short_html_())
            elif isinstance(value, str):
                fragments.append(escape(value))
            else:
                value = repr(value)
                if len(value) > 250:
                    value = value[:250] + " [...]"
                fragments.append("<em>")
                fragments.append(escape(value))
                fragments.append("</em>")
            fragments.append("</td></tr>")
        fragments.append("</table>")
        return markupsafe.Markup("".join(fragments))

    def _short_html_(self) -> markupsafe.Markup:
        return self._wrap_short_html(
            f" &quot;{markupsafe.Markup.escape(self.name)}&quot;"
            f"{(': ' + str(self.value)) if hasattr(self, 'value') else ''}"
        )

    def _wrap_short_html(self, content: str) -> markupsafe.Markup:
        return markupsafe.Markup(
            f"<strong>{markupsafe.Markup.escape(type(self).__name__)}</strong>"
            f"{content} ({markupsafe.Markup.escape(self.uuid)})"
        )

    def _repr_html_(self) -> str:
        return self.__html__()


class ElementList(cabc.MutableSequence, t.Generic[T]):
    """Provides access to elements without affecting the underlying model."""

    __slots__ = (
        "_elemclass",
        "_elements",
        "_ElementList__mapkey",
        "_ElementList__mapvalue",
        "_model",
    )

    class _Filter(t.Generic[U]):
        """Filters this list based on an extractor function."""

        __slots__ = ("_attr", "_parent", "_positive", "_single")

        def __init__(
            self,
            parent: ElementList[T],
            attr: str,
            *,
            positive: bool = True,
            single: bool = False,
        ) -> None:
            """Create a filter object.

            If the extractor returns an :class:`enum.Enum` member for any
            element, the enum member's name will be used for comparisons
            against any ``values``.

            Parameters
            ----------
            parent
                Reference to the :class:`ElementList` this filter should
                operate on
            attr
                The attribute on list members to filter on
            extract_key
                Callable that extracts the key from an element
            positive
                Use elements that match (True) or don't (False)
            single
                When listing all matches, return a single element
                instead.  If multiple elements match, it is an error; if
                none match, a ``KeyError`` is raised.
                Can be overridden at call time.
            """
            self._attr = attr
            self._parent = parent
            self._positive = positive
            self._single = single

        def extract_key(self, element: T) -> U | str:
            extractor = operator.attrgetter(self._attr)
            value: U | enum.Enum | str = extractor(element)
            if isinstance(value, enum.Enum):
                value = value.name
            return value

        def make_values_container(self, *values: U) -> cabc.Container[U]:
            return values

        def ismatch(self, element: T, valueset: cabc.Container[U]) -> bool:
            try:
                value = self.extract_key(element)
            except AttributeError:
                return False

            return self._positive == (value in valueset)

        def __call__(
            self, *values: U, single: bool | None = None
        ) -> T | ElementList[T]:
            """List all elements that match this filter.

            Parameters
            ----------
            values
                The values to match against.
            single
                If not ``None``, overrides the ``single`` argument to
                the constructor for this filter call.
            """
            if single is None:
                single = self._single
            valueset = self.make_values_container(*values)
            indices = []
            elements = []
            for i, elm in enumerate(self._parent):
                if self.ismatch(elm, valueset):
                    indices.append(i)
                    elements.append(self._parent._elements[i])

            if not single:
                return self._parent._newlist(elements)
            if len(elements) > 1:
                value = values[0] if len(values) == 1 else values
                raise KeyError(f"Multiple matches for {value!r}")
            if len(elements) == 0:
                raise KeyError(values[0] if len(values) == 1 else values)
            return self._parent[indices[0]]  # Ensure proper construction

        def __iter__(self) -> cabc.Iterator[U | str]:
            """Yield values that result in a non-empty list when filtered for.

            The returned iterator yields all values that, when given to
            :meth:`__call__`, will result in a non-empty list being
            returned.  Consequently, if the original list was empty,
            this iterator will yield no values.

            The order in which the values are yielded is undefined.
            """
            # Use list, since not all elements may be hashable.
            yielded: set[U | str] = set()

            for elm in self._parent:
                key = self.extract_key(elm)
                if key not in yielded:
                    yield key
                    yielded.add(key)

        def __contains__(self, value: U) -> bool:
            valueset = self.make_values_container(value)
            for elm in self._parent:
                if self.ismatch(elm, valueset):
                    return True
            return False

        def __getattr__(self, attr: str) -> ElementList._Filter[U]:
            if attr.startswith("_"):
                raise AttributeError(f"Invalid filter attribute name: {attr}")
            return type(self)(
                self._parent,
                f"{self._attr}.{attr}",
                positive=self._positive,
                single=self._single,
            )

    def __init__(
        self,
        model: capellambse.MelodyModel,
        elements: list[etree._Element],
        elemclass: type[T] | None = None,
        *,
        mapkey: str | None = None,
        mapvalue: str | None = None,
    ) -> None:
        # pylint: disable=assigning-non-slot # false-positive
        self._model = model
        self._elements = elements
        if elemclass is not None:
            self._elemclass = elemclass
        else:
            self._elemclass = GenericElement  # type: ignore[assignment]

        if bool(mapkey) != bool(mapvalue):
            raise TypeError(
                "mapkey and mapvalue must both either be set or unset"
            )
        if not mapkey or not mapvalue:
            self.__mapkey: cabc.Callable[[T], t.Any] | None = None
            self.__mapvalue: cabc.Callable[[T], t.Any] | None = None
        else:
            self.__mapvalue = operator.attrgetter(mapvalue)
            self.__mapkey = operator.attrgetter(mapkey)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, cabc.Sequence):
            return NotImplemented
        return len(self) == len(other) and all(
            ours == theirs for ours, theirs in zip(self, other)
        )

    def __add(
        self, other: object, *, reflected: bool = False
    ) -> ElementList[T]:
        if not isinstance(other, ElementList):
            return NotImplemented
        if self._model is not other._model:
            raise ValueError("Cannot add ElementLists from different models")

        if self._elemclass is other._elemclass is not GenericElement:
            listclass: type[ElementList] = ElementList
            elemclass: type[ModelObject] = self._elemclass
        else:
            listclass = MixedElementList
            elemclass = GenericElement

        if not reflected:
            elements = self._elements + other._elements
        else:
            elements = other._elements + self._elements

        return listclass(self._model, elements, elemclass)

    def __add__(self, other: object) -> ElementList[T]:
        return self.__add(other)

    def __radd__(self, other: object) -> ElementList[T]:
        return self.__add(other, reflected=True)

    def __sub(
        self, other: object, *, reflected: bool = False
    ) -> ElementList[T]:
        if not isinstance(other, cabc.Sequence):
            return NotImplemented

        if reflected:
            if isinstance(other, ElementList):
                objclass = other._elemclass
            else:
                objclass = GenericElement
        else:
            objclass = self._elemclass

        base: cabc.Sequence[t.Any]
        if not reflected:
            base = self
            excluded = set(i.uuid for i in other)
        else:
            base = other
            excluded = set(i.uuid for i in self)

        return ElementList(
            self._model,
            [i._element for i in base if i.uuid not in excluded],
            objclass,
        )

    def __sub__(self, other: object) -> ElementList[T]:
        """Return a new list without elements found in ``other``."""
        return self.__sub(other)

    def __rsub__(self, other: object) -> ElementList[T]:
        return self.__sub(other, reflected=True)

    def __len__(self) -> int:
        return len(self._elements)

    @t.overload
    def __getitem__(self, idx: int | str) -> T:
        ...

    @t.overload
    def __getitem__(self, idx: slice) -> ElementList[T]:
        ...

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return self._newlist(self._elements[idx])
        if isinstance(idx, int):
            return self._elemclass.from_model(self._model, self._elements[idx])

        if self.__mapkey is None or self.__mapvalue is None:
            raise TypeError("This list cannot act as a mapping")

        values = [self._mapvalue(i) for i in self if self._mapkey(i) == idx]
        if len(values) > 1:
            raise ValueError(f"Multiple matches for key {idx!r}")
        if not values:
            raise KeyError(idx)
        return values[0]

    @t.overload
    def __setitem__(self, index: int, value: T) -> None:
        ...

    @t.overload
    def __setitem__(self, index: slice, value: cabc.Iterable[T]) -> None:
        ...

    def __setitem__(self, index, value):
        del self[index]
        if isinstance(index, slice):
            for i, element in enumerate(value, start=index.start):
                self.insert(i, element)
        else:
            self.insert(index, value)

    def __delitem__(self, index: int | slice) -> None:
        del self._elements[index]

    def __getattr__(
        self,
        attr: str,
    ) -> cabc.Callable[..., T | ElementList[T]]:
        if attr.startswith("by_"):
            attr = attr[len("by_") :]
            if attr in {"name", "uuid"}:
                return self._Filter(self, attr, single=True)
            return self._Filter(self, attr)

        if attr.startswith("exclude_") and attr.endswith("s"):
            attr = attr[len("exclude_") : -len("s")]
            return self._Filter(self, attr, positive=False)

        return getattr(super(), attr)

    def __dir__(self) -> list[str]:  # pragma: no cover
        no_dir_attr = re.compile(r"^(_|as_|pvmt$|nodes$|diagrams?$)")

        def filterable_attrs() -> cabc.Iterator[str]:
            for obj in self:
                try:
                    obj_attrs = dir(obj)
                except Exception:
                    pass
                for attr in obj_attrs:
                    if not no_dir_attr.search(attr) and isinstance(
                        getattr(obj, attr), str
                    ):
                        yield f"by_{attr}"
                        yield f"exclude_{attr}s"

        attrs = list(super().__dir__())
        attrs.extend(filterable_attrs())
        return attrs

    def __repr__(self) -> str:  # pragma: no cover
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

    def _short_repr_(self) -> str:
        return repr(self)

    def __html__(self) -> markupsafe.Markup:
        if not self:
            return markupsafe.Markup("<p><em>(Empty list)</em></p>")

        fragments = ['<ol start="0" style="text-align: left;">']
        for i in self:
            fragments.append(f"<li>{i._short_html_()}</li>")
        fragments.append("</ol>")
        return markupsafe.Markup("".join(fragments))

    def _short_html_(self) -> markupsafe.Markup:
        return self.__html__()

    def _repr_html_(self) -> str:
        return self.__html__()

    def _mapkey(self, obj: T) -> t.Any:
        assert self.__mapkey is not None
        try:
            return self.__mapkey(obj)
        except AttributeError:
            return None

    def _mapvalue(self, obj: T) -> t.Any:
        assert self.__mapvalue is not None
        try:
            return self.__mapvalue(obj)
        except AttributeError:
            return None

    def _newlist(self, elements: list[etree._Element]) -> ElementList[T]:
        listtype = self._newlist_type()
        return listtype(self._model, elements, self._elemclass)

    def _newlist_type(self) -> type[ElementList]:
        return type(self)

    @t.overload
    def get(self, key: str) -> T | None:
        ...

    @t.overload
    def get(self, key: str, default: U) -> T | U:
        ...

    def get(self, key: str, default: t.Any = None) -> t.Any:
        try:
            return self[key]
        except KeyError:
            return default

    def insert(self, index: int, value: T) -> None:
        elm: etree._Element = value._element
        self._elements.insert(index, elm)

    def items(self) -> ElementListMapItemsView[T]:
        return ElementListMapItemsView(self)

    def keys(self) -> ElementListMapKeyView:
        return ElementListMapKeyView(self)

    def values(self) -> ElementList[T]:
        return self


class CachedElementList(ElementList[T], t.Generic[T]):
    """An ElementList that caches the constructed proxies by UUID."""

    class _Filter(ElementList._Filter[U], t.Generic[U]):
        def __call__(
            self, *values: U, single: bool | None = None
        ) -> T | ElementList[T]:
            newlist: T | ElementList[T] = super().__call__(
                *values, single=single
            )
            if single or self._single:
                return newlist

            assert isinstance(newlist, CachedElementList)
            newlist.cacheattr = t.cast(t.Optional[str], self._parent.cacheattr)
            return newlist

    def __init__(
        self,
        model: capellambse.MelodyModel,
        elements: list[etree._Element],
        elemclass: type[T],
        *,
        cacheattr: str | None = None,
        **kw: t.Any,
    ) -> None:
        """Create a CachedElementList.

        Parameters
        ----------
        model
            The model that all elements are a part of.
        elements
            The members of this list.
        elemclass
            The :class:`GenericElement` subclass to use for
            reconstructing elements.
        cacheattr
            The attribute on the ``model`` to use as cache.
        """
        super().__init__(model, elements, elemclass, **kw)
        self.cacheattr = cacheattr

    def __getitem__(self, key):
        elem = super().__getitem__(key)
        if self.cacheattr and not isinstance(elem, ElementList):
            try:
                cache = getattr(self._model, self.cacheattr)
            except AttributeError:
                cache = {}
                setattr(self._model, self.cacheattr, cache)
            elem = cache.setdefault(elem.uuid, elem)
        return elem


class MixedElementList(ElementList[GenericElement]):
    """ElementList that handles proxies using ``XTYPE_HANDLERS``."""

    class _LowercaseFilter(ElementList._Filter[U], t.Generic[U]):
        def extract_key(self, element: ModelObject) -> U | str:
            value = super().extract_key(element)
            assert isinstance(value, str)
            return value.lower()

        def make_values_container(self, *values: U) -> cabc.Container[U]:
            return tuple(map(operator.methodcaller("lower"), values))

    def __init__(
        self,
        model: capellambse.MelodyModel,
        elements: list[etree._Element],
        elemclass: t.Any = None,
        **kw: t.Any,
    ) -> None:
        """Create a MixedElementList.

        Parameters
        ----------
        model
            The model that all elements are a part of.
        elements
            The members of this list.
        elemclass
            Ignored; provided for drop-in compatibility.
        """
        del elemclass
        super().__init__(model, elements, GenericElement, **kw)

    def __getattr__(
        self, attr: str
    ) -> cabc.Callable[..., GenericElement | ElementList[GenericElement]]:
        if attr == "by_type":
            return self._LowercaseFilter(self, "__class__.__name__")
        return super().__getattr__(attr)

    def __dir__(self) -> list[str]:  # pragma: no cover
        return super().__dir__() + ["by_type", "exclude_types"]


class ElementListMapKeyView(cabc.Sequence):
    def __init__(self, parent, /) -> None:
        self.__parent = parent

    @t.overload
    def __getitem__(self, idx: int) -> t.Any:
        ...

    @t.overload
    def __getitem__(self, idx: slice) -> list:
        ...

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return [self.__parent._mapkey(i) for i in self.__parent[idx]]
        return self.__parent._mapkey(self.__parent[idx])

    def __len__(self) -> int:
        return len(self.__parent)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({list(self)!r})"


class ElementListMapItemsView(t.Sequence[t.Tuple[t.Any, T]], t.Generic[T]):
    def __init__(self, parent, /) -> None:
        self.__parent = parent

    @t.overload
    def __getitem__(self, idx: int) -> tuple[t.Any, T]:
        ...

    @t.overload
    def __getitem__(self, idx: slice) -> list[tuple[t.Any, T]]:
        ...

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return [(self.__parent._mapkey(i), i) for i in self.__parent[idx]]
        obj = self.__parent[idx]
        return (self.__parent._mapkey(obj), obj)

    def __len__(self) -> int:
        return len(self.__parent)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({list(self)!r})"
