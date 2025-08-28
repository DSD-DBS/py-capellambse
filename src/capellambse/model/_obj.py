# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

__all__ = [
    "CORE_VIEWPOINT",
    "CachedElementList",
    "ClassName",
    "ElementList",
    "ElementListCouplingMixin",
    "ElementListMapItemsView",
    "ElementListMapKeyView",
    "MissingClassError",
    "MixedElementList",
    "ModelElement",
    "ModelObject",
    "Namespace",
    "UnresolvedClassName",
    "enumerate_namespaces",
    "find_namespace",
    "find_namespace_by_uri",
    "find_wrapper",
    "resolve_class_name",
    "wrap_xml",
]

import abc
import collections
import collections.abc as cabc
import contextlib
import dataclasses
import functools
import importlib
import importlib.metadata as imm
import inspect
import logging
import operator
import re
import sys
import textwrap
import typing as t
import warnings

import awesomeversion as av
import markupsafe
import typing_extensions as te
from lxml import etree

import capellambse
from capellambse import helpers

from . import VIRTUAL_NAMESPACE_PREFIX, T, U, _descriptors, _pods, _styleclass

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

if t.TYPE_CHECKING:
    import capellambse.metamodel as mm

LOGGER = logging.getLogger(__name__)
CORE_VIEWPOINT = "org.polarsys.capella.core.viewpoint"


_NOT_SPECIFIED = object()
"Used to detect unspecified optional arguments"

_MapFunction: te.TypeAlias = (
    "cabc.Callable[[T], ModelElement | cabc.Iterable[ModelElement]]"
)

_TERMCELL: tuple[int, int] | None = None
_ICON_CACHE: dict[tuple[str, str, int], t.Any] = {}


UnresolvedClassName: t.TypeAlias = (
    "tuple[str | capellambse.model.Namespace, str]"
)
"""A tuple of namespace URI and class name."""

ClassName: t.TypeAlias = "tuple[capellambse.model.Namespace, str]"
"""A tuple of Namespace object and class name."""


class UnknownNamespaceError(KeyError):
    """Raised when a requested namespace cannot be found."""

    def __init__(self, name: str, /) -> None:
        super().__init__(name)

    @property
    def name(self) -> str:
        """The name or URI that was searched for."""
        return self.args[0]

    def __str__(self) -> str:
        return f"Namespace not found: {self.name}"


