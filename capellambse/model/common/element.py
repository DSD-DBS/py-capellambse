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
from __future__ import annotations

import collections.abc
import enum
import operator
import re
import typing as t

from lxml import etree

import capellambse
from capellambse import helpers
from capellambse.loader import xmltools

from . import XTYPE_HANDLERS, accessors, markuptype

_NOT_SPECIFIED = object()
"Used to detect unspecified optional arguments"


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

    def __init__(self, **kw: t.Any) -> None:
        if kw:
            raise TypeError(f"Unconsumed keyword arguments: {kw}")
        super().__init__()

    @classmethod
    def from_model(
        cls, model: capellambse.MelodyModel, element: t.Any
    ) -> ModelObject:
        """Instantiate a ModelObject from existing model elements."""
        ...


# pylint: disable=invalid-name
T = t.TypeVar("T", bound=ModelObject)
U = t.TypeVar("U")
# pylint: enable=invalid-name


class GenericElement:
    """Provides high-level access to a single model element."""

    uuid = xmltools.AttributeProperty("_element", "id", writable=False)
    xtype = property(lambda self: helpers.xtype_of(self._element))
    name = xmltools.AttributeProperty(
        "_element", "name", optional=True, default="(Unnamed {self.xtype})"
    )
    description = xmltools.AttributeProperty(
        "_element", "description", optional=True, returntype=markuptype
    )
    summary = xmltools.AttributeProperty(
        "_element", "summary", optional=True, returntype=markuptype
    )
    diagrams = property(
        lambda self: self._model.diagrams.by_target_uuid(self.uuid)
    )

    constraints: accessors.Accessor

    _required_attrs = frozenset({"uuid", "xtype"})
    _xmltag: t.Optional[str] = None

    @property
    def progress_status(self) -> t.Union[xmltools.AttributeProperty, str]:
        uuid = self._element.get("status")
        if uuid is None:
            return "NOT_SET"

        return self.from_model(self._model, self._model._loader[uuid]).name

    @classmethod
    def from_model(
        cls: t.Type[T], model: capellambse.MelodyModel, element: etree._Element
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
        all_required_attrs = set()
        for basecls in type(self).mro():
            all_required_attrs |= getattr(
                basecls, "_required_attrs", frozenset()
            )
        missing_attrs = all_required_attrs - frozenset(kw)
        if missing_attrs:
            raise TypeError(
                "Missing required keyword arguments: {}".format(
                    ", ".join(sorted(missing_attrs))
                )
            )

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

    def __eq__(self, other: object) -> t.Union[bool]:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._element is other._element

    def __repr__(self) -> str:  # pragma: no cover
        # pylint: disable=unidiomatic-typecheck
        if type(self) is GenericElement:
            mytype = f"Model element ({self.xtype})"
        else:
            mytype = type(self).__name__
        return f"<{mytype} {self.name!r} ({self.uuid})>"


class ElementList(collections.abc.MutableSequence, t.Generic[T]):
    """Provides access to elements without affecting the underlying model."""

    __slots__ = ("_elemclass", "_elements", "_model")

    class _Filter(t.Generic[U]):
        """Filters this list based on an extractor function."""

        __slots__ = ("extractor_func", "parent", "positive", "single")

        def __init__(
            self,
            parent: ElementList[T],
            extract_key: t.Callable[[T], U],
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
            extract_key
                t.Callable that extracts the key from an element
            positive
                Use elements that match (True) or don't (False)
            single
                When listing all matches, return a single element
                instead.  If multiple elements match, it is an error; if
                none match, a ``KeyError`` is raised.
            """
            self.extractor_func = extract_key
            self.parent = parent
            self.positive = positive
            self.single = single

        def extract_key(self, element: T) -> U | str:
            value: U | enum.Enum | str = self.extractor_func(element)
            if isinstance(value, enum.Enum):
                value = value.name
            return value

        def make_values_container(self, *values: U) -> t.Container[U]:
            try:
                return set(values)
            except TypeError:
                return values

        def ismatch(self, element: T, valueset: t.Container[U]) -> bool:
            try:
                value = self.extract_key(element)
            except AttributeError:
                return False

            return self.positive == (value in valueset)

        def __call__(self, *values: U) -> t.Union[T, ElementList[T]]:
            """List all elements that match this filter."""
            valueset = self.make_values_container(*values)
            indices = []
            elements = []
            for i, elm in enumerate(self.parent):
                if self.ismatch(elm, valueset):
                    indices.append(i)
                    elements.append(self.parent._elements[i])

            if not self.single:
                return self.parent._newlist(elements)
            if len(elements) > 1:
                raise KeyError(
                    "Multiple matches for {!r}".format(
                        values[0] if len(values) == 1 else values
                    )
                )
            if len(elements) == 0:
                raise KeyError(values[0] if len(values) == 1 else values)
            return self.parent[indices[0]]  # Ensure proper construction

        def __iter__(self) -> t.Iterator[U | str]:
            """Yield values that result in a non-empty list when filtered for.

            The returned iterator yields all values that, when given to
            :meth:`__call__`, will result in a non-empty list being
            returned.  Consequently, if the original list was empty,
            this iterator will yield no values.

            The order in which the values are yielded is undefined.
            """
            yielded: t.Set[U | str] = set()

            for elm in self.parent:
                key = self.extract_key(elm)
                if key not in yielded:
                    yield key
                    yielded.add(key)

        def __contains__(self, value: U) -> bool:
            valueset = self.make_values_container(value)
            for elm in self.parent:
                if self.ismatch(elm, valueset):
                    return True
            return False

    def __init__(
        self,
        model: capellambse.MelodyModel,
        elements: t.List[etree._Element],
        elemclass: t.Type[T],
    ) -> None:
        self._model = model
        self._elements = elements
        self._elemclass = elemclass

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, collections.abc.Sequence):
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

        return ElementList(
            self._model,
            (
                self._elements + other._elements
                if not reflected
                else other._elements + self._elements
            ),
            (
                self._elemclass
                if self._elemclass is other._elemclass
                else GenericElement
            ),
        )

    def __add__(self, other: object) -> ElementList[T]:
        return self.__add(other)

    def __radd__(self, other: object) -> ElementList[T]:
        return self.__add(other, reflected=True)

    def __sub(
        self, other: object, *, reflected: bool = False
    ) -> ElementList[T]:
        if not isinstance(other, t.Sequence):
            return NotImplemented

        if reflected:
            if isinstance(other, ElementList):
                objclass = other._elemclass
            else:
                objclass = GenericElement
        else:
            objclass = self._elemclass

        base: t.Sequence[t.Any]
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

    def __getitem__(self, idx):  # type: ignore[no-untyped-def]
        if isinstance(idx, slice):
            return self._newlist(self._elements[idx])
        return self._elemclass.from_model(self._model, self._elements[idx])

    @t.overload
    def __setitem__(self, index: int, value: T) -> None:
        ...

    @t.overload
    def __setitem__(self, index: slice, value: t.Iterable[T]) -> None:
        ...

    def __setitem__(self, index, value):  # type: ignore[no-untyped-def]
        del self[index]
        if isinstance(index, slice):
            for i, element in enumerate(value, start=index.start):
                self.insert(i, element)
        else:
            self.insert(index, value)

    def __delitem__(self, index: t.Union[int, slice]) -> None:
        del self._elements[index]

    def __getattr__(
        self,
        attr: str,
    ) -> t.Callable[..., T | ElementList[T]]:
        if attr.startswith("by_"):
            attr = attr[len("by_") :]
            extractor = operator.attrgetter(attr)
            if attr in {"name", "uuid"}:
                # single match only
                return self._Filter(self, extractor, single=True)
            # multiple matches
            return self._Filter(self, extractor)

        if attr.startswith("exclude_") and attr.endswith("s"):
            attr = attr[len("exclude_") : -len("s")]
            extractor = operator.attrgetter(attr)
            return self._Filter(self, extractor, positive=False)

        return getattr(super(), attr)

    def _filter(
        self,
        extract_key: t.Callable[[T], t.Any],
        *values: t.Any,
        positive: bool = True,
        single: bool = False,
    ) -> t.Union[T, ElementList[T]]:
        """Filter elements using an arbitrary extractor function.

        If the extractor returns an :class:`enum.Enum` member for any
        element, the enum member's name will be used for comparisons
        against any ``values``.

        The matched elements are encapsulated in a new instance of the
        same class that this method was called on.  If ``single`` is
        True, then only the single element that was matched is returned
        instead.  If ``single`` is True and nothing matches, a
        ``KeyError`` is raised; otherwise an empty list is returned.

        Parameters
        ----------
        extract_key
            A single-parameter t.Callable that extracts the search key
            from a list element.
        values
            The values to check
        positive
            True to use the elements that match, False to use the
            elements that do **not** match.
        single
            Return a single element instead of a list.  If this is True,
            matching multiple elements is an error.
        """
        return self._Filter(
            self, extract_key, positive=positive, single=single
        )(*values)

    def __dir__(self) -> t.List[str]:  # pragma: no cover
        no_dir_attr = re.compile(r"^(_|as_|pvmt$|nodes$|diagrams?$)")

        def filterable_attrs() -> t.Iterator[str]:
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

    def __str__(self) -> str:  # pragma: no cover
        return "\n".join(f"* {e!s}" for e in self)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{type(self).__name__} at 0x{id(self):016X} {list(self)!r}>"

    def _newlist(self, elements: t.List[etree._Element]) -> ElementList[T]:
        listtype = self._newlist_type()
        return listtype(self._model, elements, self._elemclass)

    def _newlist_type(self) -> t.Type[ElementList]:
        return type(self)

    def insert(self, index: int, value: T) -> None:
        elm: etree._Element = value._element  # type: ignore[attr-defined]
        self._elements.insert(index, elm)


class CachedElementList(ElementList[T], t.Generic[T]):
    """An ElementList that caches the constructed proxies by UUID."""

    class _Filter(ElementList._Filter[U], t.Generic[U]):
        def __call__(self, *values: U) -> t.Union[T, ElementList[T]]:
            newlist: t.Union[T, ElementList[T]] = super().__call__(*values)
            if self.single:
                return newlist

            assert isinstance(newlist, CachedElementList)
            newlist.cacheattr = self.parent.cacheattr  # type: ignore[assignment]
            return newlist

    def __init__(
        self,
        model: capellambse.MelodyModel,
        elements: t.List[etree._Element],
        elemclass: t.Type[T],
        *,
        cacheattr: str | None = None,
    ) -> None:
        """Create a CachedElementList.

        Parameters
        ----------
        cacheattr
            The attribute on the ``model`` to use as cache
        """
        super().__init__(model, elements, elemclass)
        self.cacheattr = cacheattr

    def __getitem__(self, key):  # type: ignore[no-untyped-def]
        elem = super().__getitem__(key)
        if self.cacheattr:
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
        def make_values_container(self, *values: U) -> t.Container[U]:
            try:
                return set(map(operator.methodcaller("lower"), values))
            except TypeError:
                return tuple(map(operator.methodcaller("lower"), values))

    def __init__(
        self,
        model: capellambse.MelodyModel,
        elements: t.List[etree._Element],
        elemclass: t.Any = None,
    ) -> None:
        """Create a MixedElementList.

        Parameters
        ----------
        elemclass
            Ignored; provided for drop-in compatibility.
        """
        del elemclass
        super().__init__(model, elements, GenericElement)

    def __getattr__(
        self, attr: str
    ) -> t.Callable[..., t.Union[GenericElement, ElementList[GenericElement]]]:
        if attr == "by_type":
            return self._LowercaseFilter(
                self, lambda e: type(e).__name__.lower()
            )
        return super().__getattr__(attr)

    def __dir__(self) -> t.List[str]:  # pragma: no cover
        return super().__dir__() + ["by_type", "exclude_types"]
