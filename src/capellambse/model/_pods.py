# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

__all__ = [
    "BasePOD",
    "BoolPOD",
    "DatetimePOD",
    "EnumPOD",
    "FloatPOD",
    "HTMLStringPOD",
    "IntPOD",
    "MultiStringPOD",
    "StringPOD",
]

import abc
import collections.abc as cabc
import datetime
import enum
import itertools
import math
import os
import re
import typing as t

import markupsafe
import typing_extensions as te
from lxml import etree

from capellambse import helpers

from . import E, U

if t.TYPE_CHECKING:
    from . import _obj


class BasePOD(t.Generic[U]):
    """A plain-old-data descriptor."""

    __slots__ = (
        "__dict__",
        "__name__",
        "__objclass__",
        "attribute",
        "default",
        "writable",
    )

    NOT_OPTIONAL = object()

    def __init__(
        self,
        attribute: str,
        *,
        default: U,
        writable: bool,
    ) -> None:
        self.attribute = attribute
        self.writable = writable
        self.default = default

        self.__name__ = "(unknown)"
        self.__objclass__: type[t.Any] | None = None

    @property
    def _qualname(self) -> str:
        """Generate the qualified name of this descriptor."""
        if self.__objclass__ is None:
            return f"(unknown {type(self).__name__} - call __set_name__)"
        return f"{self.__objclass__.__name__}.{self.__name__}"

    @t.overload
    def __get__(self, obj: None, objtype: type) -> te.Self: ...
    @t.overload
    def __get__(self, obj: t.Any, objtype: type | None = None) -> U: ...
    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:
            return self

        data = obj._element.get(self.attribute)
        assert data is None or isinstance(data, str)
        if data is None:
            return self.default
        return self._from_xml(obj, data)

    def __set__(self, obj: t.Any, value: U | None) -> None:
        if not self.writable and self.attribute in obj._element.attrib:
            raise TypeError(f"{self._qualname} is not writable")

        if value is not None and value != self.default:
            data = self._to_xml(obj, value)
        else:
            data = None

        if data is None:
            obj._element.attrib.pop(self.attribute, None)
        else:
            obj._element.attrib[self.attribute] = data

    def __delete__(self, obj: t.Any) -> None:
        self.__set__(obj, None)

    def __set_name__(self, owner: type[t.Any], name: str) -> None:
        if self.__objclass__ is not None:
            raise RuntimeError(
                f"__set_name__ called twice on {self._qualname}"
            )
        self.__name__ = name
        self.__objclass__ = owner

    @abc.abstractmethod
    def _from_xml(self, obj: _obj.ModelElement, value: str, /) -> U: ...
    @abc.abstractmethod
    def _to_xml(self, obj: _obj.ModelElement, value: U, /) -> str | None: ...


class StringPOD(BasePOD[str]):
    """A POD containing arbitrary string data."""

    __slots__ = ()

    def __init__(self, attribute: str, /, *, writable: bool = True) -> None:
        """Create a StringPOD.

        Parameters
        ----------
        attribute
            The name of the attribute on the XML element.
        writable
            Whether to allow changing the value at runtime.
        """
        super().__init__(attribute, default="", writable=writable)

    def _from_xml(self, obj: _obj.ModelElement, value: str, /) -> str:
        del obj
        return value

    def _to_xml(self, obj: _obj.ModelElement, value: str, /) -> str:
        del obj
        return value


class HTMLStringPOD(BasePOD[markupsafe.Markup]):
    """A POD containing a string with HTML inside."""

    __slots__ = ()

    def __init__(self, attribute: str, /, *, writable: bool = True) -> None:
        """Create an HTMLStringPOD.

        Parameters
        ----------
        attribute
            The name of the attribute on the XML element.
        writable
            Whether to allow changing the value at runtime.
        """
        super().__init__(
            attribute,
            default=markupsafe.Markup(""),
            writable=writable,
        )

    def _from_xml(
        self, obj: _obj.ModelElement, value: str, /
    ) -> markupsafe.Markup:
        if os.getenv("CAPELLAMBSE_XHTML") == "1":
            value = helpers.repair_html(value)
        value = helpers.embed_images(value, obj._model.resources)
        return markupsafe.Markup(value)

    def _to_xml(
        self, obj: _obj.ModelElement, value: markupsafe.Markup, /
    ) -> str:
        value = helpers.repair_html(value)
        return helpers.unembed_images(value, obj._model.resources)


class BoolPOD(BasePOD[bool]):
    """A POD containing a boolean."""

    __slots__ = ()

    def __init__(self, attribute: str, /) -> None:
        """Create a BoolPOD.

        Parameters
        ----------
        attribute
            The name of the attribute on the XML element.
        """
        super().__init__(attribute, default=False, writable=True)

    def _from_xml(self, obj: _obj.ModelElement, value: str, /) -> bool:
        del obj
        return value == "true"

    def _to_xml(self, obj: _obj.ModelElement, value: bool, /) -> str:
        del obj
        assert isinstance(value, bool)
        return ("false", "true")[value]