class MissingClassError(KeyError):
    """Raised when a requested class is not found."""

    def __init__(
        self,
        ns: Namespace | None,
        nsver: av.AwesomeVersion | str | None,
        clsname: str,
    ) -> None:
        if isinstance(nsver, str):
            nsver = av.AwesomeVersion(nsver)
        super().__init__(ns, nsver, clsname)

    @property
    def ns(self) -> Namespace | None:
        """The namespace that was searched, or None for all namespaces."""
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
        if self.ns and self.ns_version:
            return (
                f"No class {self.clsname!r} in v{self.ns_version} of"
                f" namespace {self.ns.uri!r}"
            )
        if self.ns:
            return f"No class {self.clsname!r} in namespace {self.ns.uri!r}"
        return f"No class {self.clsname!r} found in any known namespace"


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
    version_precision: int
    """Number of significant parts in the version number for namespaces.

    When qualifying a versioned namespace based on the model's activated
    viewpoint, only use this many components for the namespace URL.
    Components after that are set to zero.

    Example: A viewpoint version of "1.2.3" with a version precision of
    2 will result in the namespace version "1.2.0".
    """

    def __init__(
        self,
        uri: str,
        alias: str,
        viewpoint: str | None = None,
        maxver: str | None = None,
        *,
        version_precision: int = 1,
    ) -> None:
        if version_precision <= 0:
            raise ValueError("Version precision cannot be negative")

        object.__setattr__(self, "uri", uri)
        object.__setattr__(self, "alias", alias)
        object.__setattr__(self, "viewpoint", viewpoint)
        object.__setattr__(self, "version_precision", version_precision)

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
            type[ModelObject],
            av.AwesomeVersion,
            av.AwesomeVersion | None,
        ]"""
        self._classes: dict[str, list[clstuple]]
        object.__setattr__(self, "_classes", collections.defaultdict(list))

    def match_uri(self, uri: str) -> bool | av.AwesomeVersion | None:
        """Match a (potentially versioned) URI against this namespace.

        The return type depends on whether this namespace is versioned.

        Unversioned Namespaces return a simple boolean flag indicating
        whether the URI exactly matches this Namespace.

        Versioned Namespaces return one of:

        - ``False``, if the URI did not match
        - ``None``, if the URI did match, but the version field was
          empty or the literal ``{VERSION}`` placeholder
        - Otherwise, an :class:~`awesomeversion.AwesomeVersion` object
          with the version number contained in the URL

        Values other than True and False can then be passed on to
        :meth:`get_class`, to obtain a class object appropriate for the
        namespace and version described by the URI.
        """
        if "{VERSION}" not in self.uri:
            return uri == self.uri

        prefix, _, suffix = self.uri.partition("{VERSION}")
        if (
            len(uri) >= len(prefix) + len(suffix)
            and uri.startswith(prefix)
            and uri.endswith(suffix)
        ):
            v = uri[len(prefix) : -len(suffix) or None]
            if "/" in v:
                return False
            if v in ("", "{VERSION}"):
                return None
            return self.trim_version(v)

        return False

    def get_class(
        self, clsname: str, version: str | None = None
    ) -> type[ModelObject]:
        if "{VERSION}" in self.uri and not version:
            raise TypeError(
                f"Versioned namespace, but no version requested: {self.uri}"
            )

        classes = self._classes.get(clsname)
        if not classes:
            raise MissingClassError(self, version, clsname)

        eligible: list[tuple[av.AwesomeVersion, type[ModelObject]]] = []
        for cls, minver, maxver in classes:
            if version and (version < minver or (maxver and version > maxver)):
                continue
            eligible.append((minver, cls))

        if not eligible:
            raise MissingClassError(self, version, clsname)
        eligible.sort(key=lambda i: i[0], reverse=True)
        return eligible[0][1]

    def register(
        self,
        cls: type[ModelObject],
        minver: str | None,
        maxver: str | None,
    ) -> None:
        if cls.__capella_namespace__ is not self:
            raise ValueError(
                f"Cannot register class {cls.__name__!r}"
                f" in Namespace {self.uri!r},"
                f" because it belongs to {cls.__capella_namespace__.uri!r}"
            )

        classes = self._classes[cls.__name__]
        if minver is not None:
            minver = av.AwesomeVersion(minver)
        else:
            minver = av.AwesomeVersion(0)
        if maxver is not None:
            maxver = av.AwesomeVersion(maxver)
        classes.append((cls, minver, maxver))

    def trim_version(
        self, version: str | av.AwesomeVersion, /
    ) -> av.AwesomeVersion:
        assert self.version_precision > 0
        pos = dots = 0
        while pos < len(version) and dots < self.version_precision:
            try:
                pos = version.index(".", pos) + 1
            except ValueError:
                return av.AwesomeVersion(version)
            else:
                dots += 1
        trimmed = version[:pos] + re.sub(r"[^.]+", "0", version[pos:])
        return av.AwesomeVersion(trimmed)

    def __contains__(self, clsname: str) -> bool:
        """Return whether this Namespace has a class with the given name."""
        return clsname in self._classes


NS = Namespace(
    "http://www.polarsys.org/capella/common/core/{VERSION}",
    "org.polarsys.capella.common.data.core",
    CORE_VIEWPOINT,
    "7.0.0",
)
NS_METADATA = Namespace(
    "http://www.polarsys.org/kitalpha/ad/metadata/1.0.0",
    "metadata",
    CORE_VIEWPOINT,
)


@t.runtime_checkable
class ModelObject(t.Protocol):
    """A class that wraps a specific model object.

    Most of the time, you'll want to subclass the concrete
    ``ModelElement`` class. However, some special classes (e.g. AIRD
    diagrams) provide a compatible interface, but it doesn't make sense
    to wrap a specific XML element. This protocol class is used in type
    annotations to catch both "normal" ModelElement subclasses and the
    mentioned special cases.
    """

    __capella_namespace__: t.ClassVar[Namespace]
    __capella_abstract__: t.ClassVar[bool]

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


class _ModelElementMeta(abc.ABCMeta):
    def __setattr__(cls, attr, value):
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
        if "__capella_namespace__" in namespace:
            raise TypeError(
                f"Cannot create class {name!r}:"
                " Invalid declaration of __capella_namespace__ in class body"
            )

        if (
            "_xmltag" in namespace
            and namespace["_xmltag"] is not None
            and not namespace["__module__"].startswith("capellambse.")
        ):
            warnings.warn(
                (
                    "The '_xmltag' declaration in the class body is deprecated,"
                    " define a Containment on the containing class instead"
                ),
                DeprecationWarning,
                stacklevel=2,
            )

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
                return super(cls, self).__eq__(other)  # type: ignore[misc]

            namespace["__eq__"] = __eq__

        if ns is None:
            modname: str = namespace["__module__"]
            cls_mod = importlib.import_module(modname)
            auto_ns = getattr(cls_mod, "NS", None)
            if not isinstance(auto_ns, Namespace):
                raise TypeError(
                    f"Cannot create class {name!r}: No namespace\n"
                    "\n"
                    f"No Namespace found at {modname}.NS,\n"
                    "and no `ns` passed explicitly while subclassing.\n"
                    "\n"
                    "Declare a module-wide namespace with:\n"
                    "\n"
                    "    from capellambse import ModelElement, Namespace\n"
                    "    NS = Namespace(...)\n"
                    f"    class {name}(ModelElement): ...\n"
                    "\n"
                    "Or specify it explicitly for each class:\n"
                    "\n"
                    "    from capellambse import ModelElement, Namespace\n"
                    "    MY_NS = Namespace(...)\n"
                    f"    class {name}(ModelElement, ns=MY_NS): ...\n"
                )
            ns = auto_ns

        assert isinstance(ns, Namespace)
        namespace["__capella_namespace__"] = ns
        namespace["__capella_abstract__"] = bool(abstract)
        cls = t.cast(
            "type[ModelElement]",
            super().__new__(mcs, name, bases, namespace),
        )
        ns.register(cls, minver=minver, maxver=maxver)
        return cls

    def __subclasscheck__(self, subclass) -> bool:
        import capellambse.metamodel as mm  # noqa: PLC0415

        try:
            replacements = {
                (
                    mm.cs.ComponentArchitecture,
                    mm.oa.OperationalAnalysis,
                ): mm.cs.BlockArchitecture,
            }
        except AttributeError:
            # The metamodel isn't fully initialized yet
            return super().__subclasscheck__(subclass)

        for (sup, sub), replacement in replacements.items():
            if self is not sup or not issubclass(subclass, sub):
                continue
            warnings.warn(
                (
                    f"{subclass.__name__}"
                    " will soon no longer be considered a subclass of"
                    f" {sup.__name__}, use {replacement.__name__}"
                    " for issubclass/isinstance checks instead"
                ),
                UserWarning,
                stacklevel=2,
            )
            return True
        return super().__subclasscheck__(subclass)


class ModelElement(metaclass=_ModelElementMeta):
    """A model element.

    This is the common base class for all elements of a model. In terms
    of the metamodel, it combines the role of
    ``modellingcore.ModelElement`` and all its superclasses; references
    to any superclass should be modified to use this class instead.

    This class is also re-exported at
    ``capellambse.metamodel.modellingcore.ModelElement``.
    """

    __capella_namespace__: t.ClassVar[Namespace]
    __capella_abstract__: t.ClassVar[bool]

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

    diagrams: _descriptors.Accessor[
        ElementList[capellambse.model.diagram.Diagram]
    ]
    diagrams = property(  # type: ignore[assignment]
        lambda self: self._model.diagrams.by_target(self)
    )
    visible_on_diagrams = property(
        lambda self: self._model.diagrams.by_semantic_nodes(self)
    )

    parent = _descriptors.ParentAccessor()
    extensions: _descriptors.Containment[ModelElement]
    constraints: _descriptors.Containment[mm.capellacore.Constraint]

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

        return wrap_xml(self._model, self._model._loader[uuid]).name

    @classmethod
    @deprecated("ModelElement.from_model is deprecated, use wrap_xml instead")
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
        return wrap_xml(model, element, cls)

    @property
    def layer(self) -> capellambse.metamodel.cs.BlockArchitecture:
        """Find the layer that this element belongs to.

        Note that an architectural layer normally does not itself have a
        parent layer.

        Raises
        ------
        AttributeError
            Raised if this element is not nested below a layer.
        """
        import capellambse.metamodel as mm  # noqa: PLC0415

        obj: ModelElement | None = self
        assert obj is not None
        while obj := getattr(obj, "parent", None):
            if isinstance(obj, mm.cs.BlockArchitecture):
                return obj
        raise AttributeError(
            f"No parent layer found for {self._short_repr_()}"
        )

    @property
    @deprecated(
        "str-based xsi:type handling is deprecated,"
        " use 'helpers.qtype_of(elem)' and 'etree.QName' instead"
    )
    def xtype(self) -> str | None:
        return helpers.xtype_of(self._element)

    def __init__(
        self,
        model: capellambse.MelodyModel,
        parent: etree._Element,
        xmltag: str | None = None,
        /,
        *,
        uuid: str,
        xtype: str | None = None,
        **kw: t.Any,
    ) -> None:
        if type(self).__capella_abstract__:
            raise TypeError(
                f"{type(self).__name__} is an abstract class"
                " and cannot be instantiated directly"
            )

        all_required_attrs: set[str] = set()
        for basecls in type(self).mro():
            all_required_attrs |= getattr(
                basecls, "_required_attrs", frozenset()
            )
        missing_attrs = all_required_attrs - frozenset(kw) - {"uuid", "xtype"}
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

        fragment_name = model._loader.find_fragment(parent)
        fragment = model._loader.trees[fragment_name]

        self._model = model
        self._element: etree._Element = etree.Element(xmltag)
        parent.append(self._element)
        try:
            self.uuid = uuid
            if xtype is not None:
                warnings.warn(
                    "Passing 'xtype' during ModelElement construction is deprecated and no longer needed",
                    DeprecationWarning,
                    stacklevel=2,
                )
            ns = self.__capella_namespace__
            qtype = model.qualify_classname((ns, type(self).__name__))
            assert qtype.namespace is not None
            fragment.add_namespace(qtype.namespace, ns.alias)
            self._element.set(helpers.ATT_XT, qtype)
            for key, val in kw.items():
                if not isinstance(
                    getattr(type(self), key),
                    _descriptors.Accessor | _pods.BasePOD,
                ):
                    raise TypeError(
                        f"Cannot set {key!r} on {type(self).__name__}"
                    )
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
        for attr, acc in self.__iter_properties():
            if isinstance(acc, _descriptors.Backref):
                attrs.append(
                    f".{attr} = ... # backreference to {acc.class_[1]}"
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

        namegetter = getattr(type(self), "name", None)
        # TODO remove check against '.name' when removing deprecated features
        if namegetter is not None and namegetter is not ModelElement.name:  # type: ignore[attr-defined]
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
            name = type(self).__name__
            namegetter = getattr(type(self), "name", None)
            # TODO remove check against '.name' when removing deprecated features
            if namegetter is not None and namegetter is not ModelElement.name:  # type: ignore[attr-defined]
                name = self.name or name
            fragments.append(escape(name))
        fragments.append(' <span style="font-size: 70%;">(')
        fragments.append(escape(self.__capella_namespace__.alias))
        fragments.append(":")
        fragments.append(escape(type(self).__name__))
        fragments.append(")</span></h1>\n")

        fragments.append("<table>\n")
        for attr, acc in self.__iter_properties():
            if isinstance(acc, _descriptors.Backref):
                fragments.append('<tr><th style="text-align: right;">')
                fragments.append(escape(attr))
                fragments.append('</th><td style="text-align: left;"><em>')
                fragments.append(f"Backreference to {acc.class_[1]}")
                fragments.append(" - omitted: can be slow to compute.")
                fragments.append(" Display this property directly to show.")
                fragments.append("</em></td></tr>\n")
                continue

            if attr.startswith("all_"):
                fragments.append('<tr><th style="text-align: right;">')
                fragments.append(escape(attr))
                fragments.append('</th><td style="text-align: left;"><em>')
                fragments.append("omitted")
                fragments.append("</em></td></tr>\n")
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
            fragments.append("</td></tr>\n")
        fragments.append("</table>")
        return markupsafe.Markup("".join(fragments))

    def _short_html_(self) -> markupsafe.Markup:
        try:
            icon = self._get_icon("datauri_svg", size=15) or ""
        except Exception:
            icon = ""
        else:
            assert isinstance(icon, str)
        valuegetter = getattr(type(self), "value", None)
        if (
            valuegetter is None
            or isinstance(valuegetter, _descriptors.DeprecatedAccessor)
            or (
                isinstance(valuegetter, property)
                and hasattr(valuegetter.fget, "__deprecated__")
            )
        ):
            value = ""
        else:
            value = getattr(self, "value", "")
        if hasattr(value, "_short_html_"):
            value = value._short_html_()
        name = ""
        if getattr(type(self), "name", None) is not ModelElement.name:  # type: ignore[attr-defined]
            name = self.name
        return helpers.make_short_html(
            type(self).__name__,
            self.uuid,
            name,
            value,
            icon=icon,
            iconsize=15,
        )

    def _repr_html_(self) -> str:
        return self.__html__()

    def _get_styleclass(self) -> str:
        """Return the styleclass of this object.

        The styleclass determines which set of styles gets applied when
        drawing this object in a diagram.

        :meta public:
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
        from capellambse.diagram import get_icon  # noqa: PLC0415

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

    def __iter_properties(
        self,
    ) -> cabc.Iterator[
        tuple[str, _descriptors.Accessor | _pods.BasePOD | property]
    ]:
        cls = type(self)
        for attr in dir(self):
            if attr.startswith("_"):
                continue
            acc = getattr(cls, attr, None)
            if acc is None:
                continue
            if isinstance(acc, _descriptors.DeprecatedAccessor):
                continue
            if isinstance(acc, property) and (
                getattr(acc.fget, "__deprecated__", None) is not None
                or acc.fget is ModelElement.name.fget  # type: ignore[attr-defined]
                or acc.fget is ModelElement.description.fget  # type: ignore[attr-defined]
                or acc.fget is ModelElement.summary.fget  # type: ignore[attr-defined]
            ):
                continue

            if isinstance(acc, _descriptors.Single):
                acc = acc.wrapped

            yield (attr, acc)

    if t.TYPE_CHECKING:

        def __getattr__(self, attr: str) -> t.Any:
            """Account for extension attributes in static type checks."""

    else:

        @property
        def name(self) -> str:
            warnings.warn(
                (
                    f"{type(self).__name__} cannot have a '.name',"
                    " please update your code to check if the field exists or"
                    " if the object subclasses modellingcore.AbstractNamedElement"
                ),
                category=FutureWarning,
                stacklevel=2,
            )
            return ""

        @name.setter
        def name(self, _: str) -> None:
            raise TypeError(
                f"{type(self).__name__} cannot have a '.name',"
                " please update your code to check if the field exists or"
                " if the object subclasses modellingcore.AbstractNamedElement"
            )

        @property
        def description(self) -> markupsafe.Markup:
            warnings.warn(
                (
                    f"{type(self).__name__} cannot have a '.description',"
                    " please update your code to check if the field exists or"
                    " if the object subclasses capellacore.CapellaElement"
                ),
                category=FutureWarning,
                stacklevel=2,
            )
            return markupsafe.Markup("")

        @description.setter
        def description(self, _: str) -> None:
            raise TypeError(
                f"{type(self).__name__} cannot have a '.description',"
                " please update your code to check if the field exists or"
                " if the object subclasses capellacore.CapellaElement"
            )

        @property
        def summary(self) -> str:
            warnings.warn(
                (
                    f"{type(self).__name__} cannot have a '.summary',"
                    " please update your code to check if the field exists or"
                    " if the object subclasses capellacore.CapellaElement"
                ),
                category=FutureWarning,
                stacklevel=2,
            )
            return ""

        @summary.setter
        def summary(self, _: str) -> None:
            raise TypeError(
                f"{type(self).__name__} cannot have a '.summary',"
                " please update your code to check if the field exists or"
                " if the object subclasses capellacore.CapellaElement"
            )


