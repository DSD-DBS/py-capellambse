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

import abc
import itertools
import operator
import typing as t

from lxml import etree

import capellambse
from capellambse import helpers

from . import XTYPE_HANDLERS, S, T, U, build_xtype, element

_NOT_SPECIFIED = object()
"Used to detect unspecified optional arguments"


class Accessor(t.Generic[T], metaclass=abc.ABCMeta):
    """Super class for all Accessor types."""

    __slots__ = (
        "__name__",
        "__objclass__",
    )

    __objclass__: t.Type[t.Any]
    __name__: str

    @t.overload
    def __get__(self, obj: None, objtype: t.Optional[t.Any]) -> Accessor:
        ...

    @t.overload
    def __get__(
        self,
        obj: T,
        objtype: t.Optional[t.Type[T]] = None,
    ) -> t.Union[
        element.ElementList[element.GenericElement],
        element.GenericElement,
    ]:
        ...

    @abc.abstractmethod
    def __get__(
        self, obj: t.Optional[T], objtype: t.Optional[t.Type[t.Any]] = None
    ) -> t.Union[
        Accessor,
        element.ElementList[element.GenericElement],
        element.GenericElement,
    ]:
        pass

    def __set__(self, obj: element.GenericElement, value: t.Any) -> None:
        raise AttributeError("Cannot set this type of attribute")

    def __set_name__(self, owner: t.Type[t.Any], name: str) -> None:
        self.__objclass__ = owner
        self.__name__ = name


class WritableAccessor(Accessor[T], metaclass=abc.ABCMeta):
    """An Accessor that also provides write support on lists it returns."""

    __slots__ = ()

    aslist: t.Optional[t.Type[ElementListCouplingMixin]]

    def __init__(
        self,
        *args: t.Any,
        aslist: t.Optional[t.Type[element.ElementList]],
        **kw: t.Any,
    ) -> None:
        super().__init__(*args, **kw)  # type: ignore[call-arg]

        if aslist is not None:
            self.aslist = type(
                "Coupled" + aslist.__name__,
                (ElementListCouplingMixin, aslist),
                {"_accessor": self},
            )
            self.aslist.__module__ = __name__
        else:
            self.aslist = None

    def create(
        self,
        elmlist: ElementListCouplingMixin,
        /,
        *type_hints: t.Optional[str],
        **kw: t.Any,
    ) -> T:
        """Create and return a new element of type ``elmclass``.

        Parameters
        ----------
        elmlist
            The (coupled) ``ElementList`` to insert the new object into.
        xtype
            The ``xsi:type`` of the new object.
        elmclass
            The concrete ``GenericElement`` subclass to instantiate.
        kw
            Additional keyword arguments that are passed to the
            ``elmclass`` constructor.
        """
        raise TypeError("Cannot create objects")

    def insert(
        self,
        elmlist: ElementListCouplingMixin,
        index: int,
        value: element.ModelObject,
    ) -> None:
        """Insert the ``value`` object into the model.

        The object must be inserted at an appropriate place, so that, if
        ``elmlist`` were to be created afresh, ``value`` would show at
        at index ``index``.
        """
        raise NotImplementedError("Objects cannot be inserted into this list")

    def delete(
        self,
        elmlist: ElementListCouplingMixin,
        obj: element.ModelObject,
    ) -> None:
        """Delete the ``obj`` from the model."""
        raise NotImplementedError("Objects in this list cannot be deleted")

    def _match_xtype(
        self,
        type_1: t.Union[str, object, None] = _NOT_SPECIFIED,
        type_2: t.Union[str, object] = _NOT_SPECIFIED,
        /,
    ) -> t.Tuple[t.Type[T], str]:
        r"""Find the right class for the given ``xsi:type``\ (s)."""
        if type_1 is _NOT_SPECIFIED and type_2 is _NOT_SPECIFIED:
            elmclass = getattr(self, "elmclass", None)
            if elmclass not in (None, element.GenericElement):
                return elmclass
            raise TypeError("No object type specified")

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
                    f"Ambiguous xsi:type {xtp!r}, please qualify: "
                    + ", ".join(repr(i) for i in matches)
                )
            return matches[0]

        if not isinstance(type_1, str):
            raise TypeError(
                f"Expected str as first type, got {type(type_1).__name__!r}"
            )
        candidate_classes: t.Dict[str, t.Type[element.GenericElement]]
        if type_2 is _NOT_SPECIFIED:
            candidate_classes = dict(
                itertools.chain.from_iterable(
                    i.items() for i in XTYPE_HANDLERS.values()
                )
            )
            objtype = type_1
        elif not isinstance(type_2, str):
            raise TypeError(
                f"Expected a str objtype, not {type(objtype).__name__}"
            )
        else:
            candidate_classes = XTYPE_HANDLERS[
                match_xt(type_1, XTYPE_HANDLERS)
            ]
            objtype = type_2

        objtype = match_xt(objtype, candidate_classes)
        return candidate_classes[objtype], objtype