class IntPOD(BasePOD[int]):
    """A POD containing an integer number."""

    __slots__ = ()

    def __init__(self, attribute: str, /, *, writable: bool = True) -> None:
        """Create an IntPOD.

        Parameters
        ----------
        attribute
            The name of the attribute on the XML element.
        writable
            Whether to allow changing the value at runtime.
        """
        super().__init__(attribute, default=0, writable=writable)

    def _from_xml(self, obj: _obj.ModelElement, data: str, /) -> int:
        del obj
        return int(data)

    def _to_xml(self, obj: _obj.ModelElement, value: int, /) -> str | None:
        del obj
        if not isinstance(value, int):
            raise TypeError(
                f"{self._qualname} only accepts int,"
                f" not {type(value).__name__}"
            )
        return str(value)


class FloatPOD(BasePOD[float]):
    """A POD containing a floating-point number.

    In Capella's Java land, these are often called "real numbers".
    """

    __slots__ = ()

    def __init__(self, attribute: str, /, *, writable: bool = True) -> None:
        """Create an IntPOD.

        Parameters
        ----------
        attribute
            The name of the attribute on the XML element.
        writable
            Whether to allow changing the value at runtime.
        """
        super().__init__(attribute, default=0.0, writable=writable)

    def _from_xml(self, obj: _obj.ModelElement, data: str, /) -> float:
        del obj
        return float(data)

    def _to_xml(self, obj: _obj.ModelElement, value: float, /) -> str | None:
        del obj
        if isinstance(value, int):
            value = float(value)
        elif not isinstance(value, float):
            raise TypeError(
                f"{self._qualname} only accepts float or int,"
                f" not {type(value).__name__}"
            )
        assert isinstance(value, float)

        if math.isnan(value):
            raise ValueError("Cannot represent NaN")
        if value == math.inf:
            return "*"
        if value == -math.inf:
            raise ValueError("Cannot represent negative infinity")
        return str(value)


class DatetimePOD(BasePOD[datetime.datetime | None]):
    """A POD containing a timestamp.

    The value stored in the XML will be formatted as required by
    Capella. This format is the ISO8601 format with millisecond
    precision, but no ``:`` in the time zone specification.
    """

    __slots__ = ()
    re_set = re.compile(r"(?<=[+-]\d\d):(?=\d\d$)")
    re_get = re.compile(r"(?<=[+-]\d\d)(?=\d\d$)")

    def __init__(self, attribute: str, /, *, writable: bool = True) -> None:
        """Create a DatetimePOD.

        Parameters
        ----------
        attribute
            The name of the attribute on the XML element.
        writable
            Whether to allow changing the value at runtime.
        """
        super().__init__(attribute, default=None, writable=writable)

    def _from_xml(
        self, obj: _obj.ModelElement, value: str, /
    ) -> datetime.datetime:
        del obj
        formatted = self.re_get.sub(":", value)
        return datetime.datetime.fromisoformat(formatted)

    def _to_xml(
        self, obj: _obj.ModelElement, value: datetime.datetime | None, /
    ) -> str:
        del obj
        assert value is not None
        if not isinstance(value, datetime.datetime):
            raise TypeError(f"Expected datetime instance, not {value!r}")
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            value = value.astimezone()

        formatted = value.isoformat("T", "milliseconds")
        return self.re_set.sub("", formatted)


class EnumPOD(BasePOD[E]):
    """A POD that can have one of a pretermined set of values.

    This works in much the same way as the StringPOD, except that the
    returned and consumed values are not simple strings, but members of
    the Enum that was passed into the constructor.

    When assigning, this property also accepts the string name of one of
    the enum members. In either case, the corresponding enum member's
    value will be placed in the underlying XML element.

    The *default* constructor argument determines which member will be
    used if the attribute is missing from the XML. If no *default* is
    passed exlicitly, the first declared enum member will be used.
    """

    __slots__ = ("enumcls",)

    def __init__(
        self,
        attribute: str,
        enumcls: type[E],
        /,
        default: E | str | None = None,
        *,
        writable: bool = True,
    ) -> None:
        """Create an EnumPOD.

        Parameters
        ----------
        attribute
            The name of the attribute on the XML element.
        enumcls
            The :class:`enum.Enum` subclass to use. The class' members'
            values are used as the possible values for the XML
            attribute.
        default
            The default value to return if the attribute is not present
            in the XML. If not passed or None, the first member of the
            given *enumcls* will be used.
        writable
            Whether to allow changing the value at runtime.
        """
        if not (isinstance(enumcls, type) and issubclass(enumcls, enum.Enum)):
            raise TypeError(
                f"enumcls must be an Enum subclass, not {enumcls!r}"
            )

        if default is None:
            try:
                default = next(iter(enumcls.__members__.values()))
            except StopIteration:
                raise TypeError(
                    f"Enum class does not have any members: {enumcls!r}"
                ) from None
        elif isinstance(default, str):
            default = enumcls[default]
        elif not isinstance(default, enumcls):
            raise TypeError(
                f"'default' must be a member of 'enumcls', not {default!r}"
            )
        assert isinstance(default, enumcls)

        super().__init__(attribute, default=default, writable=writable)
        self.enumcls = enumcls

    def _from_xml(self, obj: _obj.ModelElement, value: str, /) -> E:
        del obj
        return self.enumcls(value)

    def _to_xml(self, obj: _obj.ModelElement, value: E | str, /) -> str | None:
        del obj
        if isinstance(value, str):
            value = self.enumcls[value]
        return value.value


