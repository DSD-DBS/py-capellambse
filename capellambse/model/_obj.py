# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

__all__ = [
    "ModelObject",
    "ModelElement",
    "ElementList",
    "CachedElementList",
    "MixedElementList",
    "ElementListMapKeyView",
    "ElementListMapItemsView",
    "ElementListCouplingMixin",
]

import collections.abc as cabc
import contextlib
import enum
import inspect
import logging
import operator
import re
import textwrap
import typing as t

import markupsafe
import typing_extensions as te
from lxml import etree

import capellambse
from capellambse import helpers

from . import T, U, _descriptors, _pods, _styleclass, _xtype

LOGGER = logging.getLogger(__name__)


_NOT_SPECIFIED = object()
"Used to detect unspecified optional arguments"

_MapFunction: te.TypeAlias = (
    "cabc.Callable[[T], ModelElement | cabc.Iterable[ModelElement]]"
)

_TERMCELL: tuple[int, int] | None = None
_ICON_CACHE: dict[tuple[str, str, int], t.Any] = {}


class ModelObject(t.Protocol):
    """A class that wraps a specific model object.

    Most of the time, you'll want to subclass the concrete
    ``ModelElement`` class. However, some special classes (e.g. AIRD
    diagrams) provide a compatible interface, but it doesn't make sense
    to wrap a specific XML element. This protocol class is used in type
    annotations to catch both "normal" ModelElement subclasses and the
    mentioned special cases.
    """

    @property
    def _model(self) -> capellambse.MelodyModel: ...

    @property
    def _element(self) -> etree._Element: ...

    def __init__(
        self,
        model: capellambse.MelodyModel,
        parent: etree._Element,
        xmltag: str | None,
        /,
        **kw: t.Any,
    ) -> None:
        """Create a new model object.

        Parameters
        ----------
        model
            The model instance.
        parent
            The parent XML element below which to create a new object.
        xmltag
            Override the XML tag to use for this element.
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


class ModelElement:
    """A model element.

    This is the common base class for all elements of a model. In terms
    of the metamodel, it combines the role of
    ``modellingcore.ModelElement`` and all its superclasses; references
    to any superclass should be modified to use this class instead.
    """

    uuid = _pods.StringPOD("id", writable=False)
    """The universally unique identifier of this object.

    This attribute is automatically populated when the object is
    instantiated, and cannot be changed afterwards. It is however
    possible to specify the UUID when instantiating the object, in which
    case it will be used instead of generating a new one.

    The UUID may be used in hashmaps and the like, as it is guaranteed
    to not change during the object's lifetime and across model
    save/reload cycles.
    """

    sid = _pods.StringPOD("sid")
    """The unique system identifier of this object."""

    xtype = property(lambda self: helpers.xtype_of(self._element))
    name = _pods.StringPOD("name")
    description = _pods.HTMLStringPOD("description")
    summary = _pods.StringPOD("summary")
    diagrams: _descriptors.Accessor[capellambse.model.diagram.Diagram]
    diagrams = property(  # type: ignore[assignment]
        lambda self: self._model.diagrams.by_target(self)
    )
    visible_on_diagrams = property(
        lambda self: self._model.diagrams.by_semantic_nodes(self)
    )

    parent: _descriptors.ParentAccessor
    constraints: _descriptors.Accessor
    property_value_packages: _descriptors.Accessor

    _required_attrs = frozenset({"uuid", "xtype"})
    _xmltag: str | None = None

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

    @property
    def progress_status(self) -> str:
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
        ModelElement
            An instance of ModelElement (or a more appropriate subclass,
            if any) that wraps the given XML element.
        """
        class_ = cls
        if class_ is ModelElement:
            xtype = helpers.xtype_of(element)
            if xtype is not None:
                with contextlib.suppress(KeyError):
                    class_ = _xtype.XTYPE_HANDLERS[None][xtype]
            if class_ is not cls:
                return class_.from_model(model, element)
        self = class_.__new__(class_)
        self._model = model
        self._element = element
        return self

    @property
    def layer(self) -> capellambse.metamodel.cs.ComponentArchitecture:
        """Find the layer that this element belongs to.

        Note that an architectural layer normally does not itself have a
        parent layer.

        Raises
        ------
        AttributeError
            Raised if this element is not nested below a layer.
        """
        import capellambse.metamodel as mm

        obj: ModelElement | None = self
        assert obj is not None
        while obj := getattr(obj, "parent", None):
            if isinstance(obj, mm.cs.ComponentArchitecture):
                return obj
        raise AttributeError(
            f"No parent layer found for {self._short_repr_()}"
        )

    def __init__(
        self,
        model: capellambse.MelodyModel,
        parent: etree._Element,
        xmltag: str | None = None,
        /,
        *,
        uuid: str,
        **kw: t.Any,
    ) -> None:
        all_required_attrs: set[str] = set()
        for basecls in type(self).mro():
            all_required_attrs |= getattr(
                basecls, "_required_attrs", frozenset()
            )
        missing_attrs = all_required_attrs - frozenset(kw) - {"uuid"}
        if missing_attrs:
            mattrs = ", ".join(sorted(missing_attrs))
            raise TypeError(f"Missing required keyword arguments: {mattrs}")

        super().__init__()
        if xmltag is None:
            xmltag = self._xmltag
        if xmltag is None:
            raise TypeError(
                f"Cannot instantiate {type(self).__name__} directly"
            )
        self._model = model
        self._element: etree._Element = etree.Element(xmltag)
        parent.append(self._element)
        try:
            self.uuid = uuid
            for key, val in kw.items():
                if key == "xtype":
                    self._element.set(helpers.ATT_XT, val)
                elif not isinstance(
                    getattr(type(self), key),
                    _descriptors.Accessor | _pods.BasePOD,
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

    def __dir__(self) -> list[str]:
        badacc = (_descriptors.DeprecatedAccessor,)
        cls = type(self)
        attrs: list[str] = []
        for i in super().__dir__():
            try:
                acc = getattr(cls, i)
            except Exception:
                continue
            if isinstance(acc, badacc):
                continue
            if isinstance(acc, _descriptors.Alias) and acc.dirhide:
                continue
            try:
                if getattr(acc, "__deprecated__", None):
                    continue
            except Exception:
                continue
            attrs.append(i)
        return attrs

    def __repr__(self) -> str:  # pragma: no cover
        header = self._short_repr_()

        attrs: list[str] = []
        for attr in dir(self):
            if attr.startswith("_"):
                continue

            acc = getattr(type(self), attr, None)
            if isinstance(acc, _descriptors.Backref):
                classes = ", ".join(i.__name__ for i in acc.target_classes)
                attrs.append(
                    f".{attr} = ... # backreference to {classes}"
                    " - omitted: can be slow to compute"
                )
                continue

            if attr.startswith("all_"):
                attrs.append(f".{attr} = ... # omitted")
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
        if type(self) is ModelElement:
            mytype = f"Model element ({self.xtype})"
        else:
            mytype = type(self).__name__

        if self.name:
            name = f" {self.name!r}"
        else:
            name = ""

        if capellambse.model.diagram.REPR_DRAW:
            global _TERMCELL
            if _TERMCELL is None:
                try:
                    _TERMCELL = helpers.get_term_cell_size()
                except ValueError as err:
                    LOGGER.warning("Cannot determine term cell size: %s", err)
                    _TERMCELL = (0, 0)
            size = (_TERMCELL[1] or 13) - 2
            icon = self._get_icon("termgraphics", size=size) or b""
            assert isinstance(icon, bytes)
        else:
            icon = b""
        return f"<{icon.decode()}{mytype}{name} ({self.uuid})>"

    def __html__(self) -> markupsafe.Markup:
        fragments: list[str] = []
        escape = markupsafe.Markup.escape

        try:
            icon = self._get_icon("datauri_svg", size=20)
        except Exception:
            icon = None

        fragments.append("<h1>")
        if icon:
            fragments.append(
                f'<img src="{icon}" alt="" width="20" height="20"> '
            )
        if type(self) is ModelElement:
            fragments.append("Model element")
        else:
            fragments.append(escape(self.name or type(self).__name__))
        fragments.append(' <span style="font-size: 70%;">(')
        fragments.append(escape(self.xtype))
        fragments.append(")</span></h1>")

        fragments.append("<table>")
        for attr in dir(self):
            if attr.startswith("_"):
                continue

            acc = getattr(type(self), attr, None)
            if isinstance(acc, _descriptors.Backref):
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
        try:
            icon = self._get_icon("datauri_svg", size=15) or ""
        except Exception:
            icon = ""
        else:
            assert isinstance(icon, str)
        value = getattr(self, "value", "")
        if hasattr(value, "_short_html_"):
            value = value._short_html_()
        return helpers.make_short_html(
            type(self).__name__,
            self.uuid,
            self.name,
            value,
            icon=icon,
            iconsize=15,
        )

    def _repr_html_(self) -> str:
        return self.__html__()

    def _get_styleclass(self) -> str:
        """Return the styleclass of this object.

        :meta public:

        The styleclass determines which set of styles gets applied when
        drawing this object in a diagram.
        """
        return _styleclass.get_styleclass(self)

    def _get_icon(self, format: str, /, *, size: int = 16) -> t.Any | None:
        """Render a small icon for this object.

        :meta public:

        This is the same icon that is also used in diagrams.

        Parameters
        ----------
        format
            The format to use.

            This uses the same format conversion machinery as diagrams, but
            starts with the *svg* format. This means that *svg* and every
            format directly or indirectly derived from it are supported,
            including *png*, *datauri_svg* and others.
        size
            Return the icon scaled to this horizontal and vertical size
            in pixels. This may yield higher quality results compared to
            scaling the returned icon, especially when using raster
            image formats.

        Returns
        -------
        Any | None
            The icon (usually as str or bytes object), or None if no
            icon could be found.
        """
        from capellambse.diagram import get_icon

        sc = self._get_styleclass()
        try:
            return _ICON_CACHE[sc, format, size]
        except KeyError:
            pass

        try:
            data: t.Any = get_icon(sc, size=size)
        except ValueError:
            return None

        if format != "svg":
            data = capellambse.model.diagram.convert_format(
                "svg", format, data
            )
        _ICON_CACHE[sc, format, size] = data
        return data

    if t.TYPE_CHECKING:

        def __getattr__(self, attr: str) -> t.Any:
            """Account for extension attributes in static type checks."""


class ElementList(cabc.MutableSequence[T], t.Generic[T]):
    """Provides access to elements without affecting the underlying model."""

    __slots__ = (
        "_elemclass",
        "_elements",
        "_ElementList__mapkey",
        "_ElementList__mapvalue",
        "_model",
    )

    def is_coupled(self) -> bool:
        return False

    def __init__(
        self,
        model: capellambse.MelodyModel,
        elements: list[etree._Element],
        elemclass: type[T] | None = None,
        *,
        mapkey: str | None = None,
        mapvalue: str | None = None,
    ) -> None:
        assert None not in elements
        self._model = model
        self._elements = elements
        if elemclass is not None:
            self._elemclass = elemclass
        else:
            self._elemclass = ModelElement  # type: ignore[assignment]

        if not mapkey:
            self.__mapkey: str | None = None
            self.__mapvalue: str | None = None
        else:
            self.__mapkey = mapkey
            self.__mapvalue = mapvalue

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, cabc.Sequence):
            return NotImplemented
        return len(self) == len(other) and all(
            ours == theirs for ours, theirs in zip(self, other, strict=True)
        )

    def __add(
        self, other: object, *, reflected: bool = False
    ) -> ElementList[T]:
        if not isinstance(other, ElementList):
            return NotImplemented
        if self._model is not other._model:
            raise ValueError("Cannot add ElementLists from different models")

        if self._elemclass is other._elemclass is not ModelElement:
            listclass: type[ElementList] = ElementList
            elemclass: type[ModelObject] = self._elemclass
        else:
            listclass = MixedElementList
            elemclass = ModelElement

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
                objclass = ModelElement
        else:
            objclass = self._elemclass

        base: cabc.Sequence[t.Any]
        if not reflected:
            base = self
            excluded = {getattr(i, "uuid", None) for i in other}
        else:
            base = other
            excluded = {getattr(i, "uuid", None) for i in self}

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
    def __getitem__(self, idx: int) -> T: ...
    @t.overload
    def __getitem__(self, idx: slice) -> ElementList[T]: ...
    @t.overload
    def __getitem__(self, idx: str) -> t.Any: ...
    def __getitem__(self, idx: int | slice | str) -> t.Any:
        if isinstance(idx, slice):
            return self._newlist(self._elements[idx])
        if isinstance(idx, str):
            obj = self._map_find(idx)
            return self._map_getvalue(obj)
        return self._elemclass.from_model(self._model, self._elements[idx])

    @t.overload
    def __setitem__(self, index: int, value: T) -> None: ...
    @t.overload
    def __setitem__(self, index: slice, value: cabc.Iterable[T]) -> None: ...
    @t.overload
    def __setitem__(self, index: str, value: t.Any) -> None: ...
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

    def __contains__(self, obj: t.Any) -> bool:
        elem = getattr(obj, "_element", None)
        if isinstance(elem, etree._Element):
            return obj._element in self._elements
        return any(i == obj for i in self)

    def __getattr__(self, attr: str) -> _ListFilter:
        if attr.startswith("by_"):
            attr = attr[len("by_") :]
            if attr in {"name", "uuid"}:
                return _ListFilter(self, attr, single=True)
            return _ListFilter(self, attr)

        if attr.startswith("exclude_") and attr.endswith("s"):
            attr = attr[len("exclude_") : -len("s")]
            return _ListFilter(self, attr, positive=False)

        return getattr(super(), attr)

    def __dir__(self) -> list[str]:  # pragma: no cover
        no_dir_attr = re.compile(r"^(_|as_|pvmt$|diagrams?$)")

        def filterable_attrs() -> cabc.Iterator[str]:
            for obj in self:
                try:
                    obj_attrs = dir(obj)
                except Exception:
                    continue
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
                item_repr = item._short_repr_()
            else:
                item_repr = repr(item)
            repr_line = item_repr.splitlines() or [""]
            prefix = f"[{i}] "
            repr_line[0] = prefix + repr_line[0]
            prefix = " " * len(prefix)
            repr_line[1:] = [prefix + i for i in repr_line[1:]]
            items.append("\n".join(repr_line))
        return "\n".join(items)

    def _short_repr_(self) -> str:
        return repr(self)

    def __html__(self) -> markupsafe.Markup:
        if not self:
            return markupsafe.Markup("<p><em>(Empty list)</em></p>")

        fragments = ['<ol start="0" style="text-align: left;">']
        for i in self:
            assert hasattr(i, "_short_html_")
            fragments.append(f"<li>{i._short_html_()}</li>")
        fragments.append("</ol>")
        return markupsafe.Markup("".join(fragments))

    def _short_html_(self) -> markupsafe.Markup:
        return self.__html__()

    def _repr_html_(self) -> str:
        return self.__html__()

    def _mapkey(self, obj: T) -> t.Any:
        if self.__mapkey is None:
            raise TypeError("This list cannot act as a mapping")

        mapkey = operator.attrgetter(self.__mapkey)
        try:
            return mapkey(obj)
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
        if self.__mapkey is None:
            raise TypeError("This list cannot act as a mapping")

        mapkey = operator.attrgetter(self.__mapkey)
        candidates = [i for i in self if mapkey(i) == key]
        if len(candidates) > 1:
            raise ValueError(f"Multiple matches for key {key!r}")
        if not candidates:
            raise KeyError(key)
        return candidates[0]

    def _map_getvalue(self, obj: T) -> t.Any:
        """Get the mapping value from the target object."""
        if not self.__mapvalue:
            return obj
        getvalue = operator.attrgetter(self.__mapvalue)
        return getvalue(obj)

    def _map_setvalue(self, obj: T, value: t.Any) -> None:
        """Set a new mapping value on the target object."""
        if not self.__mapvalue:
            self[self.index(obj)] = value
            return

        key = self.__mapvalue.rsplit(".", maxsplit=1)
        if len(key) == 1:
            target: t.Any = obj
        else:
            target = operator.attrgetter(key[0])(obj)

        setattr(target, key[-1], value)

    def _newlist(self, elements: list[etree._Element]) -> ElementList[T]:
        listtype = self._newlist_type()
        return listtype(
            self._model,
            elements,
            self._elemclass,
            mapkey=self.__mapkey,
            mapvalue=self.__mapvalue,
        )

    def _newlist_type(self) -> type[ElementList[T]]:
        return type(self)

    @t.overload
    def get(self, key: str) -> T | None: ...
    @t.overload
    def get(self, key: str, default: U) -> T | U: ...
    def get(self, key: str, default: t.Any = None) -> t.Any:
        try:
            return self[key]
        except KeyError:
            return default

    def insert(self, index: int, value: T) -> None:
        elm: etree._Element = value._element
        self._elements.insert(index, elm)

    def create(self, typehint: str | None = None, /, **kw: t.Any) -> T:
        del typehint, kw
        raise TypeError("Cannot create elements: List is not coupled")

    def create_singleattr(self, arg: t.Any) -> T:
        del arg
        raise TypeError("Cannot create elements: List is not coupled")

    def delete_all(self, **kw: t.Any) -> None:
        """Delete all matching objects from the model."""
        indices: list[int] = []
        for i, obj in enumerate(self):
            if all(getattr(obj, k) == v for k, v in kw.items()):
                indices.append(i)

        for index in reversed(indices):
            del self[index]

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

    def map(self, attr: str | _MapFunction[T]) -> ElementList:
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
            if "." in attr:
                mapped: ElementList[t.Any] = self
                for a in attr.split("."):
                    mapped = mapped.map(operator.attrgetter(a))
                return mapped

            attr = operator.attrgetter(attr)
        newelems: list[etree._Element] = []
        newuuids: set[str] = set()
        classes: set[type[ModelElement]] = set()
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
                if isinstance(v, ModelElement):
                    if v.uuid in newuuids:
                        continue
                    newuuids.add(v.uuid)
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


