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
    "StringPOD",
]

import abc
import datetime
import enum
import math
import os
import re
import typing as t

import markupsafe
import typing_extensions as te

from capellambse import helpers

from . import E, U


class BasePOD(t.Generic[U]):
    """A plain-old-data descriptor."""

    __slots__ = (
        "attribute",
        "default",
        "writable",
        "__name__",
        "__objclass__",
        "__dict__",
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
        return self._from_xml(data)

    def __set__(self, obj: t.Any, value: U | None) -> None:
        if not self.writable and self.attribute in obj._element.attrib:
            raise TypeError(f"{self._qualname} is not writable")

        if value is not None and value != self.default:
            data = self._to_xml(value)
        else:
            data = None

        if data is None:
            obj._element.attrib.pop(self.attribute, None)
        else:
            obj._element.attrib[self.attribute] = data

    def __delete__(self, obj: t.Any) -> None:
        self.__set__(obj, None)

    def __set_name__(self, owner: type[t.Any], name: str) -> None:
        self.__name__ = name
        self.__objclass__ = owner

    @abc.abstractmethod
    def _from_xml(self, value: str, /) -> U: ...
    @abc.abstractmethod
    def _to_xml(self, value: U, /) -> str | None: ...


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

    def _from_xml(self, value: str, /) -> str:
        return value

    def _to_xml(self, value: str, /) -> str:
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

    def _from_xml(self, value: str, /) -> markupsafe.Markup:
        if os.getenv("CAPELLAMBSE_XHTML") == "1":
            value = helpers.repair_html(value)
        return markupsafe.Markup(value)

    def _to_xml(self, value: markupsafe.Markup, /) -> str:
        return helpers.repair_html(value)


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

    def _from_xml(self, value: str, /) -> bool:
        return value == "true"

    def _to_xml(self, value: bool, /) -> str:
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

    def _from_xml(self, data: str, /) -> int:
        return int(data)

    def _to_xml(self, value: int, /) -> str | None:
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

    def _from_xml(self, data: str, /) -> float:
        return float(data)

    def _to_xml(self, value: float, /) -> str | None:
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

    def _from_xml(self, value: str, /) -> datetime.datetime:
        formatted = self.re_get.sub(":", value)
        return datetime.datetime.fromisoformat(formatted)

    def _to_xml(self, value: datetime.datetime | None, /) -> str:
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

    def _from_xml(self, value: str, /) -> E:
        return self.enumcls(value)

    def _to_xml(self, value: E | str, /) -> str | None:
        if isinstance(value, str):
            value = self.enumcls[value]
        return value.value
