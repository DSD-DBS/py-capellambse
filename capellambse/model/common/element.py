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
import itertools
import operator
import re
import typing as t

from lxml import etree

import capellambse
from capellambse import helpers
from capellambse.loader import xmltools

from . import XTYPE_HANDLERS, S, T, U, accessors, enumliteral, markuptype

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

    @classmethod
    def from_model(
        cls, model: capellambse.MelodyModel, element: t.Any
    ) -> ModelObject:
        """Instantiate a ModelObject from existing model elements."""
        ...


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
    progress_status = property(lambda self: enumliteral(self, "status"))

    constraints: accessors.Accessor

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

    def __init__(self, model: capellambse.MelodyModel, **kw: t.Any) -> None:
        super().__init__()
        if self._xmltag is None:
            raise TypeError(
                f"Cannot instantiate {type(self).__name__} directly"
            )
        self._model = model
        self._element: etree._Element = etree.Element(self._xmltag)

        for key, val in kw.items():
            if not isinstance(
                getattr(type(self), key),
                (accessors.Accessor, xmltools.AttributeProperty),
            ):
                raise TypeError(f"Cannot set {key!r} on {type(self).__name__}")
            setattr(self, key, val)

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


class DecoupledElementList(collections.abc.MutableSequence, t.Generic[T]):
    """Provides access to elements without affecting the underlying model."""

    __slots__ = ("_elemclass", "_elements", "_model", "_parent")

    class _Filter(t.Generic[U]):
        """Filters this list based on an extractor function."""

        __slots__ = ("extractor_func", "parent", "positive", "single")

        def __init__(
            self,
            parent: DecoupledElementList[T],
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

        def extract_key(self, element: T) -> U:
            value = self.extractor_func(element)
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

        def __call__(self, *values: U) -> t.Union[T, DecoupledElementList[T]]:
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

        def __iter__(self) -> t.Iterator[U]:
            """Yield values that result in a non-empty list when filtered for.

            The returned iterator yields all values that, when given to
            :meth:`__call__`, will result in a non-empty list being
            returned.  Consequently, if the original list was empty,
            this iterator will yield no values.

            The order in which the values are yielded is undefined.
            """
            yielded: t.Union[t.Set[U], t.List[U]] = set()
            assert isinstance(yielded, set)
            add_to_yielded: t.Callable[[U], None] = yielded.add

            for elm in self.parent:
                key = self.extract_key(elm)
                if key not in yielded:
                    yield key
                    try:
                        add_to_yielded(key)
                    except TypeError:
                        yielded = list(yielded)
                        add_to_yielded = yielded.append
                        add_to_yielded(key)

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
        *,
        parent: t.Any = None,
    ) -> None:
        del parent

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
    ) -> DecoupledElementList[T]:
        if not isinstance(other, DecoupledElementList):
            return NotImplemented
        if self._model is not other._model:
            raise ValueError("Cannot add ElementLists from different models")

        return DecoupledElementList(
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

    def __add__(self, other: object) -> DecoupledElementList[T]:
        return self.__add(other)

    def __radd__(self, other: object) -> DecoupledElementList[T]:
        return self.__add(other, reflected=True)

    def __sub(
        self, other: object, *, reflected: bool = False
    ) -> DecoupledElementList[T]:
        if not isinstance(other, t.Sequence):
            return NotImplemented

        if reflected:
            if isinstance(other, DecoupledElementList):
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

        return DecoupledElementList(
            self._model,
            [i._element for i in base if i.uuid not in excluded],
            objclass,
        )

    def __sub__(self, other: object) -> DecoupledElementList[T]:
        """Return a new list without elements found in ``other``."""
        return self.__sub(other)

    def __rsub__(self, other: object) -> DecoupledElementList[T]:
        return self.__sub(other, reflected=True)

    def __len__(self) -> int:
        return len(self._elements)

    @t.overload
    def __getitem__(self, idx: int) -> T:
        ...

    @t.overload
    def __getitem__(self, idx: slice) -> DecoupledElementList[T]:
        ...

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return self._newlist(self._elements[idx])
        return self._elemclass.from_model(self._model, self._elements[idx])

    @t.overload
    def __setitem__(self, index: int, value: T) -> None:
        ...

    @t.overload
    def __setitem__(self, index: slice, value: t.Iterable[T]) -> None:
        ...

    def __setitem__(self, index, value):
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
    ) -> t.Callable[..., t.Union[T, DecoupledElementList[T]]]:
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
    ) -> t.Union[T, DecoupledElementList[T]]:
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
        no_dir_attr = re.compile(r"^(_|as_|pvmt$|nodes$)")

        def filterable_attrs() -> t.Iterator[str]:
            for obj in self:
                for attr in dir(obj):
                    if not no_dir_attr.search(attr) and isinstance(
                        getattr(obj, attr), str
                    ):
                        yield attr

        return list(
            itertools.chain.from_iterable(
                (f"by_{a}", f"exclude_{a}s") for a in filterable_attrs()
            )
        )

    def __str__(self) -> str:  # pragma: no cover
        return "\n".join(f"* {e!s}" for e in self)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{type(self).__name__} at 0x{id(self):016X} {list(self)!r}>"

    def _newlist(
        self, elements: t.List[etree._Element]
    ) -> DecoupledElementList[T]:
        return type(self)(self._model, elements, self._elemclass)

    def insert(self, index: int, value: T) -> None:
        elm: etree._Element = value._element  # type: ignore[attr-defined]
        self._elements.insert(index, elm)