class PhysicalAccessor(t.Generic[T], Accessor[T]):
    """Helper super class for accessors that work with real elements."""

    __slots__ = (
        "aslist",
        "class_",
        "xtypes",
    )

    aslist: t.Optional[t.Type[element.ElementList]]
    class_: t.Type[T]
    xtypes: t.AbstractSet[str]

    def __init__(
        self,
        class_: t.Type[T],
        xtypes: t.Union[
            str,
            t.Type[element.GenericElement],
            t.Iterable[t.Union[str, t.Type[element.GenericElement]]],
        ] = None,
        *,
        aslist: t.Optional[t.Type[element.ElementList[T]]] = None,
    ) -> None:
        super().__init__()
        if xtypes is None:
            self.xtypes = (
                {build_xtype(class_)}
                if class_ is not element.GenericElement
                else set()
            )
        elif isinstance(xtypes, type):
            assert issubclass(xtypes, element.GenericElement)
            self.xtypes = {build_xtype(xtypes)}
        elif isinstance(xtypes, str):
            self.xtypes = {xtypes}
        else:
            self.xtypes = {
                i if isinstance(i, str) else build_xtype(i) for i in xtypes
            }

        self.aslist = aslist
        self.class_ = class_

    def _guess_xtype(self) -> t.Tuple[t.Type[T], str]:
        """Try to guess the type of element that should be created."""
        if self.class_ is element.GenericElement or self.class_ is None:
            raise ValueError("Multiple object types that can be created")
        if not self.xtypes:
            raise ValueError("No matching `xsi:type` found")
        if len(self.xtypes) > 1:
            raise ValueError("Multiple matching `xsi:type`s")
        return self.class_, next(iter(self.xtypes))