class ElementList(cabc.MutableSequence[T], t.Generic[T]):
    """Provides access to elements without affecting the underlying model."""

    __slots__ = (
        "_ElementList__legacy_by_type",
        "_ElementList__mapkey",
        "_ElementList__mapvalue",
        "_elemclass",
        "_elements",
        "_model",
    )

    __hash__ = None  # type: ignore[assignment]

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
        legacy_by_type: bool = False,
    ) -> None:
        assert None not in elements
        self._model = model
        self._elements = elements

        if (
            __debug__
            and elemclass is not None
            and elemclass is not ModelElement
        ):
            for i, e in enumerate(self._elements):
                ecls = model.resolve_class(e)
                if not issubclass(elemclass, ecls):
                    raise TypeError(
                        f"BUG: Configured elemclass {elemclass.__name__!r}"
                        f" is not a subclass of {ecls.__name__!r}"
                        f" (found at index {i})"
                    )

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
        self.__legacy_by_type = legacy_by_type

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
            elemclass: type[T] | None = self._elemclass
        else:
            elemclass = None

        if not reflected:
            elements = self._elements + other._elements
        else:
            elements = other._elements + self._elements

        return ElementList(self._model, elements, elemclass)

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

        if self._elemclass is not ModelElement:
            obj = self._elemclass.__new__(self._elemclass)
            obj._model = self._model  # type: ignore[misc]
            obj._element = self._elements[idx]  # type: ignore[misc]
            return obj
        return wrap_xml(self._model, self._elements[idx], self._elemclass)

    @t.overload
    def __setitem__(self, index: int, value: t.Any) -> None: ...
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

    def __getattr__(self, attr: str) -> _ListFilter[T]:
        if self.__legacy_by_type and attr in {"by_type", "exclude_types"}:
            if isinstance(self, ElementListCouplingMixin):
                acc = type(self)._accessor
                text = f"{attr!r} on {acc._qualname}"
            else:
                text = f"This {attr!r}"
            attr = attr.replace("type", "class")
            text = (
                f"{text} will soon change to filter"
                " on the 'type' attribute of the contained elements,"
                f" change calls to use {attr!r} instead"
            )
            warnings.warn(text, UserWarning, stacklevel=2)

        if attr.startswith("by_"):
            attr = attr[len("by_") :]
            if attr in {"name", "uuid"}:
                return _ListFilter(self, attr, single=True)
            if attr == "class":
                attr = "__class__"
            return _ListFilter(self, attr)

        if attr.startswith("exclude_") and attr.endswith("s"):
            attr = attr[len("exclude_") : -len("s")]
            if attr == "classe":
                attr = "__class__"
            return _ListFilter(self, attr, positive=False)

        return getattr(super(), attr)

    def __dir__(self) -> cabc.Iterable[str]:  # pragma: no cover
        no_dir_attr = re.compile(r"^(_|as_|pvmt$|diagrams?$)")

        def filterable_attrs() -> cabc.Iterator[str]:
            for obj in self:
                try:
                    obj_attrs = dir(obj)
                except Exception:
                    continue
                for attr in obj_attrs:
                    if no_dir_attr.search(attr):
                        continue
                    yield f"by_{attr}"
                    yield f"exclude_{attr}s"

        attrs = set(super().__dir__())
        attrs.update(filterable_attrs())
        if self.__legacy_by_type:
            attrs.update(("by_type", "exclude_types"))
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

        fragments = ['<ol start="0" style="text-align: left;">\n']
        for i in self:
            assert hasattr(i, "_short_html_")
            fragments.append(f"<li>{i._short_html_()}</li>\n")
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

    def insert(self, index: int, value: t.Any) -> None:
        if not isinstance(value, ModelObject):
            raise TypeError("Cannot create elements: List is not coupled")
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
        return ElementList(self._model, newelems, legacy_by_type=True)

    if t.TYPE_CHECKING:

        def append(self, value: t.Any) -> None: ...
        def extend(self, values: cabc.Iterable[t.Any]) -> None: ...

        by_name: _ListFilterSingle[T, str]
        by_uuid: _ListFilterSingle[T, str]
        by_class: _ListFilterClass


