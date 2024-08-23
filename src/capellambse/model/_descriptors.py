# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

__all__ = [
    "Accessor",
    "Alias",
    "Allocation",
    "AlternateAccessor",
    "Association",
    "AttributeMatcherAccessor",
    "Backref",
    "BrokenModelError",
    "Containment",
    "DeepProxyAccessor",
    "DeprecatedAccessor",
    "DirectProxyAccessor",
    "Filter",
    "IndexAccessor",
    "InvalidModificationError",
    "MissingValueError",
    "NewObject",
    "NonUniqueMemberError",
    "ParentAccessor",
    "PhysicalAccessor",
    "PhysicalLinkEndsAccessor",
    "Relationship",
    "Single",
    "SpecificationAccessor",
    "TypecastAccessor",
    "WritableAccessor",
    "build_xtype",
    "xtype_handler",
]

import abc
import collections.abc as cabc
import contextlib
import itertools
import logging
import operator
import sys
import types
import typing as t
import warnings

import markupsafe
import typing_extensions as te
from lxml import etree

import capellambse
from capellambse import helpers

from . import T, T_co, U, U_co

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

_NotSpecifiedType = t.NewType("_NotSpecifiedType", object)
_NOT_SPECIFIED = _NotSpecifiedType(object())
"Used to detect unspecified optional arguments"

LOGGER = logging.getLogger(__name__)


@deprecated(
    "@xtype_handler is deprecated and no longer used,"
    " inherit from ModelElement instead"
)
def xtype_handler(
    arch: str | None = None, /, *xtypes: str
) -> cabc.Callable[[type[T]], type[T]]:
    """Register a class as handler for a specific ``xsi:type``.

    No longer used. Instead, declare a :class:`capellambse.model.Namespace`
    containing your classes and register it as entrypoint.
    """
    del arch, xtypes
    return lambda i: i


@deprecated("xsi:type strings are deprecated")
def build_xtype(class_: type[_obj.ModelObject]) -> str:
    ns: _obj.Namespace | None = getattr(class_, "__capella_namespace__", None)
    if ns is None:
        raise ValueError(f"Cannot determine namespace of class {class_!r}")
    return f"{ns.alias}:{class_.__name__}"


class BrokenModelError(RuntimeError):
    """Raised when the model is invalid."""


class MissingValueError(BrokenModelError):
    """Raised when an enforced Single value is absent."""

    obj = property(lambda self: self.args[0])
    attr = property(lambda self: self.args[1])

    def __str__(self) -> str:
        if len(self.args) != 2:
            return super().__str__()
        return (
            f"Missing required value for {self.attr!r}"
            f" on {self.obj._short_repr_()}"
        )


class InvalidModificationError(RuntimeError):
    """Raised when a modification would result in an invalid model."""


class NonUniqueMemberError(ValueError):
    """Raised when a duplicate member is inserted into a list."""

    parent = property(lambda self: self.args[0])
    attr = property(lambda self: self.args[1])
    target = property(lambda self: self.args[2])

    def __str__(self) -> str:
        if len(self.args) != 3:
            return super().__str__()

        return (
            f"Cannot insert: {self.attr!r} of {self.parent._short_repr_()}"
            f" already contains a reference to {self.target._short_repr_()}"
        )


class NewObject:
    """A marker which will create a new model object when inserted.

    This object can be assigned to an attribute of a model object, and
    will be replaced with a new object of the correct type by the
    attribute's accessor.

    For the time being, client code should treat this as opaque object.
    """

    def __init__(self, /, type_hint: str = "", **kw: t.Any) -> None:
        self._type_hint = type_hint
        self._kw = kw

    def __repr__(self) -> str:
        kw = ", ".join(f"{k}={v!r}" for k, v in self._kw.items())
        return f"<new object {self._type_hint!r} ({kw})>"


class Accessor(t.Generic[U_co], metaclass=abc.ABCMeta):
    """Super class for all Accessor types."""

    __name__: str
    __objclass__: type[t.Any]

    def __init__(self) -> None:
        super().__init__()
        self.__doc__ = (
            f"A {type(self).__name__} that was not properly configured."
            " Ensure that ``__set_name__`` gets called after construction."
        )

    @t.overload
    def __get__(self, obj: None, objtype: type[t.Any]) -> te.Self: ...
    @t.overload
    def __get__(
        self, obj: _obj.ModelObject, objtype: type[t.Any] | None = ...
    ) -> U_co: ...
    @abc.abstractmethod
    def __get__(
        self,
        obj: _obj.ModelObject | None,
        objtype: type[t.Any] | None = None,
    ) -> te.Self | U_co:
        pass

    def __set__(self, obj: t.Any, value: t.Any) -> None:
        raise TypeError(f"Cannot set {self} on {type(obj).__name__}")

    def __delete__(self, obj: t.Any) -> None:
        raise TypeError(f"Cannot delete from {self!r} on {type(obj).__name__}")

    def __set_name__(self, owner: type[t.Any], name: str) -> None:
        self.__objclass__ = owner
        self.__name__ = name
        friendly_name = name.replace("_", " ")
        self.__doc__ = f"The {friendly_name} of this {owner.__name__}."

        if isinstance(self, Single):
            return

        super_acc = None
        for cls in owner.__mro__[1:]:
            super_acc = cls.__dict__.get(name)
            if super_acc is not None:
                break

        if isinstance(super_acc, Single):
            super_acc = super_acc.wrapped

        if super_acc is not None and type(super_acc) is type(self):
            self._resolve_super_attributes(super_acc)
        else:
            self._resolve_super_attributes(None)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self._qualname!r}>"

    @property
    def _qualname(self) -> str:
        """Generate the qualified name of this descriptor."""
        if not hasattr(self, "__objclass__"):
            return f"(unknown {type(self).__name__} - call __set_name__)"
        return f"{self.__objclass__.__name__}.{self.__name__}"

    def _resolve_super_attributes(
        self, super_acc: Accessor[t.Any] | None
    ) -> None:
        pass


class Alias(Accessor["U"], t.Generic[U]):
    """Provides an alias to another attribute.

    Parameters
    ----------
    target
        The target to redirect to.
    dirhide
        If True, hide this alias from `dir()` calls.
    """

    __slots__ = ("dirhide", "target")

    def __init__(self, target: str, /, *, dirhide: bool = True) -> None:
        if "." in target:
            raise ValueError(f"Unsupported alias target: {target!r}")

        super().__init__()
        self.target = target
        self.dirhide = dirhide

    @t.overload
    def __get__(self, obj: None, objtype: type[t.Any]) -> te.Self: ...
    @t.overload
    def __get__(
        self,
        obj: _obj.ModelObject,
        objtype: type[t.Any] | None = ...,
    ) -> U: ...
    def __get__(
        self,
        obj: _obj.ModelObject | None,
        objtype: type[t.Any] | None = None,
    ) -> te.Self | U:
        if obj is None:
            return self
        return getattr(obj, self.target)

    def __set__(
        self, obj: _obj.ModelObject, value: U | cabc.Iterable[U]
    ) -> None:
        setattr(obj, self.target, value)

    def __delete__(self, obj: _obj.ModelObject) -> None:
        delattr(obj, self.target)

    def __set_name__(self, owner: type[t.Any], name: str) -> None:
        if not hasattr(owner, self.target):
            raise TypeError(
                f"Cannot create alias {owner.__name__}.{name}:"
                f" Target {self.target!r} is not defined"
                " (make sure to define the Alias after the target, not before)"
            )

        alt = getattr(owner, self.target)
        if isinstance(alt, DeprecatedAccessor) or (
            isinstance(alt, property) and hasattr(alt.fget, "__deprecated__")
        ):
            warnings.warn(
                (
                    f"Alias {owner.__name__}.{name}:"
                    f" Target {self.target!r} is deprecated"
                ),
                DeprecationWarning,
                stacklevel=2,
            )

        super().__set_name__(owner, name)

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} {self._qualname!r}"
            f" to {self.target!r}{' (hidden)' * self.dirhide}>"
        )


class DeprecatedAccessor(Accessor[T_co]):
    """Provides a deprecated alias to another attribute."""

    __slots__ = ("alternative",)

    def __init__(self, alternative: str, /) -> None:
        super().__init__()
        self.alternative = alternative

    @t.overload
    def __get__(self, obj: None, objtype: type[t.Any]) -> te.Self: ...
    @t.overload
    def __get__(
        self,
        obj: _obj.ModelObject,
        objtype: type[t.Any] | None = ...,
    ) -> T_co: ...
    def __get__(
        self,
        obj: _obj.ModelObject | None,
        objtype: type[t.Any] | None = None,
    ) -> te.Self | T_co:
        if obj is None:
            return self

        self.__warn()
        return getattr(obj, self.alternative)

    def __set__(self, obj: _obj.ModelObject, value: t.Any) -> None:
        self.__warn()
        setattr(obj, self.alternative, value)

    def __delete__(self, obj: _obj.ModelObject) -> None:
        self.__warn()
        delattr(obj, self.alternative)

    def __set_name__(self, owner: type[t.Any], name: str) -> None:
        if not hasattr(owner, self.alternative):
            raise TypeError(
                f"Cannot deprecate {owner.__name__}.{name}:"
                f" Alternative {self.alternative!r} is not defined"
                " (make sure to define the DeprecatedAccessor"
                " after the alternative, not before)"
            )

        alt = getattr(owner, self.alternative)
        if isinstance(alt, DeprecatedAccessor) or (
            isinstance(alt, property) and hasattr(alt.fget, "__deprecated__")
        ):
            raise TypeError(
                f"Cannot deprecate {owner.__name__}.{name}:"
                f" Alternative {self.alternative!r} is also deprecated"
            )

        super().__set_name__(owner, name)

    def __warn(self) -> None:
        msg = f"{self._qualname} is deprecated, use {self.alternative} instead"
        warnings.warn(msg, FutureWarning, stacklevel=3)

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} {self._qualname!r},"
            f" use {self.alternative!r} instead>"
        )


class Single(Accessor[T_co | None], t.Generic[T_co]):
    """An Accessor wrapper that ensures there is exactly one value.

    This Accessor is used to wrap other Accessors that return multiple
    values, such as :class:`Containment`, :class:`Association` or
    :class:`Allocation`. Instead of returning a list, Single ensures
    that the list from the wrapped accessor contains exactly one
    element, and returns that element directly.

    Parameters
    ----------
    wrapped
        The accessor to wrap. This accessor must return a list (i.e. it
        is not possible to nest *Single* descriptors). The instance
        passed here should also not be used anywhere else.
    enforce
        Whether to enforce that there is exactly one value.

        If enforce False and the list obtained from the wrapped accessor
        is empty, this accessor returns None; if there is at least one
        element in it, the first element is returned.

        If enforce is True, a list which doesn't have exactly one
        element will cause a :class:`MissingValueError` to be raised,
        which is a subclass of :class:`BrokenModelError`.

        Defaults to False.

    Examples
    --------
    >>> class Foo(capellacore.CapellaElement):
    ...     bar = Single["Bar"](Containment("bar", (NS, "Bar")))
    """

    def __init__(
        self,
        wrapped: Accessor[_obj.ElementList[T_co]],
        enforce: bool = False,
    ) -> None:
        """Create a new single-value descriptor."""
        self.wrapped: t.Final = wrapped
        self.enforce: t.Final = enforce

    @t.overload
    def __get__(self, obj: None, objtype: type[t.Any]) -> te.Self: ...
    @t.overload
    def __get__(
        self, obj: _obj.ModelObject, objtype: type[t.Any] | None = None
    ) -> T_co | None: ...
    def __get__(
        self, obj: _obj.ModelObject | None, objtype: t.Any | None = None
    ) -> te.Self | T_co | None:
        """Retrieve the value of the attribute."""
        if obj is None:
            return self

        objs: t.Any = self.wrapped.__get__(obj, type(obj))
        if not isinstance(objs, _obj.ElementList):
            raise RuntimeError(
                f"Expected a list from wrapped accessor on {self._qualname},"
                f" got {type(objs).__name__}"
            )

        if objs:
            return objs[0]
        if self.enforce:
            raise MissingValueError(obj, self.__name__)
        return None

    def __set__(
        self, obj: _obj.ModelObject, value: _obj.ModelObject | None
    ) -> None:
        """Set the value of the attribute."""
        self.wrapped.__set__(obj, [value])

    def __delete__(self, obj: _obj.ModelObject) -> None:
        """Delete the attribute."""
        if self.enforce:
            o = getattr(obj, "_short_repr_", obj.__repr__)()
            raise InvalidModificationError(
                f"Cannot delete required attribute {self._qualname!r} from {o}"
            )
        self.wrapped.__delete__(obj)

    def __set_name__(self, owner: type[_obj.ModelObject], name: str) -> None:
        """Set the name and owner of the descriptor."""
        self.wrapped.__set_name__(owner, name)
        super().__set_name__(owner, name)

    def __repr__(self) -> str:
        if self.enforce:
            level = "exactly one"
        else:
            level = "the first"
        wrapped = repr(self.wrapped).replace(" " + repr(self._qualname), "")
        return f"<Single {self._qualname!r}, {level} of {wrapped}>"

    def purge_references(
        self, obj: _obj.ModelObject, target: _obj.ModelObject
    ) -> contextlib.AbstractContextManager[None]:
        if hasattr(self.wrapped, "purge_references"):
            return self.wrapped.purge_references(obj, target)
        return contextlib.nullcontext(None)