class _ListFilter(t.Generic[T]):
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

    def extract_key(self, element: T) -> t.Any:
        extractor = operator.attrgetter(self._attr)
        value = extractor(element)
        if isinstance(value, enum.Enum):
            value = value.name
        return value

    def make_values_container(self, *values: t.Any) -> cabc.Iterable[t.Any]:
        return values

    def ismatch(self, element: T, valueset: cabc.Iterable[t.Any]) -> bool:
        try:
            value = self.extract_key(element)
        except AttributeError:
            return False

        if isinstance(value, str) or not isinstance(value, cabc.Iterable):
            return self._positive == (value in valueset)
        return self._positive == any(v in value for v in valueset)

    @t.overload
    def __call__(self, *values: t.Any, single: t.Literal[True]) -> T: ...
    @t.overload
    def __call__(
        self, *values: t.Any, single: t.Literal[False]
    ) -> ElementList[T]: ...
    @t.overload
    def __call__(
        self, *values: t.Any, single: bool | None = None
    ) -> T | ElementList[T]: ...
    def __call__(
        self, *values: t.Any, single: bool | None = None
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

    def __iter__(self) -> cabc.Iterator[t.Any]:
        """Yield values that result in a non-empty list when filtered for.

        The returned iterator yields all values that, when given to
        :meth:`__call__`, will result in a non-empty list being
        returned. Consequently, if the original list was empty, this
        iterator will yield no values.

        The order in which the values are yielded is undefined.
        """
        yielded: set[t.Any] = set()

        for elm in self._parent:
            key = self.extract_key(elm)
            if key not in yielded:
                yield key
                yielded.add(key)

    def __contains__(self, value: t.Any) -> bool:
        valueset = self.make_values_container(value)
        return any(self.ismatch(elm, valueset) for elm in self._parent)

    def __getattr__(self, attr: str) -> te.Self:
        if attr.startswith("_"):
            raise AttributeError(f"Invalid filter attribute name: {attr}")
        return type(self)(
            self._parent,
            f"{self._attr}.{attr}",
            positive=self._positive,
            single=self._single,
        )


class _LowercaseListFilter(_ListFilter[T], t.Generic[T]):
    def extract_key(self, element: T) -> t.Any:
        value = super().extract_key(element)
        assert isinstance(value, str)
        return value.lower()

    def make_values_container(self, *values: t.Any) -> cabc.Iterable[t.Any]:
        return tuple(map(operator.methodcaller("lower"), values))


class CachedElementList(ElementList[T], t.Generic[T]):
    """An ElementList that caches the constructed proxies by UUID."""

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
            The :class:`ModelElement` subclass to use for reconstructing
            elements.
        cacheattr
            The attribute on the ``model`` to use as cache.
        **kw
            Additional arguments are passed to the superclass.
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

    def _newlist(self, elements: list[etree._Element]) -> ElementList[T]:
        newlist = super()._newlist(elements)
        assert isinstance(newlist, CachedElementList)
        newlist.cacheattr = self.cacheattr
        return newlist


class MixedElementList(ElementList[ModelElement]):
    """ElementList that handles proxies using ``XTYPE_HANDLERS``."""

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
        **kw
            Additional arguments are passed to the superclass.
        """
        del elemclass
        super().__init__(model, elements, ModelElement, **kw)

    def __getattr__(self, attr: str) -> _ListFilter[ModelElement]:
        if attr == "by_type":
            return _LowercaseListFilter(self, "__class__.__name__")
        return super().__getattr__(attr)

    def __dir__(self) -> list[str]:  # pragma: no cover
        return [*super().__dir__(), "by_type", "exclude_types"]


class ElementListMapKeyView(cabc.Sequence):
    def __init__(self, parent, /) -> None:
        self.__parent = parent

    @t.overload
    def __getitem__(self, idx: int) -> t.Any: ...
    @t.overload
    def __getitem__(self, idx: slice) -> list: ...
    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return [self.__parent._mapkey(i) for i in self.__parent[idx]]
        return self.__parent._mapkey(self.__parent[idx])

    def __len__(self) -> int:
        return len(self.__parent)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({list(self)!r})"


class ElementListMapItemsView(cabc.Sequence[tuple[t.Any, T]], t.Generic[T]):
    def __init__(self, parent, /) -> None:
        self.__parent = parent

    @t.overload
    def __getitem__(self, idx: int) -> tuple[t.Any, T]: ...
    @t.overload
    def __getitem__(self, idx: slice) -> list[tuple[t.Any, T]]: ...
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


class ElementListCouplingMixin(ElementList[T], t.Generic[T]):
    """Couples an ElementList with an Accessor to enable write support.

    This class is meant to be subclassed further, where the subclass has
    both this class and the originally intended one as base classes (but
    no other ones, i.e. there must be exactly two bases). The Accessor
    then inserts itself as the ``_accessor`` class variable on the new
    subclass. This allows the mixed-in methods to delegate actual model
    modifications to the Accessor.
    """

    _accessor: _descriptors.WritableAccessor[T]

    def is_coupled(self) -> bool:
        return True

    def __init__(
        self,
        *args: t.Any,
        parent: ModelObject,
        fixed_length: int = 0,
        **kw: t.Any,
    ) -> None:
        assert type(self)._accessor

        super().__init__(*args, **kw)
        self._parent = parent
        self.fixed_length = fixed_length

    @t.overload
    def __setitem__(self, index: int, value: T) -> None: ...
    @t.overload
    def __setitem__(self, index: slice, value: cabc.Iterable[T]) -> None: ...
    @t.overload
    def __setitem__(self, index: str, value: t.Any) -> None: ...
    def __setitem__(self, index: int | slice | str, value: t.Any) -> None:
        assert self._parent is not None
        accessor = type(self)._accessor
        assert isinstance(accessor, _descriptors.WritableAccessor)

        if not isinstance(index, int | slice):
            super().__setitem__(index, value)
            return

        new_objs = list(self)
        new_objs[index] = value

        if self.fixed_length and len(new_objs) != self.fixed_length:
            raise TypeError(
                f"Cannot set: List must stay at length {self.fixed_length}"
            )

        accessor.__set__(self._parent, new_objs)

    def __delitem__(self, index: int | slice) -> None:
        if self.fixed_length and len(self) <= self.fixed_length:
            raise TypeError("Cannot delete from a fixed-length list")

        assert self._parent is not None
        accessor = type(self)._accessor
        assert isinstance(accessor, _descriptors.WritableAccessor)
        if not isinstance(index, slice):
            index = slice(index, index + 1 or None)
        for obj in self[index]:
            accessor.delete(self, obj)
        super().__delitem__(index)

    def _newlist_type(self) -> type[ElementList[T]]:
        assert len(type(self).__bases__) == 2
        assert type(self).__bases__[0] is ElementListCouplingMixin
        return type(self).__bases__[1]

    def create(self, typehint: str | None = None, /, **kw: t.Any) -> T:
        """Make a new model object (instance of ModelElement).

        Instead of specifying the full ``xsi:type`` including the
        namespace, you can also pass in just the part after the ``:``
        separator. If this is unambiguous, the appropriate
        layer-specific type will be selected automatically.

        This method can be called with or without the ``layertype``
        argument. If a layertype is not given, all layers will be tried
        to find an appropriate ``xsi:type`` handler. Note that setting
        the layertype to ``None`` explicitly is different from not
        specifying it at all; ``None`` tries only the "Transverse
        modelling" type elements.

        Parameters
        ----------
        typehint
            Hints for finding the correct type of element to create. Can
            either be a full or shortened ``xsi:type`` string, or an
            abbreviation defined by the specific Accessor instance.
        kw
            Initialize the properties of the new object. Depending on
            the object, some attributes may be required.
        """
        if self.fixed_length and len(self) >= self.fixed_length:
            raise TypeError("Cannot create elements in a fixed-length list")

        assert self._parent is not None
        acc = type(self)._accessor
        assert isinstance(acc, _descriptors.WritableAccessor)
        newobj = acc.create(self, typehint, **kw)
        try:
            acc.insert(self, len(self), newobj)
            super().insert(len(self), newobj)
        except:
            self._parent._element.remove(newobj._element)
            raise
        return newobj

    def create_singleattr(self, arg: t.Any) -> T:
        """Make a new model object (instance of ModelElement).

        This new object has only one interesting attribute.

        See Also
        --------
        :meth:`ElementListCouplingMixin.create` :
            More details on how elements are created.
        :meth:`WritableAccessor.create_singleattr` :
            The method to override in Accessors in order to implement
            this operation.
        """
        if self.fixed_length and len(self) >= self.fixed_length:
            raise TypeError("Cannot create elements in a fixed-length list")

        assert self._parent is not None
        acc = type(self)._accessor
        assert isinstance(acc, _descriptors.WritableAccessor)
        newobj = acc.create_singleattr(self, arg)
        try:
            acc.insert(self, len(self), newobj)
            super().insert(len(self), newobj)
        except:
            self._parent._element.remove(newobj._element)
            raise
        return newobj

    def insert(self, index: int, value: T) -> None:
        if self.fixed_length and len(self) >= self.fixed_length:
            raise TypeError("Cannot insert into a fixed-length list")

        assert self._parent is not None
        acc = type(self)._accessor
        assert isinstance(acc, _descriptors.WritableAccessor)
        acc.insert(self, index, value)
        super().insert(index, value)