if t.TYPE_CHECKING:

    class _ListFilterSingle(t.Generic[T, U]):
        """Same as _ListFilter, but typed with 'single' defaulting to True."""

        def __init__(self, arg: te.Never) -> te.Never: ...

        @t.overload
        def __call__(
            self, *v: str, single: t.Literal[False]
        ) -> ElementList[T]: ...
        @t.overload
        def __call__(
            self, *v: str, single: t.Literal[True] | None = ...
        ) -> T: ...
        @t.overload
        def __call__(self, *v: t.Any, single: bool) -> T | ElementList[T]: ...
        def __call__(self, *args, **kw): ...

        def __iter__(self) -> cabc.Iterator[U]: ...
        def __contains__(self, value: t.Any, /) -> bool: ...
        # no __getattr__, as this is only used for 'name' and 'uuid',
        # neither of which supports chaining further attributes
        def __getattr__(self, attr: str) -> te.Never: ...

    _T = t.TypeVar("_T", bound=ModelObject)

    class _ListFilterClass(t.Generic[T]):
        """Same as _ListFilter, but specifically typed for 'by_class'."""

        def __init__(self, arg: te.Never) -> te.Never: ...

        @t.overload
        def __call__(self, *v: type[_T], single: t.Literal[True]) -> _T: ...
        @t.overload
        def __call__(
            self, *v: type[_T], single: t.Literal[False] | None = ...
        ) -> ElementList[_T]: ...
        @t.overload
        def __call__(
            self, *v: type[_T], single: bool
        ) -> _T | ElementList[_T]: ...
        @t.overload
        def __call__(
            self, *v: str | UnresolvedClassName, single: t.Literal[True]
        ) -> T: ...
        @t.overload
        def __call__(
            self,
            *v: str | UnresolvedClassName,
            single: t.Literal[False] | None = ...,
        ) -> ElementList[T]: ...
        @t.overload
        def __call__(
            self, *v: str | UnresolvedClassName, single: bool
        ) -> T | ElementList[T]: ...
        def __call__(self, *args, **kw): ...

        def __iter__(self) -> cabc.Iterator[U]: ...
        def __contains__(self, value: t.Any, /) -> bool: ...
        # no __getattr__, as this is only used for 'class',
        # which doesn't support chaining further attributes
        def __getattr__(self, attr: str) -> te.Never: ...