class Relationship(Accessor["_obj.ElementList[T_co]"], t.Generic[T_co]):
    list_type: type[_obj.ElementListCouplingMixin]
    list_extra_args: cabc.Mapping[str, t.Any]
    single_attr: str | None

    def __init__(
        self,
        *,
        mapkey: str | None,
        mapvalue: str | None,
        fixed_length: int,
        single_attr: str | None,
        legacy_by_type: bool = False,
    ) -> None:
        self.list_extra_args = {
            "fixed_length": fixed_length,
            "legacy_by_type": legacy_by_type,
            "mapkey": mapkey,
            "mapvalue": mapvalue,
        }
        self.single_attr = single_attr
        self.list_type = make_coupled_list_type(self)

    @t.overload
    def __get__(self, obj: None, objtype: type[t.Any]) -> te.Self: ...
    @t.overload
    def __get__(
        self, obj: _obj.ModelObject, objtype: type[t.Any] | None = ...
    ) -> _obj.ElementList[T_co]: ...
    @abc.abstractmethod
    def __get__(
        self,
        obj: _obj.ModelObject | None,
        objtype: type[t.Any] | None = None,
    ) -> te.Self | _obj.ElementList[T_co]:
        pass

    @abc.abstractmethod
    def __set__(
        self,
        obj: _obj.ModelObject,
        value: cabc.Iterable[T_co | NewObject],
    ) -> None:
        pass

    def __delete__(self, obj: _obj.ModelObject) -> None:
        self.__set__(obj, [])

    @abc.abstractmethod
    def insert(
        self,
        elmlist: _obj.ElementListCouplingMixin,
        index: int,
        value: T_co | NewObject,
        *,
        bounds: tuple[_obj.ClassName, ...] = (),
    ) -> T_co:
        """Insert the ``value`` object into the model.

        The object must be inserted at an appropriate place, so that, if
        ``elmlist`` were to be created afresh, ``value`` would show up
        at index ``index``.

        Returns the value that was just inserted. This is useful if the
        incoming value was a :class:`NewObject`, in which case the
        return value is the newly created object.
        """

    @abc.abstractmethod
    def delete(
        self,
        elmlist: _obj.ElementListCouplingMixin,
        obj: _obj.ModelObject,
    ) -> None:
        """Delete the ``obj`` from the model."""

    def purge_references(
        self, obj: _obj.ModelObject, target: _obj.ModelObject
    ) -> contextlib.AbstractContextManager[None]:
        """Purge references to the given object from the model.

        This method is called while deleting physical objects, in order
        to get rid of references to that object (and its descendants).
        Reference purging is done in two steps, which is why this method
        returns a context manager.

        The first step, executed by the ``__enter__`` method, collects
        references to the target and ensures that deleting them would
        result in a valid model. If any validity constraints would be
        violated, an exception is raised to indicate as such, and the
        whole operation is aborted.

        Once all ``__enter__`` methods have been called, the target
        object is deleted from the model. Then all ``__exit__`` methods
        are called, which triggers the actual deletion of all previously
        discovered references.

        As per the context manager protocol, ``__exit__`` will always be
        called after ``__enter__``, even if the operation is to be
        aborted. The ``__exit__`` method must therefore inspect whether
        an exception was passed in or not in order to know whether the
        operation succeeded.

        In order to not confuse other context managers and keep the
        model consistent, ``__exit__`` must not raise any further
        exceptions. Exceptions should instead be logged to stderr, for
        example by using the :py:meth:`logging.Logger.exception`
        facility.

        The ``purge_references`` method will only be called for Accessor
        instances that actually contain a reference.

        Parameters
        ----------
        obj
            The model object to purge references from.
        target
            The object that is to be deleted; references to this object
            will be purged.

        Returns
        -------
        contextlib.AbstractContextManager
            A context manager that deals with purging references in a
            transactional manner.

        Raises
        ------
        InvalidModificationError
            Raised by the returned context manager's ``__enter__``
            method if the attempted modification would result in an
            invalid model. Note that it is generally preferred to allow
            the operation and take the necessary steps to keep the model
            consistent, if possible. This can be achieved for example by
            deleting dependent objects along with the original deletion
            target.
        Exception
            Any exception may be raised before ``__enter__`` returns in
            order to abort the transaction and prevent the ``obj`` from
            being deleted. No exceptions must be raised by ``__exit__``.

        Examples
        --------
        A simple implementation for purging a single object reference
        could look like this:

        .. code-block:: python

           @contextlib.contextmanager
           def purge_references(self, obj, target):
               assert self.__get__(obj, type(obj)) == target

               yield

               try:
                   self.__delete__(obj)
               except Exception:
                   LOGGER.exception("Could not purge a dangling reference")
        """
        del obj, target
        return contextlib.nullcontext(None)

    def _resolve_super_attributes(
        self, super_acc: Accessor[t.Any] | None
    ) -> None:
        assert isinstance(super_acc, Relationship | None)

        super()._resolve_super_attributes(super_acc)
        if super_acc is None:
            return

        if self.list_extra_args["fixed_length"] is None:
            self.list_extra_args["fixed_length"] = super_acc.list_extra_args[  # type: ignore[index]
                "fixed_length"
            ]
        if self.list_extra_args["mapkey"] is None:
            self.list_extra_args["mapkey"] = super_acc.list_extra_args[  # type: ignore[index]
                "mapkey"
            ]
            if self.list_extra_args["mapvalue"] is None:
                self.list_extra_args["mapvalue"] = super_acc.list_extra_args[  # type: ignore[index]
                    "mapvalue"
                ]
        if self.single_attr is None:
            self.single_attr = super_acc.single_attr