class MultiStringPOD(BasePOD[cabc.MutableSequence[str]]):
    """A POD that provides access to a list of strings."""

    __slots__ = (
        "__name__",
        "__objclass__",
        "tag",
    )

    def __init__(self, tag: str) -> None:
        super().__init__(tag, default=[], writable=True)
        self.tag = tag

        self.__name__ = "(unknown)"
        self.__objclass__: type[t.Any] | None = None

    @t.overload
    def __get__(self, obj: None, objtype: type) -> te.Self: ...
    @t.overload
    def __get__(
        self, obj: t.Any, objtype: type | None = None
    ) -> cabc.MutableSequence[str]: ...
    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:
            return self

        return _MultiPODValues(obj._element, self.tag)

    def __set__(self, obj: t.Any, value: cabc.Sequence[str] | None) -> None:
        if value is None:
            value = ()
        self.__get__(obj)[:] = value

    def __delete__(self, obj: t.Any) -> None:
        self.__get__(obj)[:] = ()

    def _from_xml(
        self, obj: _obj.ModelElement, value: str, /
    ) -> cabc.MutableSequence[str]:
        del obj, value
        raise TypeError("Not used for this POD type")

    def _to_xml(
        self, obj: _obj.ModelElement, value: cabc.MutableSequence[str], /
    ) -> str | None:
        del obj, value
        raise TypeError("Not used for this POD type")


class _MultiPODValues(cabc.MutableSequence[str]):
    def __init__(self, parent: etree._Element, tag: str) -> None:
        self._parent = parent
        self._tag = tag

    @t.overload
    def __getitem__(self, _: int, /) -> str: ...
    @t.overload
    def __getitem__(self, _: slice, /) -> cabc.MutableSequence[str]: ...
    def __getitem__(
        self, i: int | slice, /
    ) -> str | cabc.MutableSequence[str]:
        values = list(self._parent.iterchildren(self._tag))
        if isinstance(i, slice):
            return [v.text or "" for v in values[i]]
        return values[i].text or ""

    @t.overload
    def __setitem__(self, i: int, v: str, /) -> None: ...
    @t.overload
    def __setitem__(self, i: slice, v: cabc.Iterable[str], /) -> None: ...
    def __setitem__(
        self, idx: int | slice, value: str | cabc.Iterable[str], /
    ) -> None:
        if not isinstance(idx, int | slice):
            raise TypeError(
                "indices must be integers or slices, not {type(i).__name__}"
            )

        if isinstance(idx, slice) and isinstance(value, cabc.Iterable):
            it = self._parent.iterchildren(self._tag)
            elems = list(itertools.islice(it, idx.start, idx.stop, idx.step))
            values = [i.text for i in elems]
            values[idx] = value
            for e, v in zip(elems, values, strict=True):
                e.text = v

        elif isinstance(idx, int) and isinstance(value, str):
            if idx < 0:
                idx += len(self)
                if idx < 0:
                    raise IndexError("assignment index out of range")

            it = self._parent.iterchildren(self._tag)
            elem = next(itertools.islice(it, idx, idx + 1), None)
            if elem is None:
                raise IndexError("assignment index out of range") from None
            elem.text = value

    def __delitem__(self, i: int | slice, /) -> None:
        it = self._parent.iterchildren(self._tag)
        if isinstance(i, slice):
            elems = list(itertools.islice(it, i.start, i.stop, i.step))
        else:
            elems = list(itertools.islice(it, i, i + 1, 1))
        for e in elems:
            self._parent.remove(e)

    def __len__(self) -> int:
        return sum(1 for _ in self._parent.iterchildren(self._tag))

    def insert(self, index: int, value: str, /) -> None:
        if index < 0:
            index = max(index + len(self), 0)
        e: etree._Element | None = None

        container = self._parent.makeelement(self._tag)
        container.text = value

        for i, e in enumerate(self._parent.iterchildren(self._tag)):
            if i == index:
                e.addprevious(container)
                break
        else:
            if e is not None:
                e.addnext(container)
                e.append(container)