class ElementList(DecoupledElementList[T], t.Generic[T]):
    """Provides access to a list of elements and allows simple filtering."""

    __slots__ = ("_elemclass", "_elements", "_model", "_parent")

    def __init__(
        self,
        model: capellambse.MelodyModel,
        elements: t.List[etree._Element],
        elemclass: t.Type[T],
        *,
        parent: t.Optional[etree._Element],
        **kw: t.Any,
    ) -> None:
        super().__init__(model, elements, elemclass, **kw)
        self._parent = parent

    def __setitem__(self, index, value):
        if self._parent is None:
            raise ValueError("Cannot set elements in filtered lists")
        super().__setitem__(index, value)

    def __delitem__(self, index: t.Union[int, slice]) -> None:
        if self._parent is None:
            raise ValueError("Cannot remove elements from filtered lists")
        if not isinstance(index, slice):
            index = slice(index, index + 1)
        for elm in self._elements[index]:
            if elm not in self._parent:
                raise RuntimeError(
                    f"Illegal state: Element {elm!r}"
                    f" is not a child of {self._parent!r}"
                )
            self._model._loader.idcache_remove(elm)
            self._parent.remove(elm)
        super().__delitem__(index)

    def _newlist(self, elements: t.List[etree._Element]) -> ElementList[T]:
        return type(self)(self._model, elements, self._elemclass, parent=None)

    @t.overload
    def create(self, objtype: str, **kw: t.Any) -> GenericElement:
        ...

    @t.overload
    def create(
        self, layer: t.Optional[str], objtype: str, **kw: t.Any
    ) -> GenericElement:
        ...

    def create(
        self,
        layertype: str,
        objtype: t.Union[str, object] = _NOT_SPECIFIED,
        **kw: t.Any,
    ) -> GenericElement:
        """Make a new model object (instance of GenericElement).

        Instead of specifying the full ``xsi:type`` including the
        namespace, you can also pass in just the part after the ``:``
        separator.  If this is unambiguous, the appropriate
        layer-specific type will be selected automatically.

        This method can be called with or without the ``layertype``
        argument.  If a layertype is not given, all layers will be tried
        to find an appropriate ``xsi:type`` handler.  Note that setting
        the layertype to ``None`` explicitly is different from not
        specifying it at all; ``None`` tries only the "Transverse
        modelling" type elements.

        Parameters
        ----------
        layertype
            The ``xsi:type`` of the architectural layer on which this
            element will eventually live (see above).
        objtype
            The ``xsi:type`` of the object to create.
        """
        # TODO Rework in a more abstract way
        #
        # Plugging generic logic for element creation into the generic
        # ElementList class will likely become insufficient very soon,
        # when more complex objects need to be handled.
        #
        # Instead, consider delegating the actual creation logic to the
        # ``Accessor`` instance that created this ``ElementList``.  If
        # ``.create()`` is called on an ``ElementList`` that was
        # filtered, the same ValueError should be raised as it is now.
        #
        # Similarly, deleting elements should be delegated to the
        # Accessor as well, for the same reasons.

        # TODO Sanity checks
        # Currently, this method allows creating arbitrary elements
        # anywhere in the tree, even if it does not make sense
        # semantically.  Instead, only allow creating elements that can
        # naturally appear in this list; this should be significantly
        # easier when delegating to the Accessor as proposed by the
        # previous paragraph.
        if not (objtype is _NOT_SPECIFIED or isinstance(objtype, str)):
            raise TypeError(
                f"Expected a str objtype, not {type(objtype).__name__}"
            )
        if self._parent is None:
            raise ValueError("Cannot create elements in filtered lists")

        def match_xt(xtp: S, itr: t.Iterable[S]) -> S:
            matches: t.List[S] = []
            for i in itr:
                if (
                    xtp is i is None
                    or i is not None
                    and xtp in (i, i.split(":")[-1])
                ):
                    matches.append(i)
            if not matches:
                raise ValueError(f"Invalid or unknown xsi:type {xtp!r}")
            if len(matches) > 1:
                raise ValueError(
                    "Ambiguous xsi:type {!r}, please qualify: {!s}".format(
                        xtp, ", ".join(repr(i) for i in matches)
                    )
                )
            return matches[0]

        candidate_classes: t.Dict[str, t.Type[GenericElement]]
        if objtype is _NOT_SPECIFIED:
            candidate_classes = dict(
                itertools.chain.from_iterable(
                    i.items() for i in XTYPE_HANDLERS.values()
                )
            )
            xt_obj = layertype
        else:
            assert isinstance(objtype, str)
            candidate_classes = XTYPE_HANDLERS[
                match_xt(layertype, XTYPE_HANDLERS)
            ]
            xt_obj = objtype

        xt_obj = match_xt(xt_obj, candidate_classes)
        cls = candidate_classes[xt_obj]
        with self._model._loader.new_uuid(self._parent) as obj_id:
            obj = cls(self._model, **kw, uuid=obj_id)
            obj._element.set(helpers.ATT_XT, xt_obj)
            self.append(obj)
        return obj

    def decoupled(self) -> DecoupledElementList[T]:
        """Create a new decoupled list with the same contents as this one."""
        return DecoupledElementList(
            self._model, self._elements, self._elemclass
        )

    def delete_all(self, **kw: t.Any) -> None:
        """Delete all matching objects from the model."""
        indices: t.List[int] = []
        for i, obj in enumerate(self):
            if all(getattr(obj, k) == v for k, v in kw.items()):
                indices.append(i)

        for index in reversed(indices):
            del self[index]

    def insert(self, index: int, value: T) -> None:
        if self._parent is None:
            raise ValueError("Cannot insert elements into filtered lists")

        try:
            if index > 0:
                parent_index = (
                    self._parent.index(self._elements[index - 1]) + 1
                )
            elif index < -1:
                parent_index = (
                    self._parent.index(self._elements[index + 1]) - 1
                )
            else:
                parent_index = index
        except ValueError:
            parent_index = len(self._parent)

        elm: etree._Element = value._element  # type: ignore[attr-defined]
        self._elements.insert(index, elm)
        self._parent.insert(parent_index, elm)
        self._model._loader.idcache_index(elm)