class ProxyAccessor(WritableAccessor[T], PhysicalAccessor[T]):
    """Creates proxy objects on the fly."""

    __slots__ = (
        "deep",
        "follow",
        "follow_abstract",
        "rootelem",
    )

    aslist: t.Optional[t.Type[ElementListCouplingMixin]]

    def __init__(
        self,
        class_: t.Type[T],
        xtypes: t.Union[
            str,
            t.Type[element.GenericElement],
            t.Iterable[t.Union[str, t.Type[element.GenericElement]]],
        ] = None,
        *,
        aslist: t.Type[element.ElementList] = None,
        deep: bool = False,
        follow: str = None,
        follow_abstract: bool = True,
        rootelem: t.Union[
            str,
            t.Type[element.GenericElement],
            t.Sequence[t.Union[str, t.Type[element.GenericElement]]],
        ] = None,
    ):
        """Create a ProxyAccessor.

        Parameters
        ----------
        class_
            The proxy class.
        xtypes
            The ``xsi:type``(s) of the child element(s).  If None, then
            the constructed proxy will be passed the original element
            instead of a child.
        aslist
            If None, only a single element must match, which will be
            returned directly.  If not None, must be a subclass of
            :class:`elements.DecoupledElementList`.  It will be used to return a
            list of all matched objects.  Incompatible with ``xtypes =
            None``.
        deep
            True to search the entire XML subtree, False to only
            consider direct children.  Ignored if ``xtype = None``.
        follow
            If not None, must be the name of an attribute on the found
            elements.  That attribute contains a reference to the actual
            element that will be used instead.
        rootelem
            A ``/``-separated list of ``xsi:type``s that defines the
            path from the current object's element to the search root.
            If None, the current element will be used directly.
        """
        super().__init__(class_, xtypes, aslist=aslist)
        self.deep: bool = deep
        self.follow: t.Optional[str] = follow
        self.follow_abstract: bool = follow_abstract
        if rootelem is None:
            self.rootelem: t.Sequence[str] = []
        elif isinstance(rootelem, str):
            self.rootelem = rootelem.split("/")
        elif isinstance(rootelem, type) and issubclass(
            rootelem, element.GenericElement
        ):
            self.rootelem = [build_xtype(rootelem)]
        else:
            self.rootelem = [
                i if isinstance(i, str) else build_xtype(i) for i in rootelem
            ]

    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:  # pragma: no cover
            return self

        elems = [self.__follow_attr(obj, e) for e in self.__getsubelems(obj)]
        elems = [x for x in elems if x is not None]
        if self.aslist is None:
            return no_list(self, obj._model, elems, self.class_)
        return self.aslist(obj._model, elems, self.class_, parent=obj)

    def __getsubelems(
        self, obj: element.GenericElement
    ) -> t.Iterator[etree._Element]:
        yielded_uuids = {None}

        if self.deep:
            it_func = obj._model._loader.iterdescendants_xt
        else:
            it_func = obj._model._loader.iterchildren_xt
        for elem in itertools.chain.from_iterable(
            it_func(i, *iter(self.xtypes)) for i in self.__findroots(obj)
        ):
            elemid = elem.get("id")
            if elemid in yielded_uuids:
                continue

            yielded_uuids.add(elemid)
            yield elem

    def __findroots(
        self, obj: element.GenericElement
    ) -> t.List[etree._Element]:
        roots = [obj._element]
        for xtype in self.rootelem:
            roots = list(
                itertools.chain.from_iterable(
                    obj._model._loader.iterchildren_xt(i, xtype) for i in roots
                )
            )
        return roots

    def __follow_attr(
        self, obj: element.GenericElement, elem: etree._Element
    ) -> etree._Element:
        if self.follow:
            if self.follow in elem.attrib:
                elem = obj._model._loader[elem.attrib[self.follow]]
            else:
                return None
        return self.__follow_href(obj, elem)

    def __follow_href(
        self, obj: element.GenericElement, elem: etree._Element
    ) -> etree._Element:
        href = elem.get("href")
        if href:
            elem = obj._model._loader[href]
        if self.follow_abstract:
            abstype = elem.get("abstractType")
            if abstype is not None:
                elem = obj._model._loader[abstype]
        return elem

    def create(
        self,
        elmlist: ElementListCouplingMixin,
        /,
        *type_hints: t.Optional[str],
        **kw: t.Any,
    ) -> T:
        if self.deep or self.follow or self.rootelem:
            raise AttributeError("Cannot create objects here")

        if type_hints:
            elmclass, xtype = self._match_xtype(*type_hints)
        else:
            elmclass, xtype = self._guess_xtype()

        assert elmclass is not None
        assert isinstance(elmlist._parent, element.GenericElement)
        assert issubclass(elmclass, element.GenericElement)

        parent = elmlist._parent._element
        with elmlist._model._loader.new_uuid(parent) as obj_id:
            obj = elmclass(
                elmlist._model, parent, **kw, xtype=xtype, uuid=obj_id
            )
        return obj

    def insert(
        self,
        elmlist: ElementListCouplingMixin,
        index: int,
        value: element.ModelObject,
    ) -> None:
        if value._model is not elmlist._model:
            raise ValueError("Cannot move elements between models")
        try:
            indexof = elmlist._parent._element.index
            if index > 0:
                parent_index = indexof(elmlist._elements[index - 1]) + 1
            elif index < -1:
                parent_index = indexof(elmlist._elements[index + 1]) - 1
            else:
                parent_index = index
        except ValueError:
            parent_index = len(self._parent)
        elmlist._parent._element.insert(parent_index, value._element)
        elmlist._model._loader.idcache_index(value._element)

    def delete(
        self,
        elmlist: ElementListCouplingMixin,
        obj: element.ModelObject,
    ) -> None:
        assert obj._model is elmlist._model
        elmlist._model._loader.idcache_remove(obj._element)
        elmlist._parent._element.remove(obj._element)