class _ListFilter(t.Generic[T]):
    """Filters this list based on an extractor function."""

    __slots__ = ("_attr", "_lower", "_parent", "_positive", "_single")

    __special_filterable: t.Final = frozenset({"__class__", "_element"})
    """Attributes starting with an underscore that can still be filtered on."""

    def __init__(
        self,
        parent: ElementList[T],
        attr: str,
        *,
        positive: bool = True,
        single: bool = False,
        case_insensitive: bool = False,
    ) -> None:
        """Create a filter object.

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
        case_insensitive
            Use case-insensitive matching.
        """
        self._attr = attr
        self._parent = parent
        self._positive = positive
        self._single = single
        self._lower = case_insensitive

    def __find_candidates(self) -> cabc.Iterator[tuple[etree._Element, t.Any]]:
        attrs = self._attr.split(".")
        assert "class" not in attrs, (
            "'class' should have been replaced with '__class__' already"
        )

        if any(
            not i or (i.startswith("_") and i not in self.__special_filterable)
            for i in attrs
        ):
            raise ValueError(f"Invalid filter attribute: {self._attr}")

        for elem in self._parent._elements:
            o: t.Any = wrap_xml(self._parent._model, elem)
            want = True

            for attr in attrs:
                if (
                    isinstance(o, cabc.Iterable)
                    and not isinstance(o, str)
                    and not isinstance(o, ModelElement)
                ):
                    o = [getattr(c, attr) for c in o if hasattr(c, attr)]
                    if not o:
                        want = False
                        break
                else:
                    try:
                        o = getattr(o, attr)
                    except AttributeError:
                        want = False
                        break

            if want:
                yield (elem, o)

    def __filter_candidates(
        self, values: tuple[t.Any, ...]
    ) -> cabc.Iterator[etree._Element]:
        valueset: tuple[t.Any, ...]
        if self._attr.rsplit(".", 1)[-1] == "__class__":
            valueset = tuple(
                v
                if isinstance(v, type)
                else self._parent._model.resolve_class(v)
                for v in values
            )

            def ismatch(o: t.Any) -> bool:
                return any(issubclass(o, v) for v in valueset)
        else:
            if self._lower:
                valueset = tuple(
                    value.lower() if isinstance(value, str) else value
                    for value in values
                )
            else:
                valueset = values

            def ismatch(o: t.Any) -> bool:
                if isinstance(o, cabc.Iterable) and not isinstance(o, str):
                    return any(i in valueset for i in o)
                return o in valueset

        for elem, candidate in self.__find_candidates():
            if ismatch(candidate) == self._positive:
                yield elem

    @t.overload
    def __call__(self, *values: t.Any, single: t.Literal[True]) -> T: ...
    @t.overload
    def __call__(
        self, *values: t.Any, single: t.Literal[False] | None = ...
    ) -> ElementList[T]: ...
    @t.overload
    def __call__(self, *values: t.Any, single: bool) -> T | ElementList[T]: ...
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

        elements = list(self.__filter_candidates(values))

        if not single:
            return self._parent._newlist(elements)
        if len(elements) > 1:
            value = values[0] if len(values) == 1 else values
            raise KeyError(f"Multiple matches for {value!r}")
        if len(elements) == 0:
            raise KeyError(values[0] if len(values) == 1 else values)
        return wrap_xml(self._parent._model, elements[0])

    def __iter__(self) -> cabc.Iterator[t.Any]:
        """Yield values that result in a non-empty list when filtered for.

        The returned iterator yields all values that, when given to
        :meth:`__call__`, will result in a non-empty list being
        returned. Consequently, if the original list was empty, this
        iterator will yield no values.

        The order in which the values are yielded is undefined.
        """
        yielded: set[t.Any] = set()

        for _, key in self.__find_candidates():
            if key not in yielded:
                yield key
                yielded.add(key)

    def __contains__(self, value: t.Any) -> bool:
        try:
            next(self.__filter_candidates((value,)))
        except StopIteration:
            return False
        return True

    def __getattr__(self, attr: str) -> te.Self:
        if "." in attr:
            raise AttributeError(f"Invalid filter attribute name: {attr}")
        if attr.startswith("_") and attr not in self.__special_filterable:
            raise AttributeError(f"Invalid filter attribute name: {attr}")

        if attr == "class":
            attr = "__class__"

        return type(self)(
            self._parent,
            f"{self._attr}.{attr}",
            positive=self._positive,
            single=self._single,
        )


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