@deprecated("WritableAccessor is deprecated, use Relationship instead")
class WritableAccessor(Accessor["_obj.ElementList[T_co]"], t.Generic[T_co]):
    """An Accessor that also provides write support on lists it returns."""

    aslist: type[_obj.ElementListCouplingMixin] | None
    class_: type[T_co]
    list_extra_args: cabc.Mapping[str, t.Any]
    single_attr: str | None

    def __init__(
        self,
        *args: t.Any,
        aslist: type[_obj.ElementList] | None,
        single_attr: str | None = None,
        **kw: t.Any,
    ) -> None:
        super().__init__(*args, **kw)
        self.single_attr = single_attr
        if aslist is not None:
            self.aslist = type(
                "Coupled" + aslist.__name__,
                (_obj.ElementListCouplingMixin, aslist),
                {"_accessor": self},
            )
            self.aslist.__module__ = __name__
        else:
            self.aslist = None

    def __set__(
        self,
        obj: _obj.ModelObject,
        value: T_co | NewObject | cabc.Iterable[T_co | NewObject],
    ) -> None:
        raise TypeError(f"Cannot set {self} on {type(obj).__name__}")

    def create(
        self,
        elmlist: _obj.ElementListCouplingMixin,
        typehint: str | None = None,
        /,
        **kw: t.Any,
    ) -> T_co:
        """Create and return a new element of type ``elmclass``.

        Parameters
        ----------
        elmlist
            The (coupled) :py:class:`~capellambse.model.ElementList` to
            insert the new object into.
        typehint
            Hints for finding the correct type of element to create. Can
            either be a full or shortened ``xsi:type`` string, or an
            abbreviation defined by the specific Accessor instance.
        kw
            Initialize the properties of the new object. Depending on
            the object's type, some attributes may be required.
        """
        del elmlist, typehint, kw
        raise TypeError(f"Cannot create objects on {self}")

    def create_singleattr(
        self, elmlist: _obj.ElementListCouplingMixin, arg: t.Any, /
    ) -> T_co:
        """Create an element that only has a single attribute of interest."""
        if self.single_attr is None:
            raise TypeError(
                "Cannot create object from string, a dictionary is required"
            )
        return self.create(elmlist, **{self.single_attr: arg})

    def insert(
        self,
        elmlist: _obj.ElementListCouplingMixin,
        index: int,
        value: _obj.ModelObject | NewObject,
    ) -> None:
        """Insert the ``value`` object into the model.

        The object must be inserted at an appropriate place, so that, if
        ``elmlist`` were to be created afresh, ``value`` would show up
        at index ``index``.
        """
        raise NotImplementedError(f"Cannot insert objects into {self}")

    def delete(
        self,
        elmlist: _obj.ElementListCouplingMixin,
        obj: _obj.ModelObject,
    ) -> None:
        """Delete the ``obj`` from the model."""
        raise NotImplementedError(f"Cannot delete object from {self}")

    def _create(
        self,
        parent: _obj.ModelObject,
        xmltag: str | None,
        typehint: str | None,
        /,
        **kw: t.Any,
    ) -> T_co:
        if typehint:
            elmclass, _ = self._match_xtype(typehint)
        else:
            elmclass, _ = self._guess_xtype()
        assert elmclass is not None

        want_id: str | None = None
        if "uuid" in kw:
            want_id = kw.pop("uuid")

        pelem = parent._element
        with parent._model._loader.new_uuid(pelem, want=want_id) as obj_id:
            return elmclass(parent._model, pelem, xmltag, uuid=obj_id, **kw)

    def _make_list(self, parent_obj, elements):
        assert hasattr(self, "class_")
        assert hasattr(self, "list_extra_args")
        if self.aslist is None:
            return no_list(self, parent_obj._model, elements, self.class_)
        return self.aslist(
            parent_obj._model,
            elements,
            self.class_,
            parent=parent_obj,
            **self.list_extra_args,
        )

    def _match_xtype(self, hint: str, /) -> tuple[type[T_co], str]:
        """Find the right class for the given ``xsi:type``."""
        if not isinstance(hint, str):
            raise TypeError(
                f"Expected str as first type, got {type(hint).__name__!r}"
            )

        (cls,) = t.cast(tuple[type[T_co]], _obj.find_wrapper(hint))
        return (cls, build_xtype(cls))  # type: ignore[deprecated]

    def _guess_xtype(self) -> tuple[type[T_co], str]:
        try:
            super_guess = super()._guess_xtype  # type: ignore[misc]
        except AttributeError:
            pass
        else:
            return super_guess()
        raise TypeError(f"{self._qualname} requires a type hint")

    def purge_references(
        self, obj: _obj.ModelObject, target: _obj.ModelObject
    ) -> contextlib.AbstractContextManager[None]:
        """Purge references to the given object from the model.

        This method is called while deleting physical objects, in order
        to get rid of references to that object (and its descendants).
        Reference purging is done in two steps, which is why this method
        returns a context manager.

        The first step, executed by the ``__enter__`` method, collects
        references to the target and ensures that deleting them would
        result in a valid model. If any validity constraints would be
        violated, an exception is raised to indicate as such, and the
        whole operation is aborted.

        Once all ``__enter__`` methods have been called, the target
        object is deleted from the model. Then all ``__exit__`` methods
        are called, which triggers the actual deletion of all previously
        discovered references.

        As per the context manager protocol, ``__exit__`` will always be
        called after ``__enter__``, even if the operation is to be
        aborted. The ``__exit__`` method must therefore inspect whether
        an exception was passed in or not in order to know whether the
        operation succeeded.

        In order to not confuse other context managers and keep the
        model consistent, ``__exit__`` must not raise any further
        exceptions. Exceptions should instead be logged to stderr, for
        example by using the :py:meth:`logging.Logger.exception`
        facility.

        The ``purge_references`` method will only be called for Accessor
        instances that actually contain a reference.

        Parameters
        ----------
        obj
            The model object to purge references from.
        target
            The object that is to be deleted; references to this object
            will be purged.

        Returns
        -------
        contextlib.AbstractContextManager
            A context manager that deals with purging references in a
            transactional manner.

        Raises
        ------
        InvalidModificationError
            Raised by the returned context manager's ``__enter__``
            method if the attempted modification would result in an
            invalid model. Note that it is generally preferred to allow
            the operation and take the necessary steps to keep the model
            consistent, if possible. This can be achieved for example by
            deleting dependent objects along with the original deletion
            target.
        Exception
            Any exception may be raised before ``__enter__`` returns in
            order to abort the transaction and prevent the ``obj`` from
            being deleted. No exceptions must be raised by ``__exit__``.

        Examples
        --------
        A simple implementation for purging a single object reference
        could look like this:

        .. code-block:: python

           @contextlib.contextmanager
           def purge_references(self, obj, target):
               assert self.__get__(obj, type(obj)) == target

               yield

               try:
                   self.__delete__(obj)
               except Exception:
                   LOGGER.exception("Could not purge a dangling reference")
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support purging references"
        )


@deprecated("PhysicalAccessor is deprecated, use Relationship instead")
class PhysicalAccessor(Accessor["_obj.ElementList[T_co]"], t.Generic[T_co]):
    """Helper super class for accessors that work with real elements."""

    __slots__ = (
        "aslist",
        "class_",
        "list_extra_args",
        "xtypes",
    )

    aslist: type[_obj.ElementList] | None
    class_: type[T_co]
    list_extra_args: cabc.Mapping[str, t.Any]
    xtypes: cabc.Set[str]

    def __init__(
        self,
        class_: type[T_co],
        xtypes: (
            str
            | type[_obj.ModelObject]
            | cabc.Iterable[str | type[_obj.ModelObject]]
            | None
        ) = None,
        *,
        aslist: type[_obj.ElementList[T_co]] | None = None,
        mapkey: str | None = None,
        mapvalue: str | None = None,
        fixed_length: int = 0,
    ) -> None:
        super().__init__()
        if xtypes is None:
            self.xtypes = (
                {build_xtype(class_)}  # type: ignore[deprecated]
                if class_ is not _obj.ModelElement
                else set()
            )
        elif isinstance(xtypes, type):
            assert issubclass(xtypes, _obj.ModelElement)
            self.xtypes = {build_xtype(xtypes)}  # type: ignore[deprecated]
        elif isinstance(xtypes, str):
            self.xtypes = {xtypes}
        else:
            self.xtypes = {
                i if isinstance(i, str) else build_xtype(i)  # type: ignore[deprecated]
                for i in xtypes
            }

        self.aslist = aslist
        self.class_ = class_
        self.list_extra_args = {}
        if mapkey is not None:
            self.list_extra_args["mapkey"] = mapkey
        if mapvalue is not None:
            self.list_extra_args["mapvalue"] = mapvalue
        if fixed_length > 0:
            self.list_extra_args["fixed_length"] = fixed_length
        elif fixed_length < 0:
            raise ValueError("List length cannot be negative")

    def _guess_xtype(self) -> tuple[type[T_co], str]:
        """Try to guess the type of element that should be created."""
        if self.class_ is _obj.ModelElement or self.class_ is None:
            raise ValueError("Multiple object types that can be created")
        if not self.xtypes:
            raise ValueError("No matching `xsi:type` found")
        if len(self.xtypes) > 1:
            raise ValueError("Multiple matching `xsi:type`s")
        return self.class_, next(iter(self.xtypes))

    def _make_list(self, parent_obj, elements):
        if self.aslist is None:
            return no_list(self, parent_obj._model, elements, self.class_)
        return self.aslist(
            parent_obj._model,
            elements,
            self.class_,
            **self.list_extra_args,
        )


@deprecated("DirectProxyAccessor is deprecated, use Containment instead")
class DirectProxyAccessor(WritableAccessor[T_co], PhysicalAccessor[T_co]):
    """Creates proxy objects on the fly."""

    __slots__ = ("follow_abstract", "rootelem")

    aslist: type[_obj.ElementListCouplingMixin] | None
    class_: type[T_co]
    single_attr: str | None

    def __init__(
        self,
        class_: type[T_co],
        xtypes: (
            str | type[T_co] | cabc.Iterable[str | type[T_co]] | None
        ) = None,
        *,
        aslist: type[_obj.ElementList] | None = None,
        mapkey: str | None = None,
        mapvalue: str | None = None,
        fixed_length: int = 0,
        follow_abstract: bool = False,
        rootelem: (
            str
            | type[_obj.ModelElement]
            | cabc.Sequence[str | type[_obj.ModelElement]]
            | None
        ) = None,
        single_attr: str | None = None,
    ):
        r"""Create a DirectProxyAccessor.

        Parameters
        ----------
        class_
            The proxy class.
        xtypes
            The ``xsi:type``\ (s) of the child element(s). If None, then
            the constructed proxy will be passed the original element
            instead of a child.
        aslist
            If None, only a single element must match, which will be
            returned directly. If not None, must be a subclass of
            :class:`~capellambse.model.ElementList`, which will be used
            to return a list of all matched objects.
        mapkey
            Specify the attribute to look up when the returned list is
            indexed with a str. If not specified, str indexing is not
            possible.

            Ignored if *aslist* is not specified.
        mapvalue
            If specified, return this attribute of the found object when
            using str indices into the returned list. If not specified,
            the found object itself is returned.

            Ignored if *aslist* is not specified.
        fixed_length
            When non-zero, the returned list will try to stay at exactly
            this length, by not allowing to insert or delete beyond this
            many members.

            Ignored if *aslist* is not specified.
        follow_abstract
            Follow the link in the ``abstractType`` XML attribute of
            each list member and instantiate that object instead. The
            default is to instantiate the child elements directly.
        rootelem
            A class or ``xsi:type`` (or list thereof) that defines the
            path from the current object's XML element to the search
            root. If None, the current element will be used directly.
        single_attr
            If objects can be created with only a single attribute
            specified, this argument is the name of that attribute. This
            :meth:`~capellambse.model.WritableAccessor.create_singleattr`.
        """
        super().__init__(
            class_,
            xtypes,
            aslist=aslist,
            mapkey=mapkey,
            mapvalue=mapvalue,
            fixed_length=fixed_length,
            single_attr=single_attr,
        )
        self.follow_abstract: bool = follow_abstract
        if rootelem is None:
            self.rootelem: cabc.Sequence[str] = []
        elif isinstance(rootelem, str):
            self.rootelem = rootelem.split("/")
        elif isinstance(rootelem, type) and issubclass(
            rootelem, _obj.ModelElement
        ):
            self.rootelem = [build_xtype(rootelem)]  # type: ignore[deprecated]
        else:
            self.rootelem = [
                i if isinstance(i, str) else build_xtype(i)  # type: ignore[deprecated]
                for i in rootelem
            ]

    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:  # pragma: no cover
            return self

        elems = [
            self._resolve(obj, e)
            for e in self._getsubelems(obj)
            if e.get("id") is not None
        ]
        return self._make_list(obj, elems)

    def __set__(
        self,
        obj: _obj.ModelObject,
        value: str | T_co | NewObject | cabc.Iterable[str | T_co | NewObject],
    ) -> None:
        if self.aslist:
            if isinstance(value, str) or not isinstance(value, cabc.Iterable):
                raise TypeError("Can only set list attribute to an iterable")
            list = self.__get__(obj)
            for v in list:
                self.delete(list, v)
            for i, v in enumerate(value):
                if isinstance(v, str):
                    self.create_singleattr(list, v)
                else:
                    self.insert(list, i, v)
        else:
            if isinstance(value, cabc.Iterable) and not isinstance(value, str):
                raise TypeError("Cannot set non-list attribute to an iterable")
            if not isinstance(value, NewObject):
                raise NotImplementedError(
                    "Moving model objects is not supported yet"
                )
            if self.__get__(obj) is not None:
                raise NotImplementedError(
                    "Replacing model objects is not supported yet"
                )
            self._create(obj, None, value._type_hint, **value._kw)

    def __delete__(self, obj: _obj.ModelObject) -> None:
        if self.rootelem:
            raise TypeError("Cannot delete due to 'rootelem' being set")
        if self.follow_abstract:
            raise TypeError("Cannot delete when following abstract types")

        if self.aslist is not None:
            self._delete(obj._model, list(self._getsubelems(obj)))
        else:
            raise TypeError(f"Cannot delete {self._qualname}")

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self._qualname!r} of {self.xtypes!r}>"

    def _delete(
        self, model: capellambse.MelodyModel, elements: list[etree._Element]
    ) -> None:
        all_elements = (
            list(
                itertools.chain.from_iterable(
                    model._loader.iterdescendants_xt(i) for i in elements
                )
            )
            + elements
        )
        with contextlib.ExitStack() as stack:
            for elm in all_elements:
                if elm.get("id") is None:
                    continue

                obj = _obj.wrap_xml(model, elm)
                for ref, attr, _ in model.find_references(obj):
                    acc = getattr(type(ref), attr)
                    if acc is self or not isinstance(
                        acc, WritableAccessor | Relationship | Single
                    ):
                        continue
                    stack.enter_context(acc.purge_references(ref, obj))

            for elm in elements:
                parent = elm.getparent()
                assert parent is not None
                model._loader.idcache_remove(elm)
                parent.remove(elm)

    def _resolve(
        self, obj: _obj.ModelObject, elem: etree._Element
    ) -> etree._Element:
        if self.follow_abstract:
            if abstype := elem.get("abstractType"):
                elem = obj._model._loader[abstype]
            else:
                raise RuntimeError("Broken XML: No abstractType defined?")
        return elem

    def _getsubelems(
        self, obj: _obj.ModelObject
    ) -> cabc.Iterator[etree._Element]:
        return itertools.chain.from_iterable(
            obj._model._loader.iterchildren_xt(i, *iter(self.xtypes))
            for i in self._findroots(obj)
        )

    def _findroots(self, obj: _obj.ModelObject) -> list[etree._Element]:
        roots = [obj._element]
        for xtype in self.rootelem:
            roots = list(
                itertools.chain.from_iterable(
                    obj._model._loader.iterchildren_xt(i, xtype) for i in roots
                )
            )
        return roots

    def create(
        self,
        elmlist: _obj.ElementListCouplingMixin,
        typehint: str | None = None,
        /,
        **kw: t.Any,
    ) -> T_co:
        if self.rootelem:
            raise TypeError(f"Cannot create objects on {self}")

        return self._create(elmlist._parent, None, typehint, **kw)

    def insert(
        self,
        elmlist: _obj.ElementListCouplingMixin,
        index: int,
        value: _obj.ModelObject | NewObject,
    ) -> None:
        if isinstance(value, NewObject):
            raise NotImplementedError(
                "Creating new objects in lists with new_object() is not"
                " supported yet"
            )

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
            parent_index = len(elmlist._parent._element)
        elmlist._parent._element.insert(parent_index, value._element)
        elmlist._model._loader.idcache_index(value._element)

    def delete(
        self,
        elmlist: _obj.ElementListCouplingMixin,
        obj: _obj.ModelObject,
    ) -> None:
        assert obj._model is elmlist._model
        self._delete(obj._model, [obj._element])

    @contextlib.contextmanager
    def purge_references(
        self, obj: _obj.ModelObject, target: _obj.ModelObject
    ) -> cabc.Iterator[None]:
        del obj, target
        yield


@deprecated(
    "DeepProxyAccessor is deprecated, use @property and model.search() instead"
)
class DeepProxyAccessor(PhysicalAccessor[T_co]):
    """A DirectProxyAccessor that searches recursively through the tree."""

    __slots__ = ()

    def __init__(
        self,
        class_: type[T_co],
        xtypes: (
            str | type[T_co] | cabc.Iterable[str | type[T_co]] | None
        ) = None,
        *,
        aslist: type[_obj.ElementList] | None = None,
        rootelem: (
            type[_obj.ModelElement]
            | cabc.Sequence[type[_obj.ModelElement]]
            | None
        ) = None,
    ) -> None:
        """Create a DeepProxyAccessor.

        Parameters
        ----------
        class_
            The proxy class.
        xtypes
            The ``xsi:type`` (or types) to search for. If None, defaults
            to the type of the passed ``class_``.
        aslist
            A subclass of :class:`~capellambse.model.ElementList` to use
            for returning a list of all matched objects. If not
            specified, defaults to the base ElementList.
        rootelem
            Limit the search scope to objects of this type, nested below
            the current object. When passing a sequence, defines a path
            of object types to follow.
        """
        if aslist is None:
            aslist = _obj.ElementList
        super().__init__(
            class_,
            xtypes,
            aslist=aslist,
        )
        if rootelem is None:
            self.rootelem: cabc.Sequence[str] = ()
        elif isinstance(rootelem, type) and issubclass(
            rootelem, _obj.ModelElement
        ):
            self.rootelem = (build_xtype(rootelem),)  # type: ignore[deprecated]
        elif not isinstance(rootelem, str):  # type: ignore[unreachable]
            self.rootelem = tuple(build_xtype(i) for i in rootelem)  # type: ignore[deprecated]
        else:
            raise TypeError(
                "Invalid 'rootelem', expected a type or list of types: "
                + repr(rootelem)
            )

    @t.overload
    def __get__(self, obj: None, objtype: type[t.Any]) -> te.Self: ...
    @t.overload
    def __get__(
        self, obj: _obj.ModelObject, objtype: type[t.Any] | None = ...
    ) -> _obj.ElementList[T_co]: ...
    def __get__(
        self,
        obj: _obj.ModelObject | None,
        objtype: type[t.Any] | None = None,
    ) -> te.Self | _obj.ElementList[T_co]:
        del objtype
        if obj is None:  # pragma: no cover
            return self

        elems = [e for e in self._getsubelems(obj) if e.get("id") is not None]
        assert self.aslist is not None
        return self.aslist(obj._model, elems)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self._qualname!r} to {self.class_!r}>"

    def _getsubelems(
        self, obj: _obj.ModelObject
    ) -> cabc.Iterator[etree._Element]:
        ldr = obj._model._loader
        roots = [obj._element]
        for xtype in self.rootelem:
            roots = list(
                itertools.chain.from_iterable(
                    ldr.iterchildren_xt(i, xtype) for i in roots
                )
            )
        for root in roots:
            yield from ldr.iterdescendants_xt(root, *self.xtypes)


class Allocation(Relationship[T_co]):
    """Accesses elements through reference elements."""

    __slots__ = ("alloc_type", "attr", "backattr", "class_", "tag")

    tag: str | None
    alloc_type: _obj.ClassName | None
    class_: _obj.ClassName
    attr: str | None
    backattr: str | None

    @t.overload
    @deprecated(
        "Raw classes, xsi:type strings and 'aslist' are deprecated,"
        " migrate to (Namespace, 'ClassName') tuples and drop aslist=..."
    )
    def __init__(
        self,
        tag: str | None,
        xtype: str | type[_obj.ModelElement],
        /,
        *,
        aslist: type[_obj.ElementList] | None = ...,
        mapkey: str | None = ...,
        mapvalue: str | None = ...,
        attr: str,
        backattr: str | None = ...,
        unique: bool = ...,
        legacy_by_type: bool = ...,
    ) -> None: ...
    @t.overload
    def __init__(
        self,
        tag: str | None,
        alloc_type: _obj.UnresolvedClassName | None,
        class_: _obj.UnresolvedClassName,
        /,
        *,
        mapkey: str | None = ...,
        mapvalue: str | None = ...,
        attr: str | None = ...,
        backattr: str | None = ...,
        legacy_by_type: bool = ...,
    ) -> None: ...
    def __init__(
        self,
        tag: str | None,
        alloc_type: (
            str | type[_obj.ModelElement] | _obj.UnresolvedClassName | None
        ),
        class_: _obj.UnresolvedClassName | _NotSpecifiedType = _NOT_SPECIFIED,
        /,
        *,
        aslist: t.Any = _NOT_SPECIFIED,
        mapkey: str | None = None,
        mapvalue: str | None = None,
        attr: str | None = None,
        backattr: str | None = None,
        unique: bool = True,
        legacy_by_type: bool = False,
    ) -> None:
        """Define an Allocation.

        Allocations use link elements (often named like "SomethingAllocation"),
        which only contain a link to the target and sometimes also the source
        element.

        If the link element has anything other than these, e.g. its own name or
        a type, use Containment instead and create a shortcut to the target
        with a small ``@property``.

        Parameters
        ----------
        tag
            The XML tag that the reference elements will have.
        alloc_type
            The type that the allocation element will have, as a
            ``(Namespace, "ClassName")`` tuple.
        class_
            The type of element that this allocation links to, as a
            ``(Namespace, "ClassName")`` tuple.
        attr
            The attribute on the reference element that contains the
            actual link.
        backattr
            An optional attribute on the reference element to store a
            reference back to the owner (parent) object.
        aslist
            Optionally specify a different subclass of
            :class:`~capellambse.model.ElementList`.
        mapkey
            Specify the attribute to look up when the returned list is
            indexed with a str. If not specified, str indexing is not
            possible.
        mapvalue
            If specified, return this attribute of the found object when
            using str indices into the returned list. If not specified,
            the found object itself is returned.
        unique
            Enforce that each element may only appear once in the list.
            If a duplicate is attempted to be added, an exception will
            be raised. Note that this does not have an effect on lists
            already existing within the loaded model.
        legacy_by_type
            When filtering with 'by_X' etc., make 'type' an alias for
            '__class__'. This was the behavior when using the MixedElementList
            for the *aslist* parameter. Note that this parameter should itself
            be considered deprecated, and only exists to facilitate the
            transition to 'by_class'.
        """
        if not isinstance(tag, str | None):
            raise TypeError(f"tag must be a str, not {type(tag).__name__}")
        if aslist is not _NOT_SPECIFIED:
            warnings.warn(
                "The aslist argument is deprecated and will be removed soon",
                DeprecationWarning,
                stacklevel=2,
            )
            if isinstance(aslist, type) and issubclass(
                aslist, _obj.MixedElementList
            ):
                legacy_by_type = True

        super().__init__(
            mapkey=mapkey,
            mapvalue=mapvalue,
            fixed_length=0,
            single_attr=None,
            legacy_by_type=legacy_by_type,
        )
        self.tag = tag
        self.attr = attr
        self.backattr = backattr
        self.unique = unique

        if alloc_type is None:
            self.alloc_type = None
        elif isinstance(alloc_type, str):
            warnings.warn(
                (
                    "xsi:type strings for Allocation are deprecated,"
                    " use a (Namespace, 'ClassName') tuple instead"
                ),
                DeprecationWarning,
                stacklevel=2,
            )
            if ":" in alloc_type:
                alloc_type = t.cast(
                    tuple[str, str], tuple(alloc_type.rsplit(":", 1))
                )
                self.alloc_type = (
                    _obj.find_namespace(alloc_type[0]),
                    alloc_type[1],
                )
            else:
                self.alloc_type = _obj.resolve_class_name(("", alloc_type))
        elif isinstance(alloc_type, type):
            if not issubclass(alloc_type, _obj.ModelElement):
                raise TypeError(
                    "Allocation class must be a subclass of ModelElement:"
                    f" {alloc_type.__module__}.{alloc_type.__name__}"
                )
            warnings.warn(
                (
                    "Raw classes for Allocation are deprecated,"
                    " use a (Namespace, 'ClassName') tuple instead"
                ),
                DeprecationWarning,
                stacklevel=2,
            )
            self.alloc_type = (
                alloc_type.__capella_namespace__,
                alloc_type.__name__,
            )
        elif isinstance(alloc_type, tuple) and len(alloc_type) == 2:
            self.alloc_type = _obj.resolve_class_name(alloc_type)
        else:
            raise TypeError(
                f"Malformed alloc_type, expected a 2-tuple: {alloc_type!r}"
            )

        if class_ is _NOT_SPECIFIED:
            warnings.warn(
                "Unspecified target class is deprecated",
                DeprecationWarning,
                stacklevel=2,
            )
            self.class_ = (_obj.NS, "ModelElement")
        else:
            self.class_ = _obj.resolve_class_name(class_)

    @t.overload
    def __get__(self, obj: None, objtype: type[t.Any]) -> te.Self: ...
    @t.overload
    def __get__(
        self, obj: _obj.ModelObject, objtype: type[t.Any] | None = ...
    ) -> _obj.ElementList[T_co]: ...
    def __get__(
        self,
        obj: _obj.ModelObject | None,
        objtype: type[t.Any] | None = None,
    ) -> te.Self | _obj.ElementList[T_co]:
        del objtype
        if obj is None:  # pragma: no cover
            return self

        # TODO extend None check to self.tag when removing deprecated features
        if None in (self.alloc_type, self.attr):
            raise RuntimeError(
                f"{type(self).__name__} was not initialized properly;"
                " make sure that __set_name__ gets called"
            )

        elems: list[etree._Element] = []
        seen: set[etree._Element] = set()
        for i in self.__find_refs(obj):
            e = self.__follow_ref(obj, i)
            if e is None:
                continue
            if e not in seen:
                elems.append(e)
                seen.add(e)
        return self.list_type(
            obj._model, elems, parent=obj, **self.list_extra_args
        )

    def __set__(
        self,
        obj: _obj.ModelObject,
        value: T_co | NewObject | cabc.Iterable[T_co | NewObject],
    ) -> None:
        if not isinstance(value, cabc.Iterable):
            warnings.warn(
                (
                    "Assigning a single value onto Allocation is deprecated."
                    f" If {self._qualname!r} is supposed to use single values,"
                    " wrap it in a 'm.Single()'."
                    " Otherwise, update your code to assign a list instead."
                ),
                DeprecationWarning,
                stacklevel=2,
            )
            value = (value,)

        te.assert_type(value, cabc.Iterable[T_co | NewObject])
        if any(isinstance(i, NewObject) for i in value):
            raise TypeError(f"Cannot create objects on {self}")
        value = t.cast(cabc.Iterable[T_co], value)

        # TODO Remove this extra check when removing deprecated features
        if self.tag is None:
            raise TypeError(f"Cannot set: XML tag not set on {self}")
        if None in (self.tag, self.alloc_type, self.attr):
            raise RuntimeError(
                f"{type(self).__name__} was not initialized properly;"
                " make sure that __set_name__ gets called"
            )

        elmlist = self.__get__(obj)
        assert isinstance(elmlist, _obj.ElementListCouplingMixin)
        i = -1
        for i, v in enumerate(value):
            self.insert(elmlist, i, v)
        for o in elmlist[i + 1 :]:
            self.delete(elmlist, o)

    def __delete__(self, obj: _obj.ModelObject) -> None:
        refobjs = list(self.__find_refs(obj))
        for i in refobjs:
            obj._model._loader.idcache_remove(i)
            obj._element.remove(i)

    def __repr__(self) -> str:
        if self.alloc_type is None:
            return f"<Uninitialized {type(self).__name__} - call __set_name__>"
        return (
            f"<{type(self).__name__} {self._qualname!r}"
            f" to {self.class_[0].alias}:{self.class_[1]}"
            f" via {self.tag!r}"
            f" on {self.alloc_type[0].alias}:{self.alloc_type[1]}>"
        )

    def __follow_ref(
        self, obj: _obj.ModelObject, refelm: etree._Element
    ) -> etree._Element | None:
        assert self.attr is not None

        link = refelm.get(self.attr)
        if not link:
            return None
        return obj._model._loader.follow_link(obj._element, link)

    def __find_refs(
        self, obj: _obj.ModelObject
    ) -> cabc.Iterator[etree._Element]:
        assert self.alloc_type is not None
        # TODO add None check for self.tag when removing deprecated features

        target_type = obj._model.qualify_classname(self.alloc_type)
        for refelm in obj._element.iterchildren(tag=self.tag):
            elm_type = helpers.qtype_of(refelm)
            if elm_type == target_type:
                yield refelm

    def __backref(
        self, obj: _obj.ModelObject, target: _obj.ModelObject
    ) -> etree._Element | None:
        for i in self.__find_refs(obj):
            if self.__follow_ref(obj, i) == target._element:
                return i
        return None

    def __create_link(
        self,
        parent: _obj.ModelObject,
        target: _obj.ModelObject,
        *,
        before: _obj.ModelObject | None = None,
    ) -> etree._Element:
        assert self.alloc_type is not None
        assert self.attr is not None
        assert self.tag is not None

        model = parent._model

        if self.unique:
            for i in self.__find_refs(parent):
                if self.__follow_ref(parent, i) is target._element:
                    raise NonUniqueMemberError(parent, self.__name__, target)

        if __debug__:
            alloc_cls = parent._model.resolve_class(self.alloc_type)
            if alloc_cls.__capella_abstract__:
                raise RuntimeError(
                    f"Invalid metamodel: {alloc_cls} is abstract,"
                    f" and cannot be used with Allocation {self._qualname}"
                )

        xtype = parent._model.qualify_classname(self.alloc_type)
        with model._loader.new_uuid(parent._element) as obj_id:
            link = model._loader.create_link(parent._element, target._element)
            refobj = parent._element.makeelement(self.tag)
            self.__insert_refobj(parent, refobj, before=before)
            try:
                refobj.set(helpers.ATT_XT, xtype)
                refobj.set("id", obj_id)
                refobj.set(self.attr, link)
                if self.backattr:
                    backlink = model._loader.create_link(
                        refobj, parent._element
                    )
                    refobj.set(self.backattr, backlink)
                model._loader.idcache_index(refobj)
            except:
                parent._element.remove(refobj)
                raise
        return refobj

    def __insert_refobj(
        self,
        parent: _obj.ModelObject,
        refobj: etree._Element,
        *,
        before: _obj.ModelObject | None,
    ) -> None:
        if before is None:
            parent._element.append(refobj)
        else:
            before_elm = self.__backref(parent, before)
            assert before_elm is not None
            assert before_elm in parent._element
            before_elm.addprevious(refobj)

    def insert(
        self,
        elmlist: _obj.ElementListCouplingMixin,
        index: int,
        value: T_co | NewObject,
        *,
        bounds: tuple[_obj.ClassName, ...] = (),
    ) -> T_co:
        if self.tag is None:
            # TODO Change to RuntimeError when removing deprecated features
            raise NotImplementedError(f"Cannot set: XML tag not set on {self}")
        if isinstance(value, NewObject):
            raise TypeError(f"Cannot create objects on {self}")
        if value._model is not elmlist._parent._model:
            raise ValueError("Cannot insert elements from different models")
        for b in (self.class_, *bounds):
            bcls = elmlist._model.resolve_class(b)
            if not isinstance(value, bcls):
                raise InvalidModificationError(
                    f"Cannot insert into {self._qualname}:"
                    f" Objects must be instances of {b[0].alias}:{b[1]},"
                    f" not {type(value)}"
                )

        try:
            refobj = next(
                r
                for r in self.__find_refs(elmlist._parent)
                if self.__follow_ref(elmlist._parent, r) is value._element
            )
        except StopIteration:
            self.__create_link(
                elmlist._parent,
                value,
                before=elmlist[index] if index < len(elmlist) else None,
            )
        else:
            if index < len(elmlist):
                self.__insert_refobj(
                    elmlist._parent, refobj, before=elmlist[index]
                )
            else:
                self.__insert_refobj(elmlist._parent, refobj, before=None)
        elmlist._elements = list(self.__find_refs(elmlist._parent))
        return t.cast(T_co, value)

    def delete(
        self,
        elmlist: _obj.ElementListCouplingMixin,
        obj: _obj.ModelObject,
    ) -> None:
        parent = elmlist._parent
        for ref in self.__find_refs(parent):
            if self.__follow_ref(parent, ref) == obj._element:
                parent._model._loader.idcache_remove(ref)
                parent._element.remove(ref)
                break
        else:
            raise ValueError("Cannot delete: Target object not in this list")

    @contextlib.contextmanager
    def purge_references(
        self, obj: _obj.ModelObject, target: _obj.ModelObject
    ) -> cabc.Generator[None, None, None]:
        purge: list[etree._Element] = []
        for ref in self.__find_refs(obj):
            if self.__follow_ref(obj, ref) is target._element:
                purge.append(ref)

        yield

        for ref in purge:
            try:
                parent = ref.getparent()
                if parent is None:
                    continue
                parent.remove(ref)
            except Exception:
                LOGGER.exception("Cannot purge dangling ref object %r", ref)

    def _resolve_super_attributes(
        self, super_acc: Accessor[t.Any] | None
    ) -> None:
        assert isinstance(super_acc, Allocation | None)

        super()._resolve_super_attributes(super_acc)

        if self.tag is None and super_acc is not None:
            self.tag = super_acc.tag
        if self.tag is None:
            # TODO change warning to error when removing deprecated features
            warnings.warn(
                "Unspecified XML tag is deprecated",
                DeprecationWarning,
                stacklevel=2,
            )

        if None not in (self.alloc_type, self.attr):
            return
        if super_acc is None:
            raise TypeError(
                f"Cannot inherit {type(self).__name__} configuration:"
                f" No super class of {self.__objclass__.__name__}"
                f" defines {self.__name__!r}"
            )

        if self.alloc_type is None:
            self.alloc_type = super_acc.alloc_type
        if self.attr is None:
            self.attr = super_acc.attr
            if self.backattr is None:
                self.backattr = super_acc.backattr


class Association(Relationship[T_co]):
    """Provides access to elements that are linked in an attribute."""

    __slots__ = ("attr", "class_")

    def __init__(
        self,
        class_: type[T_co] | None | _obj.UnresolvedClassName,
        attr: str | None,
        *,
        aslist: t.Any = _NOT_SPECIFIED,
        mapkey: str | None = None,
        mapvalue: str | None = None,
        fixed_length: int = 0,
        legacy_by_type: bool = False,
    ):
        """Define an Association.

        Associations are stored as simple links in an XML attribute.

        Parameters
        ----------
        class_
            The proxy class. Currently only used for type hints.
        attr
            The XML attribute to handle. If None, the attribute is
            copied from an Association with the same name on the parent
            class.
        aslist
            If None, the attribute contains at most one element
            reference, and either None or the constructed proxy will be
            returned. If not None, must be a subclass of
            :class:`~capellambse.model.ElementList`. It will be used to
            return a list of all matched objects.
        mapkey
            Specify the attribute to look up when the returned list is
            indexed with a str. If not specified, str indexing is not
            possible.
        mapvalue
            If specified, return this attribute of the found object when
            using str indices into the returned list. If not specified,
            the found object itself is returned.
        fixed_length
            When non-zero, the returned list will try to stay at exactly
            this length, by not allowing to insert or delete beyond this
            many members.
        legacy_by_type
            When filtering with 'by_X' etc., make 'type' an alias for
            '__class__'. This was the behavior when using the MixedElementList
            for the *aslist* parameter. Note that this parameter should itself
            be considered deprecated, and only exists to facilitate the
            transition to 'by_class'.
        """
        if aslist is not _NOT_SPECIFIED:
            warnings.warn(
                "The aslist argument is deprecated and will be removed soon",
                DeprecationWarning,
                stacklevel=2,
            )
            if isinstance(aslist, type) and issubclass(
                aslist, _obj.MixedElementList
            ):
                legacy_by_type = True

        super().__init__(
            mapkey=mapkey,
            mapvalue=mapvalue,
            fixed_length=fixed_length,
            single_attr=None,
            legacy_by_type=legacy_by_type,
        )

        if class_ is None:
            warnings.warn(
                (
                    "None as class_ argument to Association is deprecated,"
                    " specify a (Namespace, 'ClassName') tuple"
                ),
                DeprecationWarning,
                stacklevel=2,
            )
            class_ = (_obj.NS, _obj.ModelElement.__name__)
        elif isinstance(class_, type):
            warnings.warn(
                (
                    "Raw classes for Association are deprecated,"
                    " use a (Namespace, 'ClassName') tuple instead"
                ),
                DeprecationWarning,
                stacklevel=2,
            )
            try:
                ns = class_.__capella_namespace__
            except AttributeError:
                raise RuntimeError(
                    f"Invalid class without namespace: {class_!r}"
                ) from None
            class_ = (ns, class_.__name__)
        self.class_ = _obj.resolve_class_name(class_)
        self.attr = attr

    @t.overload
    def __get__(self, obj: None, objtype: type[t.Any]) -> te.Self: ...
    @t.overload
    def __get__(
        self, obj: _obj.ModelObject, objtype: type[t.Any] | None = ...
    ) -> _obj.ElementList[T_co]: ...
    def __get__(
        self,
        obj: _obj.ModelObject | None,
        objtype: type[t.Any] | None = None,
    ) -> te.Self | _obj.ElementList[T_co]:
        del objtype
        if obj is None:  # pragma: no cover
            return self

        if self.attr is None:
            raise RuntimeError(
                f"{type(self).__name__} was not initialized properly;"
                " make sure that __set_name__ gets called"
            )

        elems = obj._model._loader.follow_links(
            obj._element, obj._element.get(self.attr, "")
        )

        return self.list_type(
            obj._model, elems, parent=obj, **self.list_extra_args
        )

    def __set__(
        self,
        obj: _obj.ModelObject,
        value: T_co | NewObject | cabc.Iterable[T_co | NewObject],
    ) -> None:
        if not isinstance(value, cabc.Iterable):
            warnings.warn(
                (
                    "Assigning a single value onto Association is deprecated."
                    f" If {self._qualname!r} is supposed to use single values,"
                    " wrap it in a 'm.Single()'."
                    " Otherwise, update your code to assign a list instead."
                ),
                DeprecationWarning,
                stacklevel=2,
            )
            value = (value,)

        te.assert_type(value, cabc.Iterable[T_co | NewObject])
        if any(isinstance(i, NewObject) for i in value):
            raise TypeError("Cannot create new objects on an Association")
        value = t.cast(cabc.Iterable[T_co], value)

        if self.attr is None:
            raise RuntimeError(
                f"{type(self).__name__} was not initialized properly;"
                " make sure that __set_name__ gets called"
            )

        self.__set_links(obj, value)

    def __delete__(self, obj: _obj.ModelObject) -> None:
        if self.attr is None:
            raise RuntimeError(
                f"{type(self).__name__} was not initialized properly;"
                " make sure that __set_name__ gets called"
            )

        del obj._element.attrib[self.attr]

    def __repr__(self) -> str:
        if self.attr is None:
            return f"<Uninitialized {type(self).__name__} - call __set_name__>"
        return (
            f"<{type(self).__name__} {self._qualname!r}"
            f" to {self.class_[0].alias}:{self.class_[1]}"
            f" on {self.attr!r}>"
        )

    def insert(
        self,
        elmlist: _obj.ElementListCouplingMixin,
        index: int,
        value: T_co | NewObject,
        *,
        bounds: tuple[_obj.ClassName, ...] = (),
    ) -> T_co:
        if isinstance(value, NewObject):
            raise TypeError(f"Cannot create new objects on {self}")
        if value._model is not elmlist._parent._model:
            raise ValueError("Cannot insert elements from different models")
        for b in bounds:
            bcls = elmlist._model.resolve_class(b)
            if not isinstance(value, bcls):
                raise InvalidModificationError(
                    f"Cannot insert into {self._qualname}:"
                    f" Objects must be instances of {b[0].alias}:{b[1]},"
                    f" not {type(value)}"
                )

        objs = [*elmlist[:index], value, *elmlist[index:]]
        self.__set_links(elmlist._parent, objs)
        return t.cast(T_co, value)

    def delete(
        self, elmlist: _obj.ElementListCouplingMixin, obj: _obj.ModelObject
    ) -> None:
        objs = [i for i in elmlist if i != obj]
        self.__set_links(elmlist._parent, objs)

    def __set_links(
        self, obj: _obj.ModelObject, values: cabc.Iterable[T_co]
    ) -> None:
        if self.attr is None:
            raise RuntimeError(
                f"{type(self).__name__} was not initialized properly;"
                " make sure that __set_name__ gets called"
            )

        class_ = obj._model.resolve_class(self.class_)
        parts: list[str] = []
        for value in values:
            if not isinstance(value, class_):
                raise InvalidModificationError(
                    f"Cannot insert into {self._qualname}:"
                    " Objects must be instances of"
                    f" {self.class_[0].alias}:{self.class_[1]},"
                    f" not {type(value)!r}"
                )
            if value._model is not obj._model:
                raise ValueError(
                    "Cannot insert elements from different models"
                )
            link = obj._model._loader.create_link(obj._element, value._element)
            parts.append(link)
        obj._element.set(self.attr, " ".join(parts))

    @contextlib.contextmanager
    def purge_references(
        self, obj: _obj.ModelObject, target: _obj.ModelObject
    ) -> cabc.Generator[None, None, None]:
        if self.attr is None:
            raise RuntimeError(
                f"{type(self).__name__} was not initialized properly;"
                " make sure that __set_name__ gets called"
            )

        yield

        try:
            elt = obj._element
            links = obj._model._loader.follow_links(
                elt, elt.get(self.attr, ""), ignore_broken=True
            )
            remaining_links = [
                link for link in links if link is not target._element
            ]
            self.__set_links(
                obj, _obj.ElementList(obj._model, remaining_links)
            )
        except Exception:
            LOGGER.exception("Cannot write new list of targets")

    def _resolve_super_attributes(
        self, super_acc: Accessor[t.Any] | None
    ) -> None:
        assert isinstance(super_acc, Association | None)

        super()._resolve_super_attributes(super_acc)

        if self.attr is not None:
            return

        if super_acc is None:
            raise TypeError(
                f"Cannot inherit {type(self).__name__} configuration:"
                f" No super class of {self.__objclass__.__name__}"
                f" defines {self.__name__}"
            )

        assert isinstance(super_acc, Association)
        self.attr = super_acc.attr


@deprecated(
    "PhysicalLinkEndsAccessor is deprecated,"
    " use Association(..., fixed_length=2) instead"
)
class PhysicalLinkEndsAccessor(Association[T_co]):
    def __init__(
        self,
        class_: type[T_co] | None | _obj.UnresolvedClassName,
        attr: str,
        *,
        aslist: t.Any = _NOT_SPECIFIED,
        mapkey: str | None = None,
        mapvalue: str | None = None,
    ) -> None:
        super().__init__(
            class_,
            attr,
            aslist=aslist,
            mapkey=mapkey,
            mapvalue=mapvalue,
            fixed_length=2,
        )


class IndexAccessor(Accessor["_obj.ElementList[T_co]"], t.Generic[T_co]):
    """Access a specific index in an ElementList of a fixed size."""

    __slots__ = ("index", "wrapped")

    def __init__(self, wrapped: str, index: int) -> None:
        super().__init__()
        self.index = index
        self.wrapped = wrapped

    @t.overload
    def __get__(self, obj: None, objtype: type[t.Any]) -> te.Self: ...
    @t.overload
    def __get__(
        self, obj: _obj.ModelObject, objtype: type[t.Any] | None = None
    ) -> _obj.ElementList[T_co]: ...
    def __get__(
        self,
        obj: _obj.ModelObject | None,
        objtype: type[t.Any] | None = None,
    ) -> te.Self | T_co | _obj.ElementList[T_co]:
        if obj is None:
            return self
        container = getattr(obj, self.wrapped)
        if not isinstance(container, _obj.ElementList):
            raise RuntimeError(
                f"Cannot get {self._qualname}: {self.wrapped} is not a list"
            )
        if len(container) <= self.index:
            raise RuntimeError(
                f"Broken XML: Expected at least {self.index + 1} elements,"
                f" found {len(container)}"
            )
        return container[self.index]

    def __set__(self, obj: _obj.ModelObject, value: t.Any) -> None:
        container = getattr(obj, self.wrapped)
        if not isinstance(container, _obj.ElementListCouplingMixin):
            raise TypeError(
                f"Cannot set {self._qualname}:"
                f" {self.wrapped} is not a coupled list"
            )
        if len(container) < self.index:
            raise RuntimeError(
                f"Broken XML: Expected at least {self.index + 1} elements,"
                f" found {len(container)}"
            )
        container[self.index] = value

    def __repr__(self) -> str:
        wrapped = repr(self.wrapped).replace(" " + repr(self._qualname), "")
        return (
            f"<{type(self).__name__} {self._qualname!r},"
            f" index {self.index} of {wrapped}>"
        )


class AlternateAccessor(Accessor[T_co]):
    """Provides access to an "alternate" form of the object."""

    __slots__ = ("class_",)

    def __init__(self, class_: type[T_co]):
        super().__init__()
        self.class_ = class_

    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:  # pragma: no cover
            return self

        if self.class_ is _obj.ModelElement:
            return _obj.wrap_xml(obj._model, obj._element)

        alt = self.class_.__new__(self.class_)
        alt._model = obj._model  # type: ignore[misc]
        alt._element = obj._element  # type: ignore[misc]
        return alt

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} {self._qualname!r} for {self.class_!r}>"
        )


class ParentAccessor(Accessor["_obj.ModelObject"]):
    """Accesses the parent XML element."""

    __slots__ = ()

    def __init__(self, class_: type[T_co] | None = None):
        del class_
        super().__init__()

    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:  # pragma: no cover
            return self

        parent = next(obj._model._loader.iterancestors(obj._element), None)
        if parent is None:
            objrepr = getattr(obj, "_short_repr_", obj.__repr__)()
            raise AttributeError(f"Object {objrepr} is orphaned")
        return _obj.wrap_xml(obj._model, parent)


@deprecated("AttributeMatcherAccessor is deprecated, use Filter instead")
class AttributeMatcherAccessor(DirectProxyAccessor[T_co]):
    __slots__ = (
        "_AttributeMatcherAccessor__aslist",
        "attributes",
    )

    def __init__(
        self,
        class_: type[T_co],
        xtypes: (
            str | type[T_co] | cabc.Iterable[str | type[T_co]] | None
        ) = None,
        *,
        aslist: type[_obj.ElementList] | None = None,
        attributes: dict[str, t.Any],
        **kwargs,
    ) -> None:
        super().__init__(
            class_, xtypes, aslist=_obj.MixedElementList, **kwargs
        )
        self.__aslist = aslist
        self.attributes = attributes

    def __get__(self, obj, objtype=None):
        if obj is None:  # pragma: no cover
            return self

        elements = super().__get__(obj, objtype)
        matches = []
        assert isinstance(elements, cabc.Iterable)
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

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} {self._qualname!r},"
            f" matching {self.attributes!r} on {self.class_.__name__!r}>"
        )


class _Specification(t.MutableMapping[str, str]):
    __capella_namespace__: t.ClassVar[_obj.Namespace]
    __capella_abstract__: t.ClassVar[bool] = True

    _aliases = types.MappingProxyType({"LinkedText": "capella:linkedText"})
    _linked_text = frozenset({"capella:linkedText"})
    _model: capellambse.MelodyModel
    _element: etree._Element

    def __init__(
        self, model: capellambse.MelodyModel, elm: etree._Element
    ) -> None:
        self._model = model
        self._element = elm

    def __delitem__(self, k: str) -> None:
        k = self._aliases.get(k, k)
        i, lang_elem = self._index_of(k)
        body_elem = self._body_at(k, i)
        self._element.remove(lang_elem)
        self._element.remove(body_elem)

    def __getitem__(self, k: str) -> str:
        k = self._aliases.get(k, k)
        i, _ = self._index_of(k)
        v = self._body_at(k, i).text or ""
        if k in self._linked_text:
            v = helpers.unescape_linked_text(self._model._loader, v)
        return v

    def __iter__(self) -> cabc.Iterator[str]:
        for i in self._element.iterchildren("languages"):
            yield i.text or ""

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def __setitem__(self, k: str, v: str) -> None:
        k = self._aliases.get(k, k)
        if k in self._linked_text:
            v = helpers.escape_linked_text(self._model._loader, v)
        try:
            i, lang = self._index_of(k)
        except KeyError:
            self._element.append(body := self._element.makeelement("bodies"))
            self._element.append(
                lang := self._element.makeelement("languages")
            )
            body.text = v
            lang.text = k
        else:
            body = self._body_at(k, i)
            body.text = v

    def _index_of(self, k: str) -> tuple[int, etree._Element]:
        for i, elm in enumerate(self._element.iterchildren("languages")):
            if elm.text == k:
                return i, elm

        raise KeyError(k)

    def _body_at(self, k: str, i: int) -> etree._Element:
        try:
            return next(
                itertools.islice(
                    self._element.iterchildren("bodies"), i, i + 1
                )
            )
        except StopIteration:
            raise KeyError(k) from None

    def __html__(self) -> str:
        return markupsafe.escape(self.__str__())

    def __str__(self) -> str:  # pragma: no cover
        return next(iter(self.values()))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{type(self).__name__} at 0x{id(self):016X} {list(self)!r}>"

    @classmethod
    def from_model(cls, _1: capellambse.MelodyModel, _2: t.Any) -> te.Self:
        """Specifications can not be instantiated."""
        raise RuntimeError("Cannot create a specification from a model")


class SpecificationAccessor(Accessor[_Specification]):
    """Provides access to linked specifications."""

    __slots__ = ()

    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:  # pragma: no cover
            return self

        try:
            spec_elm = next(obj._element.iterchildren("ownedSpecification"))
        except StopIteration:
            raise AttributeError("No specification found") from None

        return _Specification(obj._model, spec_elm)


class Backref(Accessor["_obj.ElementList[T_co]"], t.Generic[T_co]):
    """Searches for references to the current element elsewhere."""

    __slots__ = ("attrs", "target_classes")

    attrs: tuple[operator.attrgetter, ...]
    class_: _obj.ClassName
    list_extra_args: cabc.Mapping[str, t.Any]

    def __init__(
        self,
        class_: (
            type[T_co]
            | tuple[type[_obj.ModelObject], ...]
            | _obj.UnresolvedClassName
        ),
        *attrs: str,
        aslist: t.Any = _NOT_SPECIFIED,
        mapkey: str | None = None,
        mapvalue: str | None = None,
        legacy_by_type: bool = False,
    ) -> None:
        """Define a back-reference.

        This relation is not actually stored in the model, but nevertheless
        provides a useful shortcut to other related elements.

        Parameters
        ----------
        class_
            The type of class to search for references on.
        attrs
            The attributes of the target classes to search through.
        aslist
            If None, only a single element must match, which will be
            returned directly. If not None, must be a subclass of
            :class:`~capellambse.model.ElementList`,
            which will be used to return a list of all matched objects.
        mapkey
            Specify the attribute to look up when the returned list is
            indexed with a str. If not specified, str indexing is not
            possible.
        mapvalue
            If specified, return this attribute of the found object when
            using str indices into the returned list. If not specified,
            the found object itself is returned.
        legacy_by_type
            When filtering with 'by_X' etc., make 'type' an alias for
            '__class__'. This was the behavior when using the MixedElementList
            for the *aslist* parameter. Note that this parameter should itself
            be considered deprecated, and only exists to facilitate the
            transition to 'by_class'.
        """
        if aslist is not _NOT_SPECIFIED:
            warnings.warn(
                "The aslist argument is deprecated and will be removed soon",
                DeprecationWarning,
                stacklevel=2,
            )
            if isinstance(aslist, type) and issubclass(
                aslist, _obj.MixedElementList
            ):
                legacy_by_type = True

        super().__init__()

        if class_ == ():
            class_ = (_obj.NS, "ModelElement")

        if (
            isinstance(class_, tuple)
            and len(class_) == 2
            and isinstance(class_[0], _obj.Namespace | str)
            and isinstance(class_[1], str)
        ):
            self.class_ = _obj.resolve_class_name(class_)
        elif isinstance(class_, cabc.Sequence):
            warnings.warn(
                (
                    "Multiple classes to Backref are deprecated,"
                    " use a common abstract base class instead"
                ),
                DeprecationWarning,
                stacklevel=2,
            )
            self.class_ = (_obj.NS, "ModelElement")
        else:
            warnings.warn(
                (
                    "Raw classes to Backref are deprecated,"
                    " use a (Namespace, 'ClassName') tuple instead"
                ),
                DeprecationWarning,
                stacklevel=2,
            )
            if not hasattr(class_, "__capella_namespace__"):
                raise TypeError(f"Class does not have a namespace: {class_!r}")
            self.class_ = (class_.__capella_namespace__, class_.__name__)
        self.attrs = tuple(operator.attrgetter(i) for i in attrs)
        self.list_extra_args = {
            "legacy_by_type": legacy_by_type,
            "mapkey": mapkey,
            "mapvalue": mapvalue,
        }

    @t.overload
    def __get__(self, obj: None, objtype: type[t.Any]) -> te.Self: ...
    @t.overload
    def __get__(
        self, obj: _obj.ModelObject, objtype: type[t.Any] | None = ...
    ) -> _obj.ElementList[T_co]: ...
    def __get__(
        self,
        obj: _obj.ModelObject | None,
        objtype: type[t.Any] | None = None,
    ) -> te.Self | _obj.ElementList[T_co]:
        del objtype
        if obj is None:  # pragma: no cover
            return self

        matches: list[etree._Element] = []
        for candidate in obj._model.search(self.class_):
            for attr in self.attrs:
                try:
                    value = attr(candidate)
                except AttributeError:
                    continue
                if (isinstance(value, _obj.ElementList) and obj in value) or (
                    isinstance(value, _obj.ModelElement) and obj == value
                ):
                    matches.append(candidate._element)
                    break
        return _obj.ElementList(
            obj._model, matches, None, **self.list_extra_args
        )

    def __repr__(self) -> str:
        try:
            attrs: cabc.Sequence[t.Any] = [
                i for (_, (i,), *_) in t.cast(t.Any, self.attrs.__reduce__())
            ]
        except Exception:
            attrs = self.attrs
        return (
            f"<{type(self).__name__} {self._qualname!r}"
            f" to {self.class_[0].alias}:{self.class_[1]}"
            f" through {attrs}>"
        )


class Filter(Accessor["_obj.ElementList[T_co]"], t.Generic[T_co]):
    """Provides access to a filtered subset of another attribute."""

    __slots__ = ("attr", "class_", "wrapped")

    attr: str
    class_: _obj.ClassName

    def __init__(
        self,
        attr: str,
        class_: _obj.UnresolvedClassName,
        /,
        *,
        legacy_by_type: bool = False,
    ) -> None:
        self.attr = attr
        self.class_ = _obj.resolve_class_name(class_)
        self.list_type = make_coupled_list_type(self)
        self.wrapped: Relationship[T_co] | None = None
        self.list_extra_args = {
            "legacy_by_type": legacy_by_type,
        }

    @t.overload
    def __get__(self, obj: None, objtype: type[t.Any]) -> te.Self: ...
    @t.overload
    def __get__(
        self, obj: _obj.ModelObject, objtype: type[t.Any] | None = ...
    ) -> _obj.ElementList[T_co]: ...
    def __get__(
        self,
        obj: _obj.ModelObject | None,
        objtype: type[t.Any] | None = None,
    ) -> te.Self | _obj.ElementList[T_co]:
        if obj is None:  # pragma: no cover
            return self

        if self.wrapped is None:
            raise RuntimeError(
                f"{type(self).__name__} was not initialized properly;"
                " make sure that __set_name__ gets called"
            )

        cls = obj._model.resolve_class(self.class_)
        parent_elts = self.wrapped.__get__(obj, objtype)
        if not isinstance(parent_elts, _obj.ElementList):
            raise TypeError(
                f"Parent accessor {self.wrapped!r}"
                f" did not return an ElementList: {parent_elts!r}"
            )
        filtered_elts = [
            i
            for i in parent_elts._elements
            if issubclass(obj._model.resolve_class(i), cls)
        ]

        return self.list_type(
            obj._model,
            filtered_elts,
            parent=obj,
            **self.list_extra_args,
        )

    def __set__(
        self,
        obj: _obj.ModelObject,
        value: cabc.Iterable[T_co | NewObject],
    ) -> None:
        if self.wrapped is None:
            raise RuntimeError(
                f"{type(self).__name__} was not initialized properly;"
                " make sure that __set_name__ gets called"
            )

        elmlist = self.__get__(obj, type(obj))
        assert isinstance(elmlist, _obj.ElementListCouplingMixin)
        i = -1
        for i, v in enumerate(value):
            self.insert(elmlist, i, v)
        for o in elmlist[i + 1 :]:
            self.delete(elmlist, o)

    def __delete__(self, obj: _obj.ModelObject) -> None:
        if self.wrapped is None:
            raise RuntimeError(
                f"{type(self).__name__} was not initialized properly;"
                " make sure that __set_name__ gets called"
            )

        if not isinstance(self.wrapped, Relationship):
            raise AttributeError(f"Cannot delete from {self._qualname}")

        children = self.__get__(obj, type(obj))
        assert isinstance(children, _obj.ElementListCouplingMixin)
        children[:] = ()

    def __set_name__(self, owner: type[t.Any], name: str) -> None:
        wrapped = getattr(owner, self.attr)
        if not isinstance(wrapped, Relationship):
            raise TypeError(
                "Can only filter on Relationship accessors, not"
                f" {type(wrapped).__name__}"
            )
        self.wrapped = wrapped

        super().__set_name__(owner, name)

    def __repr__(self) -> str:
        if self.wrapped is None:
            return f"<Uninitialized {type(self).__name__} - call __set_name__>"
        wrapped = repr(self.wrapped).replace(" " + repr(self._qualname), "")
        return (
            f"<{type(self).__name__} {self._qualname!r},"
            f" using {self.class_[0].alias}:{self.class_[1]}"
            f" on {wrapped}>"
        )

    def insert(
        self,
        elmlist: _obj.ElementListCouplingMixin,
        index: int,
        value: T_co | NewObject,
        *,
        bounds: tuple[_obj.ClassName, ...] = (),
    ) -> T_co:
        if self.wrapped is None:
            raise RuntimeError(
                f"{type(self).__name__} was not initialized properly;"
                " make sure that __set_name__ gets called"
            )

        unfiltered = self.wrapped.__get__(
            elmlist._parent, type(elmlist._parent)
        )
        assert isinstance(unfiltered, _obj.ElementListCouplingMixin)
        if index < 0:
            index += len(elmlist)

        if index >= len(elmlist):
            real_index = len(unfiltered)
        else:
            real_index = unfiltered.index(elmlist[index])

        return self.wrapped.insert(
            unfiltered, real_index, value, bounds=bounds + (self.class_,)
        )

    def delete(
        self, elmlist: _obj.ElementListCouplingMixin, obj: _obj.ModelObject
    ) -> None:
        if self.wrapped is None:
            raise RuntimeError(
                f"{type(self).__name__} was not initialized properly;"
                " make sure that __set_name__ gets called"
            )

        if not isinstance(self.wrapped, Relationship):
            raise AttributeError(f"Cannot delete from {self._qualname}")

        unfiltered = self.wrapped.__get__(
            elmlist._parent, type(elmlist._parent)
        )
        assert isinstance(unfiltered, _obj.ElementListCouplingMixin)
        self.wrapped.delete(unfiltered, obj)

    @contextlib.contextmanager
    def purge_references(
        self, obj: _obj.ModelObject, target: _obj.ModelObject
    ) -> cabc.Generator[None, None, None]:
        if self.wrapped is None:
            raise RuntimeError(
                f"{type(self).__name__} was not initialized properly;"
                " make sure that __set_name__ gets called"
            )

        assert isinstance(self.wrapped, Relationship)
        with self.wrapped.purge_references(obj, target):
            yield


@deprecated(
    "TypecastAccessor is deprecated,"
    " use Filter to perform filtering"
    " or Alias to create an unfiltered Alias"
)
class TypecastAccessor(WritableAccessor[T_co], PhysicalAccessor[T_co]):
    """Changes the static type of the value of another accessor.

    This is useful for when a class has an attribute that is
    polymorphic, but the accessor should always return a specific
    subclass.

    At runtime, this Accessor mostly behaves like a simple alias
    (without performing any runtime type checks or conversions). When
    creating new objects, it will only allow to create objects of the
    specified type.
    """

    aslist: type[_obj.ElementListCouplingMixin] | None
    class_: type[T_co]

    def __init__(
        self,
        cls: type[T_co],
        attr: str,
        mapkey: str | None = None,
        mapvalue: str | None = None,
    ) -> None:
        super().__init__(
            cls,
            (),
            aslist=_obj.ElementList,
            mapkey=mapkey,
            mapvalue=mapvalue,
        )
        self.attr = attr

    @t.overload
    def __get__(self, obj: None, objtype: type[t.Any]) -> te.Self: ...
    @t.overload
    def __get__(
        self, obj: _obj.ModelObject, objtype: type[t.Any] | None = None
    ) -> _obj.ElementList[T_co]: ...
    def __get__(
        self,
        obj: _obj.ModelObject | None,
        objtype: type[t.Any] | None = None,
    ) -> te.Self | _obj.ElementList[T_co]:
        del objtype
        if obj is None:
            return self

        return getattr(obj, self.attr)

    def __set__(
        self,
        obj: _obj.ModelObject,
        value: T_co | NewObject | cabc.Iterable[T_co | NewObject],
    ) -> None:
        if isinstance(value, list | _obj.ElementList | tuple):
            pass
        elif isinstance(value, cabc.Iterable):
            value = list(value)
        else:
            raise TypeError(
                f"Expected list for {self._qualname!r},"
                f" got {type(value).__name__}"
            )

        if any(isinstance(i, NewObject) for i in value):
            raise NotImplementedError(f"Cannot create objects on {self}")

        if not all(isinstance(i, self.class_) for i in value):
            orepr = getattr(obj, "_short_repr_", obj.__repr__)()
            raise TypeError(
                f"Expected all objects in {self._qualname!r}"
                f" to be of type {self.class_.__name__!r},"
                f" but found a {type(value).__name__!r}"
                f" in {orepr}"
            )
        setattr(obj, self.attr, value)

    def __delete__(self, obj):
        delattr(obj, self.attr)

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} {self._qualname!r}"
            f" to {self.class_!r} from {self.attr!r}>"
        )

    def create(
        self,
        elmlist: _obj.ElementListCouplingMixin,
        typehint: str | None = None,
        /,
        **kw: t.Any,
    ) -> T_co:
        if typehint:
            raise TypeError(f"{self._qualname} does not support type hints")
        acc: WritableAccessor = getattr(self.class_, self.attr)
        obj = acc.create(elmlist, build_xtype(self.class_), **kw)  # type: ignore[deprecated]
        assert isinstance(obj, self.class_)
        return obj

    def insert(
        self,
        elmlist: _obj.ElementListCouplingMixin,
        index: int,
        value: _obj.ModelObject | NewObject,
    ) -> None:
        if isinstance(value, NewObject):
            raise NotImplementedError(f"Cannot create objects on {self}")
        if not isinstance(value, self.class_):
            raise TypeError(
                f"Expected {self.class_.__name__}, got {type(value).__name__}"
            )
        acc: WritableAccessor = getattr(self.class_, self.attr)
        acc.insert(elmlist, index, value)

    def delete(
        self,
        elmlist: _obj.ElementListCouplingMixin,
        obj: _obj.ModelObject,
    ) -> None:
        acc: WritableAccessor = getattr(self.class_, self.attr)
        acc.delete(elmlist, obj)

    @contextlib.contextmanager
    def purge_references(
        self, obj: _obj.ModelObject, target: _obj.ModelObject
    ) -> cabc.Iterator[None]:
        acc: WritableAccessor = getattr(self.class_, self.attr)
        with acc.purge_references(obj, target):
            yield


class Containment(Relationship[T_co]):
    __slots__ = ("classes", "role_tag")

    aslist: type[_obj.ElementListCouplingMixin]
    alternate: type[_obj.ModelObject] | None

    @t.overload
    @deprecated(
        "Raw classes, xsi:type strings and 'aslist' are deprecated,"
        " migrate to (Namespace, 'ClassName') tuples and drop aslist=..."
    )
    def __init__(
        self,
        role_tag: str,
        classes: type[T_co] | cabc.Iterable[type[_obj.ModelObject]] = ...,
        /,
        *,
        aslist: type[_obj.ElementList[T_co]] | None = ...,
        mapkey: str | None = ...,
        mapvalue: str | None = ...,
        alternate: type[_obj.ModelObject] | None = ...,
        single_attr: str | None = ...,
        fixed_length: int = ...,
        legacy_by_type: bool = ...,
        type_hint_map: (
            cabc.Mapping[str, _obj.UnresolvedClassName] | None
        ) = None,
    ) -> None: ...
    @t.overload
    def __init__(
        self,
        role_tag: str,
        class_: _obj.UnresolvedClassName,
        /,
        *,
        mapkey: str | None = ...,
        mapvalue: str | None = ...,
        alternate: type[_obj.ModelObject] | None = ...,
        single_attr: str | None = ...,
        fixed_length: int = ...,
        legacy_by_type: bool = ...,
        type_hint_map: (
            cabc.Mapping[str, _obj.UnresolvedClassName] | None
        ) = None,
    ) -> None: ...
    def __init__(
        self,
        role_tag: str,
        class_: (
            type[T_co]
            | cabc.Iterable[type[_obj.ModelObject]]
            | _obj.UnresolvedClassName
        ) = (),
        /,
        *,
        aslist: t.Any = _NOT_SPECIFIED,
        mapkey: str | None = None,
        mapvalue: str | None = None,
        alternate: type[_obj.ModelObject] | None = None,
        single_attr: str | None = None,
        fixed_length: int = 0,
        legacy_by_type: bool = False,
        type_hint_map: (
            cabc.Mapping[str, _obj.UnresolvedClassName] | None
        ) = None,
    ) -> None:
        if aslist is not _NOT_SPECIFIED:
            warnings.warn(
                "The aslist argument is deprecated and will be removed soon",
                DeprecationWarning,
                stacklevel=2,
            )

        super().__init__(
            mapkey=mapkey,
            mapvalue=mapvalue,
            fixed_length=fixed_length,
            single_attr=single_attr,
            legacy_by_type=legacy_by_type,
        )
        self.role_tag = role_tag
        self.alternate = alternate
        self.type_hint_map = type_hint_map or {}

        if (
            isinstance(class_, tuple)
            and len(class_) == 2
            and isinstance(class_[0], _obj.Namespace | str)
            and isinstance(class_[1], str)
        ):
            self.class_ = _obj.resolve_class_name(class_)
        elif isinstance(class_, cabc.Iterable) and not isinstance(class_, str):
            warnings.warn(
                (
                    "Multiple classes for Containment are deprecated,"
                    " use a common abstract base class instead"
                ),
                DeprecationWarning,
                stacklevel=2,
            )
            self.class_ = (_obj.NS, "ModelElement")
        elif isinstance(class_, type) and issubclass(
            class_, _obj.ModelElement
        ):
            warnings.warn(
                (
                    "Raw classes in Containment are deprecated,"
                    " use a (Namespace, 'ClassName') tuple instead"
                ),
                DeprecationWarning,
                stacklevel=2,
            )
        else:
            raise TypeError(
                f"Invalid class_ specified, expected a 2-tuple: {class_!r}"
            )

    @t.overload
    def __get__(self, obj: None, objtype: type[t.Any]) -> te.Self: ...
    @t.overload
    def __get__(
        self, obj: _obj.ModelObject, objtype: type[t.Any] | None = ...
    ) -> _obj.ElementList[T_co]: ...
    def __get__(
        self,
        obj: _obj.ModelObject | None,
        objtype: type[t.Any] | None = None,
    ) -> te.Self | _obj.ElementList[T_co]:
        del objtype
        if obj is None:  # pragma: no cover
            return self

        if self.role_tag is None:
            raise RuntimeError(
                f"{type(self).__name__} was not initialized properly;"
                " make sure that __set_name__ gets called"
            )

        loader = obj._model._loader
        elts = list(loader.iterchildren(obj._element, self.role_tag))
        return self.list_type(
            obj._model,
            elts,
            self.alternate,
            parent=obj,
            **self.list_extra_args,
        )

    def __set__(
        self,
        obj: _obj.ModelObject,
        value: cabc.Iterable[str | T_co | NewObject],
    ) -> None:
        if isinstance(value, str) or not isinstance(value, cabc.Iterable):
            warnings.warn(
                (
                    "Assigning a single value onto Containment is deprecated."
                    f" If {self._qualname!r} is supposed to use single values,"
                    " wrap it in a 'm.Single()'."
                    " Otherwise, update your code to assign a list instead."
                ),
                DeprecationWarning,
                stacklevel=2,
            )
            value = (value,)

        current = self.__get__(obj)
        previous = {id(i): i for i in current}

        for i in value:
            current.append(i)
            if hasattr(i, "_element"):
                previous.pop(id(i._element), None)
        for i in previous.values():
            current.remove(i)

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} {self._qualname!r}"
            f" of {self.class_[0].alias}:{self.class_[1]}"
            f" in {self.role_tag!r}>"
        )

    def insert(
        self,
        elmlist: _obj.ElementListCouplingMixin,
        index: int,
        value: T_co | NewObject,
        *,
        bounds: tuple[_obj.ClassName, ...] = (),
    ) -> T_co:
        if self.role_tag is None:
            raise RuntimeError(
                f"{type(self).__name__} was not initialized properly;"
                " make sure that __set_name__ gets called"
            )

        if self.alternate is not None:
            raise NotImplementedError(
                "Cannot mutate lists with 'alternate' set"
            )

        if (
            isinstance(value, _obj.ModelObject)
            and value._model is not elmlist._model
        ):
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
            parent_index = len(elmlist._parent._element)

        if isinstance(value, NewObject):
            value = self._insert_create(
                elmlist._model, elmlist._parent, value, bounds=bounds
            )

        else:
            assert isinstance(value, _obj.ModelObject)
            value._element.tag = self.role_tag

        elmlist._parent._element.insert(parent_index, value._element)
        elmlist._model._loader.idcache_index(value._element)
        return value

    def delete(
        self,
        elmlist: _obj.ElementListCouplingMixin,
        obj: _obj.ModelObject,
    ) -> None:
        assert obj._model is elmlist._model
        model = obj._model
        all_elements = [
            *list(model._loader.iterdescendants_xt(obj._element)),
            obj._element,
        ]
        with contextlib.ExitStack() as stack:
            for elm in all_elements:
                if elm.get("id") is None:
                    continue

                obj = _obj.wrap_xml(model, elm)
                for ref, attr, _ in model.find_references(obj):
                    acc = getattr(type(ref), attr)
                    if acc is self or not isinstance(
                        acc, WritableAccessor | Relationship | Single
                    ):
                        continue
                    stack.enter_context(acc.purge_references(ref, obj))

            elm = obj._element
            parent = elm.getparent()
            assert parent is not None
            model._loader.idcache_remove(elm)
            parent.remove(elm)

    @contextlib.contextmanager
    def purge_references(
        self, obj: _obj.ModelObject, target: _obj.ModelObject
    ) -> cabc.Iterator[None]:
        del obj, target
        yield

    def _find_candidate_classes(
        self,
        model: capellambse.MelodyModel,
        *,
        bounds: tuple[_obj.ClassName, ...],
        hint: str,
    ) -> list[type[T_co]]:
        clsbounds = tuple(
            model.resolve_class(i) for i in bounds or ("ModelElement",)
        )
        subclasses = _find_all_subclasses(model.resolve_class(self.class_))
        classes = [
            i
            for i in subclasses
            if not i.__capella_abstract__ and issubclass(i, clsbounds)
        ]
        if not classes:
            basecls = model.resolve_class(self.class_)
            raise InvalidModificationError(
                f"No concrete subclass of {basecls!r}"
                f" satisfies all bounds: {clsbounds!r}"
            )

        if uclsname := self.type_hint_map.get(hint.lower()):
            cls = model.resolve_class(uclsname)
            if cls not in classes:
                raise InvalidModificationError(
                    f"Type hint {hint!r} maps to class {cls.__name__!r},"
                    f" which doesn't satisfy all bounds: {clsbounds!r}"
                )
            classes = [cls]

        elif hint:
            *_, clsname = hint.rsplit(":", 1)
            for i in classes:
                if i.__name__ == clsname:
                    LOGGER.debug(
                        "Found exact match for type hint %r: %r", hint, i
                    )
                    classes = [i]
                    break
            else:
                raise ValueError(f"Invalid type hint: {hint}")

        return t.cast(list[type[T_co]], classes)

    def _insert_create(
        self,
        model: capellambse.MelodyModel,
        parent: _obj.ModelObject,
        value: NewObject,
        *,
        bounds: tuple[_obj.ClassName, ...],
    ) -> T_co:
        classes = self._find_candidate_classes(
            model, bounds=bounds, hint=value._type_hint
        )
        attrs = dict(value._kw)
        uuid: str | None = attrs.pop("uuid", None)
        with model._loader.new_uuid(parent._element, want=uuid) as uuid:
            LOGGER.debug(
                "Trying to create object %r in %s with %d classes: %r",
                uuid,
                self._qualname,
                len(classes),
                classes,
            )
            for cls in classes:
                assert hasattr(cls, "__capella_namespace__")
                assert not cls.__capella_abstract__

                try:
                    return cls(
                        model,
                        parent._element,
                        self.role_tag,
                        uuid=uuid,
                        **attrs,
                    )
                except InvalidModificationError as err:
                    LOGGER.debug("%r rejected %r: %s", cls, uuid, err)

            arg_repr = ", ".join(
                f"{k!r}: {getattr(v, '_short_repr_', v.__repr__)()}"
                for k, v in value._kw.items()
            )
            raise InvalidModificationError(
                "Cannot construct model object with"
                + (
                    f" type hint {value._type_hint!r} and"
                    if value._type_hint
                    else ""
                )
                + f" arguments {{{arg_repr}}} in {self._qualname!r}"
            )

    def _resolve_super_attributes(
        self, super_acc: Accessor[t.Any] | None
    ) -> None:
        assert isinstance(super_acc, Containment | None)

        super()._resolve_super_attributes(super_acc)


def no_list(
    desc: Accessor,
    model: capellambse.MelodyModel,
    elems: cabc.Sequence[etree._Element],
    class_: type[T_co],
) -> _obj.ModelObject | None:
    """Return a single element or None instead of a list of elements.

    Parameters
    ----------
    desc
        The descriptor that called this function
    model
        The ``MelodyModel`` instance
    elems
        List of elements that was matched
    class_
        The ``ModelElement`` subclass to instantiate
    """
    del class_

    if not elems:  # pragma: no cover
        return None
    if len(elems) > 1:  # pragma: no cover
        raise RuntimeError(
            f"Expected 1 object for {desc._qualname}, got {len(elems)}"
        )
    return _obj.wrap_xml(model, elems[0])


def make_coupled_list_type(
    parent: Accessor[t.Any],
) -> type[_obj.ElementListCouplingMixin]:
    list_type: type[_obj.ElementListCouplingMixin] = type(
        "CoupledElementList",
        (_obj.ElementListCouplingMixin, _obj.ElementList),
        {},
    )
    list_type._accessor = parent
    list_type.__module__ = __name__
    return list_type


def _find_all_subclasses(cls: type[U]) -> dict[type[U], None]:
    classes = {cls: None}
    for scls in cls.__subclasses__():
        classes.update(_find_all_subclasses(scls))
    return classes


from . import _obj
from ._obj import Namespace  # noqa: F401 # needed for Sphinx

# HACK to make _Specification objects cooperate in the new world order
_Specification.__capella_namespace__ = _obj.NS
