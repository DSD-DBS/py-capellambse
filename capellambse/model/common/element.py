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
import typing_extensions as te
from lxml import etree

import capellambse
from capellambse import helpers

from . import XTYPE_HANDLERS, T, U, accessors, properties

_NOT_SPECIFIED = object()
"Used to detect unspecified optional arguments"

_MapFunction: te.TypeAlias = (
    "cabc.Callable[[T], GenericElement | cabc.Iterable[GenericElement]]"
)


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
                (
                    "Hashing of this type is broken and will likely be"
                    " removed in the future. Please use the `.uuid` or"
                    f" `.{attr}` directly instead."
                ),
                category=FutureWarning,
                stacklevel=2,
            )

            return orig_hash(self)

        cls.__eq__ = new_eq  # type: ignore[method-assign]
        cls.__hash__ = new_hash  # type: ignore[method-assign]

        return cls

    return add_wrapped_eq


class ModelObject(t.Protocol):
    """A class that wraps a specific model object.

    Most of the time, you'll want to subclass the concrete
    ``GenericElement`` class. However, some special classes (e.g. AIRD
    diagrams) provide a compatible interface, but it doesn't make sense
    to wrap a specific XML element. This protocol class is used in type
    annotations to catch both "normal" GenericElement subclasses and the
    mentioned special cases.
    """

    @property
    def _model(self) -> capellambse.MelodyModel:
        ...

    @property
    def _element(self) -> etree._Element:
        ...

    @property
    def _constructed(self) -> bool:
        ...

    def __init__(
        self,
        model: capellambse.MelodyModel,
        parent: etree._Element,
        **kw: t.Any,
    ) -> None:
        """Create a new model object.

        Parameters
        ----------
        model
            The model instance.
        parent
            The parent XML element below which to create a new object.
        kw
            Any additional arguments will be used to populate the
            instance attributes. Note that some attributes may be
            required by specific element types at construction time
            (commonly e.g. ``uuid``).
        """

    @classmethod
    def from_model(
        cls, model: capellambse.MelodyModel, element: t.Any
    ) -> ModelObject:
        """Instantiate a ModelObject from existing model elements."""