@deprecated("MixedElementList is deprecated, use base ElementList instead")
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
        kw["legacy_by_type"] = True
        super().__init__(model, elements, None, **kw)


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

    _accessor: _descriptors.Accessor[ElementList[T]]

    def is_coupled(self) -> bool:
        return True

    def __init__(
        self,
        *args: t.Any,
        parent: ModelObject,
        fixed_length: int = 0,
        **kw: t.Any,
    ) -> None:
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
        acc = type(self)._accessor
        if not (
            isinstance(acc, _descriptors.WritableAccessor)
            or hasattr(acc, "__set__")
        ):
            raise TypeError(
                f"Parent accessor does not support overwriting: {acc!r}"
            )

        if not isinstance(index, int | slice):
            super().__setitem__(index, value)
            return

        new_objs = list(self)
        new_objs[index] = value

        if self.fixed_length and len(new_objs) != self.fixed_length:
            raise TypeError(
                f"Cannot set: List must stay at length {self.fixed_length}"
            )

        acc.__set__(self._parent, new_objs)

    def __delitem__(self, index: int | slice) -> None:
        if self.fixed_length and len(self) <= self.fixed_length:
            raise TypeError("Cannot delete from a fixed-length list")

        assert self._parent is not None
        acc = type(self)._accessor
        if not (
            isinstance(acc, _descriptors.WritableAccessor)
            or hasattr(acc, "delete")
        ):
            raise TypeError(
                f"Parent accessor does not support deleting items: {acc!r}"
            )
        if not isinstance(index, slice):
            index = slice(index, index + 1 or None)
        for obj in self[index]:
            acc.delete(self, obj)
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
        marker = _descriptors.NewObject(typehint or "", **kw)
        return self._insert(len(self), marker)

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
        acc = type(self)._accessor
        single_attr = getattr(acc, "single_attr", None)
        if not isinstance(single_attr, str):
            raise TypeError("Cannot create object from a single attribute")

        marker = _descriptors.NewObject("", **{single_attr: arg})
        return self._insert(len(self), marker)

    def insert(self, index: int, value: t.Any) -> None:
        self._insert(index, value)

    def _insert(self, index: int, value: t.Any) -> T:
        if self.fixed_length and len(self) >= self.fixed_length:
            raise TypeError("Cannot insert into a fixed-length list")

        assert self._parent is not None
        acc = type(self)._accessor

        if not isinstance(value, ModelElement | _descriptors.NewObject):
            single_attr = getattr(acc, "single_attr", None)
            if not isinstance(single_attr, str):
                raise TypeError("Cannot create object from a single attribute")
            value = _descriptors.NewObject("", **{single_attr: value})

        if isinstance(acc, _descriptors.WritableAccessor):
            if isinstance(value, _descriptors.NewObject):
                value = acc.create(self, value._type_hint, **value._kw)
            acc.insert(self, index, value)

        elif hasattr(acc, "insert"):
            value = acc.insert(self, index, value)

        else:
            raise TypeError(
                f"Parent accessor does not support item insertion: {acc!r}"
            )

        super().insert(index, value)
        return value


