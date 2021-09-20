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
import functools
import itertools
import operator
import typing as t

from lxml import etree

import capellambse
from capellambse import helpers

from . import T, U, build_xtype, element


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
        element.DecoupledElementList[element.GenericElement],
        element.GenericElement,
    ]:
        ...

    @abc.abstractmethod
    def __get__(
        self, obj: t.Optional[T], objtype: t.Optional[t.Type[t.Any]] = None
    ) -> t.Union[
        Accessor,
        element.DecoupledElementList[element.GenericElement],
        element.GenericElement,
    ]:
        pass

    def __set__(self, obj: element.GenericElement, value: t.Any) -> None:
        raise AttributeError("Cannot set this type of attribute")

    def __set_name__(self, owner: t.Type[t.Any], name: str) -> None:
        self.__objclass__ = owner
        self.__name__ = name


class PhysicalAccessor(t.Generic[T], Accessor[T]):
    """Helper super class for accessors that work with real elements."""

    __slots__ = (
        "aslist",
        "class_",
        "xtypes",
    )

    aslist: t.Callable[
        ...,
        t.Union[
            element.GenericElement,
            element.DecoupledElementList[element.GenericElement],
            None,
        ],
    ]
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
        aslist: t.Type[element.DecoupledElementList[T]] = None,
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

        self.aslist = aslist or functools.partial(  # type: ignore[assignment]
            no_list, self  # type: ignore[arg-type]
        )
        self.class_ = class_


class ProxyAccessor(PhysicalAccessor[T]):
    """Creates proxy objects on the fly."""

    __slots__ = (
        "deep",
        "follow",
        "follow_abstract",
        "rootelem",
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
        aslist: t.Type[element.DecoupledElementList] = None,
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
        return self.aslist(obj._model, elems, self.class_, parent=obj._element)

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


class AttrProxyAccessor(PhysicalAccessor[T]):
    """Provides access to elements that are linked in an attribute."""

    __slots__ = ("attr",)

    def __init__(
        self,
        class_: t.Type[T],
        attr: str,
        *,
        aslist: t.Type[element.DecoupledElementList] = None,
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

        return self.aslist(obj._model, elems, self.class_, parent=None)


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
        aslist: t.Type[element.DecoupledElementList] = None,
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
        return self.aslist(obj._model, matches, self.class_, parent=None)


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
        aslist: t.Type[element.DecoupledElementList] = None,
        attributes: t.Dict[str, t.Any],
        **kwargs,
    ) -> None:
        super().__init__(
            class_, xtypes, aslist=element.DecoupledMixedElementList, **kwargs
        )
        self.__aslist = aslist or functools.partial(
            no_list, self  # type: ignore[arg-type]
        )
        self.attributes = attributes

    def __get__(self, obj, objtype=None):
        if obj is None:  # pragma: no cover
            return self

        elements = super().__get__(obj, objtype)
        matches = []
        for element in elements:
            try:
                if all(
                    getattr(element, k) == v
                    for k, v in self.attributes.items()
                ):
                    matches.append(element._element)
            except AttributeError:
                pass

        return self.__aslist(obj._model, matches, self.class_, parent=None)


class SpecificationAccessor(Accessor):
    """Provides access to linked specifications."""

    __slots__ = ()

    class _Specification(t.MutableMapping[str, str]):
        def __init__(
            self, model: capellambse.MelodyModel, element: etree._Element
        ) -> None:
            self._model = model
            self.element = element

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
            for i, element in enumerate(
                self.element.iterchildren("languages")
            ):
                if element.text == k:
                    return i, element

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
        aslist: t.Type[element.DecoupledElementList] = None,
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
                    isinstance(value, element.DecoupledElementList)
                    and obj in value
                    or isinstance(value, element.GenericElement)
                    and obj == value
                ):
                    matches.append(candidate._element)
                    break
        return self.aslist(obj._model, matches, self.class_, parent=None)


def no_list(
    desc: Accessor,
    model: capellambse.MelodyModel,
    elems: t.Sequence[etree._Element],
    class_: t.Type[T],
    *,
    parent: t.Any = None,
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
    del parent
    if not elems:  # pragma: no cover
        return None
    if len(elems) > 1:  # pragma: no cover
        raise RuntimeError(
            "Expected 1 object for {}.{}, got {}".format(
                desc.__objclass__.__name__, desc.__name__, len(elems)
            )
        )
    return class_.from_model(model, elems[0])