class GenericElement:
    """Provides high-level access to a single model element."""

    uuid = properties.AttributeProperty("id", writable=False)
    xtype = property(lambda self: helpers.xtype_of(self._element))
    name = properties.AttributeProperty("name", optional=True, default="")
    description = properties.HTMLAttributeProperty(
        "description", optional=True
    )
    summary = properties.AttributeProperty("summary", optional=True)
    diagrams: accessors.Accessor[capellambse.model.diagram.Diagram]
    diagrams = property(  # type: ignore[assignment]
        lambda self: self._model.diagrams.by_target_uuid(self.uuid)
    )

    constraints: accessors.Accessor
    parent: accessors.ParentAccessor

    _constructed: bool
    _required_attrs = frozenset({"uuid", "xtype"})
    _xmltag: str | None = None

    @property
    def progress_status(self) -> properties.AttributeProperty | str:
        uuid = self._element.get("status")
        if uuid is None:
            return "NOT_SET"

        return self.from_model(self._model, self._model._loader[uuid]).name

    @classmethod
    def from_model(
        cls, model: capellambse.MelodyModel, element: etree._Element
    ) -> te.Self:
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
            if class_ is not cls:
                return class_.from_model(model, element)
        self = class_.__new__(class_)
        self._model = model
        self._element = element
        self._constructed = True
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
        self._constructed = False
        self._model = model
        self._element: etree._Element = etree.Element(self._xmltag)
        parent.append(self._element)
        try:
            for key, val in kw.items():
                if key == "xtype":
                    self._element.set(helpers.ATT_XT, val)
                    self._model._loader.add_namespace(
                        parent, val.split(":", maxsplit=1)[0]
                    )
                elif not isinstance(
                    getattr(type(self), key),
                    (accessors.Accessor, properties.AttributeProperty),
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
        self._constructed = True

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

            acc = getattr(type(self), attr, None)
            if isinstance(acc, accessors.ReferenceSearchingAccessor):
                classes = ", ".join(i.__name__ for i in acc.target_classes)
                attrs.append(
                    f".{attr} = ... # backreference to {classes}"
                    " - omitted: can be slow to compute"
                )
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
        if self.name:
            name = f" {self.name!r}"
        else:
            name = ""
        return f"<{mytype}{name} ({self.uuid})>"

    def __html__(self) -> markupsafe.Markup:
        fragments: list[str] = []
        escape = markupsafe.Markup.escape

        # pylint: disable=unidiomatic-typecheck
        if type(self) is GenericElement:
            fragments.append("<h1>Model element")
        else:
            fragments.append("<h1>")
            fragments.append(escape(self.name or type(self).__name__))
        fragments.append(' <span style="font-size: 70%;">(')
        fragments.append(escape(self.xtype))
        fragments.append(")</span>")
        fragments.append("</h1>")

        fragments.append("<table>")
        for attr in dir(self):
            if attr.startswith("_"):
                continue

            acc = getattr(type(self), attr, None)
            if isinstance(acc, accessors.ReferenceSearchingAccessor):
                classes = ", ".join(i.__name__ for i in acc.target_classes)
                fragments.append('<tr><th style="text-align: right;">')
                fragments.append(escape(attr))
                fragments.append('</th><td style="text-align: left;"><em>')
                fragments.append(f"Backreference to {escape(classes)}")
                fragments.append(" - omitted: can be slow to compute.")
                fragments.append(" Display this property directly to show.")
                fragments.append("</em></td></tr>")
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

    if t.TYPE_CHECKING:

        def __getattr__(self, attr: str) -> t.Any:
            """Account for extension attributes in static type checks."""


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
                instead. If multiple elements match, it is an error; if
                none match, a ``KeyError`` is raised. Can be overridden
                at call time.
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
            returned. Consequently, if the original list was empty, this
            iterator will yield no values.

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
            self.__mapvalue: str | None = None
        else:
            self.__mapkey = operator.attrgetter(mapkey)
            self.__mapvalue = mapvalue

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
    def __getitem__(self, idx: int) -> T:
        ...

    @t.overload
    def __getitem__(self, idx: slice) -> ElementList[T]:
        ...

    @t.overload
    def __getitem__(self, idx: str) -> t.Any:
        ...

    def __getitem__(self, idx: int | slice | str) -> t.Any:
        if isinstance(idx, slice):
            return self._newlist(self._elements[idx])
        if isinstance(idx, int):
            return self._elemclass.from_model(self._model, self._elements[idx])

        obj = self._map_find(idx)
        return self._map_getvalue(obj)

    @t.overload
    def __setitem__(self, index: int, value: T) -> None:
        ...

    @t.overload
    def __setitem__(self, index: slice, value: cabc.Iterable[T]) -> None:
        ...

    @t.overload
    def __setitem__(self, index: str, value: t.Any) -> None:
        ...

    def __setitem__(self, index: int | slice | str, value: t.Any) -> None:
        if isinstance(index, slice):
            del self[index]
            for i, element in enumerate(value, start=index.start):
                self.insert(i, element)
        elif isinstance(index, int):
            del self[index]
            self.insert(index, value)
        else:
            obj = self._map_find(index)
            self._map_setvalue(obj, value)

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
        if self.__mapkey is None or self.__mapvalue is None:
            raise TypeError("This list cannot act as a mapping")

        try:
            return self.__mapkey(obj)
        except AttributeError:
            return None

    def _map_find(self, key: str) -> T:
        """Find the target object of a mapping operation.

        When this list acts as a mapping (like ``some_list["key"]``),
        this method finds the target object associated with the
        ``"key"``.

        See Also
        --------
        :meth:`_map_getvalue` and :meth:`_map_setvalue`
            Get or set the mapping value behind the target object.
        """
        if self.__mapkey is None or self.__mapvalue is None:
            raise TypeError("This list cannot act as a mapping")

        candidates = [i for i in self if self.__mapkey(i) == key]
        if len(candidates) > 1:
            raise ValueError(f"Multiple matches for key {key!r}")
        if not candidates:
            raise KeyError(key)
        return candidates[0]

    def _map_getvalue(self, obj: T) -> t.Any:
        """Get the mapping value from the target object."""
        assert self.__mapvalue
        getvalue = operator.attrgetter(self.__mapvalue)
        return getvalue(obj)

    def _map_setvalue(self, obj: T, value: t.Any) -> None:
        """Set a new mapping value on the target object."""
        assert self.__mapvalue
        key = self.__mapvalue.rsplit(".", maxsplit=1)
        if len(key) == 1:
            target: t.Any = obj
        else:
            target = operator.attrgetter(key[0])(obj)

        setattr(target, key[-1], value)

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

    def filter(
        self, predicate: str | cabc.Callable[[T], bool]
    ) -> ElementList[T]:
        """Filter this list with a custom predicate.

        The predicate may be the name of an attribute or a callable,
        which will be called on each list item. If the attribute value
        or the callable's return value is truthy, the item is included
        in the resulting list.

        When specifying the name of an attribute, nested attributes can
        be chained using ``.``, like ``"parent.name"`` (which would
        pick all elements whose ``parent`` has a non-empty ``name``).
        """
        if isinstance(predicate, str):
            predicate = operator.attrgetter(predicate)
        return self._newlist([i._element for i in self if predicate(i)])

    def map(self, attr: str | _MapFunction[T]) -> ElementList[GenericElement]:
        """Apply a function to each element in this list.

        If the argument is a string, it is interpreted as an attribute
        name, and the value of that attribute is returned for each
        element. Nested attribute names can be chained with ``.``.

        If the argument is a callable, it is called for each element,
        and the return value is included in the result. If the callable
        returns a sequence, the sequence is flattened into the result.

        Duplicate values and Nones are always filtered out.

        It is an error if a callable returns something that is not a
        model element or a flat sequence of model elements.
        """
        if isinstance(attr, str):
            attr = operator.attrgetter(attr)
        newelems: list[etree._Element] = []
        classes: set[type[GenericElement]] = set()
        for i in self:
            try:
                value = attr(i)
            except AttributeError:
                continue

            if not isinstance(value, cabc.Iterable):
                value = [value]

            for v in value:  # type: ignore[union-attr] # false-positive
                if v is None:
                    continue
                if isinstance(v, GenericElement):
                    newelems.append(v._element)
                    classes.add(type(v))
                else:
                    raise TypeError(
                        f"Map function must return a model element or a list"
                        f" of model elements, not {v!r}"
                    )

        if len(classes) == 1:
            return ElementList(self._model, newelems, classes.pop())
        return MixedElementList(self._model, newelems)


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


class ElementListMapItemsView(t.Sequence[t.Tuple[t.Any, t.Any]], t.Generic[T]):
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
            return [
                (self.__parent._mapkey(i), self.__parent._map_getvalue(i))
                for i in self.__parent[idx]
            ]
        obj = self.__parent[idx]
        return (self.__parent._mapkey(obj), self.__parent._map_getvalue(obj))

    def __len__(self) -> int:
        return len(self.__parent)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({list(self)!r})"