@functools.cache
def enumerate_namespaces() -> tuple[Namespace, ...]:
    has_base_metamodel = False
    namespaces: list[Namespace] = []
    for i in imm.entry_points(group="capellambse.namespaces"):
        if i.value.startswith("capellambse.metamodel."):
            has_base_metamodel = True

        nsobj = i.load()
        if not isinstance(nsobj, Namespace):
            raise TypeError(
                "Found non-Namespace object at entrypoint"
                f" {i.name!r} in group {i.group!r}: {nsobj!r}"
            )
        namespaces.append(nsobj)

    if not has_base_metamodel:
        raise RuntimeError(
            "Did not find the base metamodel in enumerate_namespaces()!"
            " Check that capellambse is installed properly."
        )
    assert len(namespaces) > 1
    return tuple(namespaces)


@functools.lru_cache(maxsize=128)
def find_namespace(name: str, /) -> Namespace:
    try:
        return next(i for i in enumerate_namespaces() if i.alias == name)
    except StopIteration:
        raise UnknownNamespaceError(name) from None


@functools.lru_cache(maxsize=128)
def find_namespace_by_uri(
    uri: str, /
) -> tuple[Namespace, av.AwesomeVersion | None]:
    """Find a namespace by its URL.

    If the namespace is versioned, the second element of the returned
    tuple is the version indicated in the URL. For unversioned
    namespaces, the second element is always None.
    """
    for i in enumerate_namespaces():
        result = i.match_uri(uri)
        if result is False:
            continue
        if result is True:
            return (i, None)
        return (i, result)
    raise UnknownNamespaceError(uri)