class CachedElementList(ElementList):
    """An ElementList that caches the constructed proxies by UUID."""

    class _Filter(ElementList._Filter, t.Generic[T, U]):
        def __call__(self, *values):
            newlist = super().__call__(*values)
            if self.single:
                return newlist

            assert isinstance(newlist, CachedElementList)
            newlist.cacheattr = self.parent.cacheattr
            return newlist

    def __init__(
        self,
        model: capellambse.MelodyModel,
        elements: t.List[etree._Element],
        elemclass: t.Type[T],
        *,
        cacheattr: str = None,
        parent: t.Optional[etree._Element],
        **kw: t.Any,
    ) -> None:
        """Create a CachedElementList.

        Parameters
        ----------
        cacheattr
            The attribute on the ``model`` to use as cache
        """
        del parent

        super().__init__(model, elements, elemclass, parent=None, **kw)
        self.cacheattr = cacheattr

    def __getitem__(self, key: int) -> T:
        elem = super().__getitem__(key)
        if self.cacheattr:
            try:
                cache = getattr(self._model, self.cacheattr)
            except AttributeError:
                cache = {}
                setattr(self._model, self.cacheattr, cache)
            elem = cache.setdefault(elem.uuid, elem)
        return elem


class DecoupledMixedElementList(DecoupledElementList[GenericElement]):
    """DecoupledElementList that handles proxies using ``XTYPE_HANDLERS``."""

    class _LowercaseFilter(t.Generic[T, U], ElementList._Filter[U]):
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
        **kw: t.Any,
    ) -> None:
        """Create a MixedElementList.

        Parameters
        ----------
        elemclass
            Ignored; provided for drop-in compatibility.
        """
        del elemclass
        super().__init__(model, elements, GenericElement, **kw)

    def __getattr__(
        self, attr: str
    ) -> t.Callable[..., t.Union[t.Any, DecoupledElementList[t.Any]]]:
        if attr == "by_type":
            return self._LowercaseFilter(
                self, lambda e: type(e).__name__.lower()
            )
        return super().__getattr__(attr)

    def __dir__(self) -> t.List[str]:  # pragma: no cover
        return super().__dir__() + ["by_type", "exclude_types"]


class MixedElementList(DecoupledMixedElementList, ElementList):
    """ElementList that handles proxies using ``XTYPE_HANDLERS``."""