class AttrProxyAccessor(PhysicalAccessor[T]):
    """Provides access to elements that are linked in an attribute."""

    __slots__ = ("attr",)

    def __init__(
        self,
        class_: t.Type[T],
        attr: str,
        *,
        aslist: t.Type[element.ElementList] = None,
    ):
        """Create an AttrProxyAccessor.

        Parameters
        ----------
        class_
            The proxy class.
        attr
            The element attribute to handle.
        aslist
            If None, the attribute contains at most one element
            reference, and either None or the constructed proxy will be
            returned.  If not None, must be a subclass of
            :class:`elements.DecoupledElementList`.  It will be used to return a
            list of all matched objects.  Incompatible with ``xtypes =
            None``.
        """
        super().__init__(class_, aslist=aslist)
        self.attr = attr

    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:  # pragma: no cover
            return self

        elems = []
        next_xtype: t.Optional[str] = None
        for elemref in obj._element.get(self.attr, "").split():
            if "#" in elemref:
                elem = obj._model._loader[elemref]
                if next_xtype is not None:
                    this_xtype = helpers.xtype_of(elem)
                    if this_xtype != next_xtype:  # pragma: no cover
                        raise RuntimeError(
                            "Broken XML: Expected xsi:type {!r}, got {!r}".format(
                                next_xtype, this_xtype
                            )
                        )
                elems.append(elem)
                next_xtype = None
            elif next_xtype is not None:  # pragma: no cover
                raise RuntimeError(
                    "Broken XML: Expected element reference, got xsi:type {!r}".format(
                        elemref
                    )
                )
            else:
                next_xtype = elemref

        if self.aslist is None:
            return no_list(self, obj._model, elems, self.class_)
        return self.aslist(obj._model, elems, self.class_)

    def __set__(
        self,
        obj: element.GenericElement,
        values: t.Union[T, t.Iterable[T]],
    ) -> None:
        if not isinstance(values, t.Iterable):
            values = (values,)
        elif self.aslist is None:
            raise TypeError(
                f"{self.__objclass__.__name__}.{self.__name__}"
                " requires a single item, not an iterable"
            )

        assert isinstance(values, t.Iterable)
        parts: t.List[str] = []
        for value in values:
            if not value._model is obj._model:
                raise ValueError("Cannot set elements from different models")
            link = obj._model._loader.create_link(obj._element, value._element)
            parts.append(link)
        obj._element.set(self.attr, " ".join(parts))


class AlternateAccessor(PhysicalAccessor[T]):
    """Provides access to an "alternate" form of the object."""

    __slots__ = ()

    def __init__(
        self,
        class_: t.Type[T],
    ):
        super().__init__(class_)

    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:  # pragma: no cover
            return self
        return self.class_.from_model(obj._model, obj._element)


class ParentAccessor(PhysicalAccessor[T]):
    """Accesses the parent XML element."""

    __slots__ = ()

    def __init__(
        self,
        class_: t.Type[T],
    ):
        super().__init__(class_)

    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:  # pragma: no cover
            return self
        return self.class_.from_model(
            obj._model,
            obj._element.getparent(),
        )


class CustomAccessor(PhysicalAccessor[T]):
    """Customizable alternative to the ProxyAccessor."""

    __slots__ = (
        "elmfinders",
        "elmmatcher",
        "matchtransform",
    )

    def __init__(
        self,
        class_: t.Type[T],
        *elmfinders: t.Callable[
            [element.GenericElement], t.Iterable[element.GenericElement]
        ],
        elmmatcher: t.Callable[
            [U, element.GenericElement], bool
        ] = operator.contains,
        matchtransform: t.Callable[[element.GenericElement], U] = (
            lambda e: e
        ),
        aslist: t.Type[element.ElementList] = None,
    ) -> None:
        """Create a CustomAccessor.

        Parameters
        ----------
        class_
            The target subclass of ``GenericElement``
        elmfinders
            Functions that are called on the current element.  Each
            returns an iterable of possible targets.
        elmmatcher
            Function that is called with the transformed target element
            and the current element to determine if the untransformed
            target should be accepted.
        matchtransform
            Function that transforms a target so that it can be used by
            the matcher function.
        """
        super().__init__(class_, aslist=aslist)
        self.elmfinders = elmfinders
        self.elmmatcher = elmmatcher
        self.matchtransform = matchtransform

    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:
            return self

        elms = itertools.chain.from_iterable(f(obj) for f in self.elmfinders)
        matches = [
            e._element
            for e in elms
            if self.elmmatcher(self.matchtransform(e), obj)
        ]
        if self.aslist is None:
            return no_list(self, obj._model, matches, self.class_)
        return self.aslist(obj._model, matches, self.class_)