@functools.lru_cache(maxsize=128)
def resolve_class_name(uclsname: UnresolvedClassName, /) -> ClassName:
    """Resolve an unresolved classname to a resolved ClassName tuple.

    Note that this method does not check whether the requested class
    name actually exists in the resolved namespace. This helps to avoid
    problems with circular dependencies between metamodel modules, where
    the first point of use is initialized before the class gets
    registered in the namespace.

    However, if the namespace part of the UnresolvedClassName input is
    the empty string, the class must already be registered in its
    namespace, as there would be no way to find the correct namespace
    otherwise.
    """
    ns, clsname = uclsname

    if isinstance(ns, Namespace):
        return (ns, clsname)

    if isinstance(ns, str) and ns:
        try:
            ns_obj = next(
                i
                for i in enumerate_namespaces()
                if i.alias == ns or i.match_uri(ns)
            )
        except StopIteration:
            raise ValueError(f"Namespace not found: {ns}") from None
        else:
            return (ns_obj, clsname)

    if not ns:
        classes: list[ClassName] = []
        for ns_obj in enumerate_namespaces():
            if clsname in ns_obj:
                classes.append((ns_obj, clsname))
        if len(classes) < 1:
            raise ValueError(f"Class not found: {uclsname!r}")
        if len(classes) > 1:
            if not ns:
                raise ValueError(
                    f"Multiple classes {clsname!r} found, specify namespace"
                )
            raise RuntimeError(
                f"Multiple classes {clsname!r} found in namespace {ns}"
            )
        return classes[0]

    raise TypeError(f"Malformed class name: {uclsname!r}")


@t.overload
def wrap_xml(
    model: capellambse.MelodyModel, element: etree._Element, /
) -> t.Any: ...
@t.overload
def wrap_xml(
    model: capellambse.MelodyModel, element: etree._Element, /, type: type[T]
) -> T: ...
def wrap_xml(
    model: capellambse.MelodyModel,
    element: etree._Element,
    /,
    type: type[T] | None = None,
) -> T | t.Any:
    """Wrap an XML element with the appropriate high-level proxy class.

    If *type* is a subclass of the element's declared type, and it belongs to a
    namespace whose URL starts with the value of
    :data:`capellambse.model.VIRTUAL_NAMESPACE_PREFIX`, it is used instead of
    the declared type.

    Otherwise, *type* will be verified to be a superclass of (or exactly match)
    the element's declared type. A mismatch will result in an error being
    raised at runtime. This may be used to benefit more from static type
    checkers.
    """
    try:
        cls = model.resolve_class(element)
    except (UnknownNamespaceError, MissingClassError) as err:
        LOGGER.warning("Current metamodel is incomplete: %s", err)
        cls = ModelElement

    if type is not None:
        try:
            ns: Namespace = type.__capella_namespace__
        except AttributeError:
            raise TypeError(
                f"Class does not belong to a namespace: {type.__name__}"
            ) from None

        if ns.uri.startswith(VIRTUAL_NAMESPACE_PREFIX):
            if not issubclass(type, cls):
                raise TypeError(
                    f"Requested virtual type {type.__name__!r}"
                    f" is not a subtype of declared type {cls.__name__!r}"
                    f" for element with ID {element.get('id')!r}"
                )
            cls = type
        elif type is not ModelElement and not issubclass(cls, type):
            raise RuntimeError(
                f"Class mismatch: requested {type!r}, but found {cls!r} in XML"
            )

    obj = cls.__new__(cls)
    obj._model = model  # type: ignore[misc]
    obj._element = element  # type: ignore[misc]
    return obj


@deprecated(
    "find_wrapper is deprecated,"
    " use resolve_class_name or MelodyModel.resolve_class instead"
)
@functools.cache
def find_wrapper(typehint: str) -> tuple[type[ModelObject], ...]:
    """Find the possible wrapper classes for the hinted type.

    The typehint is either a single class name, or a namespace prefix
    and class name separated by ``:``. This function searches for all
    known wrapper classes that match the given namespace prefix (if any)
    and which have the given name, and returns them as a tuple. If no
    matching wrapper classes are found, an empty tuple is returned.
    """
    namespaces: list[tuple[Namespace, av.AwesomeVersion | None]]
    if typehint.startswith("{"):
        qname = etree.QName(typehint)
        assert qname.namespace is not None
        clsname = qname.localname
        namespaces = []
        for i in enumerate_namespaces():
            v = i.match_uri(qname.namespace)
            if v is True:
                namespaces.append((i, None))
            elif v:
                namespaces.append((i, v))
        if not namespaces:
            raise ValueError(
                f"Unknown namespace: {qname.namespace!r}."
                " Check that relevant extensions are installed properly."
            )

    elif ":" in typehint:
        nsname, clsname = typehint.rsplit(":", 1)
        namespaces = [
            (i, i.maxver) for i in enumerate_namespaces() if i.alias == nsname
        ]
        if not namespaces:
            raise ValueError(
                f"Unknown namespace alias: {nsname!r}."
                " Check that relevant extensions are installed properly."
            )

    else:
        namespaces = [(i, i.maxver) for i in enumerate_namespaces()]
        clsname = typehint

    candidates: list[type[ModelObject]] = []
    for ns, nsver in namespaces:
        with contextlib.suppress(MissingClassError):
            candidates.append(ns.get_class(clsname, nsver))
    return tuple(candidates)