class AttributeMatcherAccessor(ProxyAccessor[T]):
    __slots__ = (
        "_AttributeMatcherAccessor__aslist",
        "attributes",
    )

    def __init__(
        self,
        class_: t.Type[T],
        xtypes: t.Union[
            str,
            t.Type[element.GenericElement],
            t.Iterable[t.Union[str, t.Type[element.GenericElement]]],
        ] = None,
        *,
        aslist: t.Optional[t.Type[element.ElementList]] = None,
        attributes: t.Dict[str, t.Any],
        **kwargs,
    ) -> None:
        super().__init__(
            class_, xtypes, aslist=element.MixedElementList, **kwargs
        )
        self.__aslist = aslist
        self.attributes = attributes

    def __get__(self, obj, objtype=None):
        if obj is None:  # pragma: no cover
            return self

        elements = super().__get__(obj, objtype)
        matches = []
        for elm in elements:
            try:
                if all(
                    getattr(elm, k) == v for k, v in self.attributes.items()
                ):
                    matches.append(elm._element)
            except AttributeError:
                pass

        if self.__aslist is None:
            return no_list(self, obj._model, matches, self.class_)
        return self.__aslist(obj._model, matches, self.class_)


class SpecificationAccessor(Accessor):
    """Provides access to linked specifications."""

    __slots__ = ()

    class _Specification(t.MutableMapping[str, str]):
        def __init__(
            self, model: capellambse.MelodyModel, elm: etree._Element
        ) -> None:
            self._model = model
            self.element = elm

        def __delitem__(self, k: str) -> None:
            i, lang_elem = self._index_of(k)
            body_elem = self._body_at(k, i)
            self.element.remove(lang_elem)
            self.element.remove(body_elem)

        def __getitem__(self, k: str) -> str:
            i, _ = self._index_of(k)
            return helpers.unescape_linked_text(
                self._model._loader, self._body_at(k, i).text
            )

        def __iter__(self) -> t.Iterator[str]:
            for i in self.element.iterchildren("languages"):
                yield i.text or ""

        def __len__(self) -> int:
            return sum(1 for _ in self)

        def __setitem__(self, k: str, v: str) -> None:
            try:
                i, lang = self._index_of(k)
            except KeyError:
                self.element.append(body := self.element.makeelement("bodies"))
                self.element.append(
                    lang := self.element.makeelement("languages")
                )
                body.text = v
                lang.text = k
            else:
                body = self._body_at(k, i)
                body.text = v

        def _index_of(self, k: str) -> t.Tuple[int, etree._Element]:
            for i, elm in enumerate(self.element.iterchildren("languages")):
                if elm.text == k:
                    return i, elm

            raise KeyError(k)

        def _body_at(self, k: str, i: int) -> etree._Element:
            try:
                return next(
                    itertools.islice(
                        self.element.iterchildren("bodies"), i, i + 1
                    )
                )
            except StopIteration:
                raise KeyError(k) from None

        def __str__(self) -> str:  # pragma: no cover
            return "\n".join(
                f"* language'{e!s}': {self.__getitem__(e)}" for e in self
            )

        def __repr__(self) -> str:  # pragma: no cover
            return (
                f"<{type(self).__name__} at 0x{id(self):016X} {list(self)!r}>"
            )

        @property
        def text(self) -> str:
            """Return ``self["capella:linkedText"]``."""
            return self["capella:linkedText"]

    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:  # pragma: no cover
            return self

        try:
            spec_elm = next(obj._element.iterchildren("ownedSpecification"))
        except StopIteration:
            raise AttributeError("No specification found") from None

        return self._Specification(obj._model, spec_elm)


class ReferenceSearchingAccessor(PhysicalAccessor):
    __slots__ = ("attrs",)

    attrs: t.Tuple[str, ...]

    def __init__(
        self,
        class_: t.Type[element.GenericElement],
        *attrs: str,
        aslist: t.Type[element.ElementList] = None,
    ) -> None:
        super().__init__(class_, aslist=aslist)
        self.attrs = attrs

    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:  # pragma: no cover
            return self

        matches: t.List[etree._Element] = []
        for candidate in obj._model.search(self.class_):
            for attr in self.attrs:
                try:
                    value = getattr(candidate, attr)
                except AttributeError:
                    continue
                if (
                    isinstance(value, element.ElementList)
                    and obj in value
                    or isinstance(value, element.GenericElement)
                    and obj == value
                ):
                    matches.append(candidate._element)
                    break
        if self.aslist is None:
            return no_list(self, obj._model, matches, self.class_)
        return self.aslist(obj._model, matches, self.class_)


def no_list(
    desc: Accessor,
    model: capellambse.MelodyModel,
    elems: t.Sequence[etree._Element],
    class_: t.Type[T],
) -> t.Optional[T]:
    """Return a single element or None instead of a list of elements.

    Parameters
    ----------
    desc
        The descriptor that called this function
    model
        The ``MelodyModel`` instance
    elems
        t.List of elements that was matched
    class_
        The ``GenericElement`` subclass to instantiate
    parent
        Ignored.
    """
    if not elems:  # pragma: no cover
        return None
    if len(elems) > 1:  # pragma: no cover
        raise RuntimeError(
            "Expected 1 object for {}.{}, got {}".format(
                desc.__objclass__.__name__, desc.__name__, len(elems)
            )
        )
    return class_.from_model(model, elems[0])


class ElementListCouplingMixin(element.ElementList[T], t.Generic[T]):
    """Couples an ElementList with an Accessor to enable write support.

    This class is meant to be subclassed further, where the subclass has
    both this class and the originally intended one as base classes (but
    no other ones, i.e. there must be exactly two bases).  The Accessor
    then inserts itself as the ``_accessor`` class variable on the new
    subclass.  This allows the mixed-in methods to delegate actual model
    modifications to the Accessor.
    """

    _accessor: t.ClassVar[WritableAccessor[T]]

    def __init__(
        self, *args: t.Any, parent: element.ModelObject, **kw: t.Any
    ) -> None:
        assert type(self)._accessor
        assert isinstance(parent, element.GenericElement)

        super().__init__(*args, **kw)
        self._parent = parent

    @t.overload
    def __setitem__(self, index: int, value: T) -> None:
        ...

    @t.overload
    def __setitem__(self, index: slice, value: t.Iterable[T]) -> None:
        ...

    def __setitem__(self, index, value):
        assert self._parent is not None
        del self[index]
        if isinstance(index, slice):
            for i, elm in enumerate(value, start=index.start):
                self.insert(i, elm)
        else:
            self.insert(index, value)

    def __delitem__(self, index: t.Union[int, slice]) -> None:
        assert self._parent is not None
        if not isinstance(index, slice):
            index = slice(index, index + 1)
        for obj in self[index]:
            type(self)._accessor.delete(self, obj)
        super().__delitem__(index)

    def _newlist_type(self) -> t.Type[element.ElementList[T]]:
        assert len(type(self).__bases__) == 2
        assert type(self).__bases__[0] is ElementListCouplingMixin
        return type(self).__bases__[1]

    def create(
        self, *args: t.Optional[str], **kw: t.Any
    ) -> element.GenericElement:
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
        assert self._parent is not None
        acc = type(self)._accessor
        assert isinstance(acc, WritableAccessor)
        newobj = acc.create(self, *args, **kw)
        self._newlist_type().insert(self, len(self), newobj)
        return newobj

    def delete_all(self, **kw: t.Any) -> None:
        """Delete all matching objects from the model."""
        indices: t.List[int] = []
        for i, obj in enumerate(self):
            if all(getattr(obj, k) == v for k, v in kw.items()):
                indices.append(i)

        for index in reversed(indices):
            del self[index]

    def insert(self, index: int, value: T) -> None:
        assert self._parent is not None
        acc = type(self)._accessor
        assert isinstance(acc, WritableAccessor)
        acc.insert(self, index, value)
        self._newlist_type().insert(self, index, value)
