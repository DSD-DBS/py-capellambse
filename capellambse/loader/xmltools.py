# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Useful helpers for making object-oriented XML proxy classes."""
from __future__ import annotations

import abc
import collections.abc as cabc
import datetime
import enum
import math
import sys
import typing as t

import markupsafe
from lxml import etree

import capellambse.loader
from capellambse import helpers


class AttributeProperty:
    """A property that forwards access to the underlying XML element."""

    __slots__ = (
        "attribute",
        "default",
        "writable",
        "xmlattr",
        "returntype",
        "__name__",
        "__objclass__",
        "__dict__",
    )

    NOT_OPTIONAL = object()

    def __init__(
        self,
        xmlattr: str,
        attribute: str,
        *,
        returntype: cabc.Callable[[str], t.Any] = str,
        optional: bool = False,
        default: t.Any = None,
        writable: bool = True,
        __doc__: str | None = None,
    ) -> None:
        """Create an AttributeProperty.

        Parameters
        ----------
        xmlattr
            The owning type's instance attribute pointing to the XML
            element.
        attribute
            The attribute on the XML element to handle.
        returntype
            The type to return the result as. Must accept a single
            ``str`` as argument.
        optional
            If False (default) and the XML attribute does not exist, an
            AttributeError is raised.  Otherwise a default value is
            returned.
        default
            A new-style format string to use as fallback value.  You can
            access the object instance as ``self`` and the XML element
            as ``xml``.
        writable
            Whether to allow modifying the XML attribute.
        """
        self.attribute = attribute
        self.writable = writable
        self.xmlattr = xmlattr
        self.returntype = returntype
        if optional or default is not None:
            self.default = default
        else:
            self.default = self.NOT_OPTIONAL

        self.__name__ = "(unknown)"
        self.__objclass__: type[t.Any] | None = None
        self.__doc__ = __doc__

    @property
    def _qualname(self) -> str:
        """Generate the qualified name of this descriptor."""
        if self.__objclass__ is None:
            return f"(unknown {type(self).__name__} - call __set_name__)"
        return f"{self.__objclass__.__name__}.{self.__name__}"

    @t.overload
    def __get__(self, obj: None, objtype: type) -> AttributeProperty:
        ...

    @t.overload
    def __get__(self, obj: t.Any, objtype: type | None = None) -> t.Any:
        ...

    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:
            return self

        xml_element = getattr(obj, self.xmlattr)
        try:
            rv = self.returntype(xml_element.attrib[self.attribute])
        except KeyError:
            if self.default is not self.NOT_OPTIONAL:
                return self.default and self.returntype(
                    self.default.format(self=obj, xml=xml_element)
                )
            raise TypeError(
                f"Mandatory XML attribute {self.attribute!r} not found on {xml_element!r}"
            ) from None

        sys.audit("capellambse.read_attribute", obj, self.__name__, rv)
        return rv

    def __set__(self, obj, value) -> None:
        xml_element = getattr(obj, self.xmlattr)
        if not self.writable and xml_element.get(self.attribute) is not None:
            raise TypeError(
                f"Cannot set attribute {self.__name__!r} on {type(obj).__name__!r} objects"
            )

        if value == self.default:
            return self.__delete__(obj)

        stringified = str(value)

        try:
            roundtripped = self.returntype(stringified)
        except (TypeError, ValueError) as err:
            raise TypeError(
                "Value is not round-trip safe:"
                f" Cannot read back {stringified} as {value}"
            ) from err

        if roundtripped != value:
            raise TypeError(
                "Value is not round-trip safe:"
                f" {value!r} would be read back as {roundtripped!r}"
            )

        xml_element.attrib[self.attribute] = stringified

    def __delete__(self, obj: t.Any) -> None:
        if not self.writable:
            raise TypeError(
                f"Cannot delete attribute {self.__name__!r} on {type(obj).__name__!r} objects"
            )

        xml_element = getattr(obj, self.xmlattr)
        try:
            del xml_element.attrib[self.attribute]
        except KeyError:
            pass

    def __set_name__(self, owner: type[t.Any], name: str) -> None:
        self.__name__ = name
        self.__objclass__ = owner


class HTMLAttributeProperty(AttributeProperty):
    """An AttributeProperty that gracefully handles HTML-in-XML."""

    def __init__(
        self,
        xmlattr: str,
        attribute: str,
        *,
        optional: bool = False,
        writable: bool = True,
        __doc__: str | None = None,
    ) -> None:
        super().__init__(
            xmlattr,
            attribute,
            default=None,
            returntype=markupsafe.Markup,
            optional=optional,
            writable=writable,
            __doc__=__doc__,
        )

    def __set__(self, obj: t.Any, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(
                f"Cannot set {self._qualname} on {obj!r}:"
                f" Expected str, got {type(value).__name__}"
            )
        value = helpers.repair_html(value)
        super().__set__(obj, value)


class NumericAttributeProperty(AttributeProperty):
    """Attribute property that handles (possibly infinite) numeric values.

    Positive infinity is stored in Capella XML as `*`. This class takes
    care of converting to and from that value when setting or retrieving
    the value.

    Note that there is currently no representation of negative infinity,
    which is why ``-inf`` is rejected with a :class:`ValueError`.

    ``NaN`` values are rejected with a ValueError as well.
    """

    def __init__(
        self,
        xmlattr: str,
        attribute: str,
        *,
        optional: bool = False,
        default: int | float | None = None,
        allow_float: bool = True,
        writable: bool = True,
        __doc__: str | None = None,
    ) -> None:
        super().__init__(
            xmlattr,
            attribute,
            optional=optional,
            default=default,
            writable=writable,
            __doc__=__doc__,
        )
        self.number_type = float if allow_float else int

    def __get__(self, obj, objtype=None):
        value = super().__get__(obj, objtype)
        if not isinstance(value, str):
            return value

        if value == "*":
            return math.inf
        return self.number_type(value)

    def __set__(self, obj, value) -> None:
        if not isinstance(value, (int, float)):
            raise TypeError(f"Not a number: {value}")

        if value == math.inf:
            strvalue = "*"
        elif value == -math.inf:
            raise ValueError("Cannot set value to negative infinity")
        else:
            strvalue = str(self.number_type(value))
        super().__set__(obj, strvalue)


class BooleanAttributeProperty(AttributeProperty):
    """An AttributeProperty that works with booleans."""

    def __init__(
        self,
        xmlattr: str,
        attribute: str,
        *,
        writable: bool = True,
        __doc__: str | None = None,
    ) -> None:
        super().__init__(
            xmlattr,
            attribute,
            returntype=lambda x: x,
            optional=False,
            writable=writable,
            __doc__=__doc__,
        )

    @t.overload
    def __get__(self, obj: None, objtype: type) -> AttributeProperty:
        ...

    @t.overload
    def __get__(self, obj: t.Any, objtype: type | None = None) -> bool:
        ...

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        xml_element = getattr(obj, self.xmlattr)
        return xml_element.get(self.attribute, "false") == "true"

    def __set__(self, obj, value) -> None:
        if value:
            super().__set__(obj, "true")
        else:
            self.__delete__(obj)


class DatetimeAttributeProperty(AttributeProperty):
    """An AttributeProperty that stores a datetime.

    The value stored in the XML will be formatted according to the
    ``format`` given to the constructor. When loading a value, it must
    strictly be parsable with the same format, otherwise an exception
    will be raised.
    """

    __slots__ = ("format",)

    def __init__(
        self,
        xmlattr: str,
        attribute: str,
        *,
        format: str,
        optional: bool = True,
        writable: bool = True,
        __doc__: str | None = None,
    ) -> None:
        super().__init__(
            xmlattr,
            attribute,
            optional=optional,
            writable=writable,
            __doc__=__doc__,
        )
        self.format = format

    @t.overload
    def __get__(self, obj: None, objtype: type) -> DatetimeAttributeProperty:
        ...

    @t.overload
    def __get__(
        self, obj: t.Any, objtype: type | None = None
    ) -> datetime.datetime:
        ...

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        formatted = super().__get__(obj, objtype)
        if formatted is None:
            return None
        return datetime.datetime.strptime(formatted, self.format)

    def __set__(self, obj, value) -> None:
        if value is None:
            self.__delete__(obj)
        elif isinstance(value, datetime.datetime):
            if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
                value = value.astimezone()
            super().__set__(obj, value.strftime(self.format))
        else:
            raise TypeError(f"Expected datetime, not {type(value).__name__}")


class EnumAttributeProperty(AttributeProperty):
    """An AttributeProperty whose values are determined by an Enum.

    This works in much the same way as the standard AttributeProperty,
    except that the returned and consumed values are not simple strings,
    but members of the Enum that was passed into the constructor.

    Usually it is expected that the enum members will be directly
    assigned to this property.  However it is also possible to assign a
    :class:`str` instead.  In this case, the string will be taken to be
    an enum member's name.  In both cases, the enum member's value will
    be placed in the underlying XML attribute.

    If the XML attribute contains a value that does not correspond to
    any of the Enum's members, a KeyError will be raised. If the
    attribute is completely missing from the XML and there was no
    ``default=`` value set during construction, this property will
    return ``None``.
    """

    __slots__ = ("enumcls",)

    def __init__(
        self,
        xmlattr: str,
        attribute: str,
        enumcls: type[enum.Enum],
        *args: t.Any,
        default: str | enum.Enum | None = None,
        **kw: t.Any,
    ) -> None:
        """Create an EnumAttributeProperty.

        Parameters
        ----------
        xmlattr
            The owning type's instance attribute pointing to the XML
            element.
        attribute
            The attribute on the XML element to handle.
        enumcls
            The :class:`enum.Enum` subclass to use.  The class' members'
            values are used as the possible values for the XML
            attribute.
        default
            The default value to return if the attribute is not present
            in the XML.  If None, an AttributeError will be raised
            instead.
        """
        if not (isinstance(enumcls, type) and issubclass(enumcls, enum.Enum)):
            raise TypeError(
                "enumcls must be an Enum subclass, not {!r}".format(enumcls)
            )

        if default is None or isinstance(default, enumcls):
            pass
        elif isinstance(default, str):
            default = enumcls[default]
        else:
            raise TypeError(
                f"default must be a member (or its name) of {enumcls!r}, not {default!r}"
            )
        super().__init__(
            xmlattr, attribute, *args, optional=True, default=default, **kw
        )
        self.enumcls = enumcls

    def __get__(self, obj: t.Any, objtype: type | None = None) -> t.Any:
        if obj is None:
            return self

        try:
            rawvalue = super().__get__(obj, objtype)
        except AttributeError:
            if self.default is not None:
                return self.default
            raise

        if rawvalue is None:
            return None
        return self.enumcls[rawvalue]

    def __set__(self, obj: t.Any, value: str | enum.Enum) -> None:
        assert self.__objclass__ is not None
        if isinstance(value, str):
            try:
                value = self.enumcls[value]
            except KeyError:
                raise ValueError(
                    f"{value!r} is not a valid value for {self._qualname}"
                ) from None
        elif not isinstance(value, self.enumcls):
            raise TypeError(
                f"Expected str or member of {self.enumcls}, not {value!r}"
            )

        return super().__set__(obj, value.name)


class XMLDictProxy(cabc.MutableMapping):
    """Provides dict-like access to underlying XML structures.

    Subclasses of this class behave like regular Python dictionary,
    except that all key/value accesses are transparently forwarded to
    the underlying XML.
    """

    def __init__(
        self,
        xml_element: etree._Element,
        *args: t.Any,
        childtag: str,
        keyattr: str,
        model: capellambse.loader.MelodyLoader | None = None,
        **kwargs: t.Any,
    ) -> None:
        """Initialize the XMLDictProxy.

        Parameters
        ----------
        xml_element
            The underlying XML element.
        childtag
            The XML tag of handled child elements.
        keyattr
            The element attribute to use as dictionary key.
        model
            Reference to the original MelodyLoader.  If not None, the
            loader will be informed about element creation and deletion.
        """
        super().__init__(*args, **kwargs)  # type: ignore[call-arg]
        self.__childtag = childtag
        self.__keyattr = keyattr
        self.model = model
        self.xml_element = xml_element

    def __iter__(self) -> cabc.Iterator[str]:
        return (
            e.attrib[self.__keyattr]
            for e in self.xml_element.iterchildren(self.__childtag)
        )

    def __len__(self) -> int:
        return sum(1 for i in self.xml_element.iterchildren(self.__childtag))

    def __getitem__(self, key: str) -> t.Any:
        for elem in self.xml_element.iterchildren(self.__childtag):
            if elem.attrib[self.__keyattr] == key:
                return self._extract_value(elem)
        raise KeyError(key)

    def __setitem__(self, key: str, value: t.Any) -> None:
        for elem in self.xml_element.iterchildren(self.__childtag):
            if elem.attrib[self.__keyattr] == key:
                break
        else:
            # Doesn't exist in the tree yet: create a new child
            elem = self.xml_element.makeelement(
                self.__childtag, {self.__keyattr: key}
            )
            self._prepare_child(elem, key)
            self.xml_element.append(elem)
            if self.model is not None:
                self.model.idcache_index(elem)
        self._insert_value(elem, value)

    def __delitem__(self, key: str) -> None:
        for elem in self.xml_element.iterchildren(self.__childtag):
            if elem.attrib[self.__keyattr] == key:
                if self.model is not None:
                    self.model.idcache_remove(elem)
                self.xml_element.remove(elem)
                return
        raise KeyError(key)

    def copy(self) -> dict[str, t.Any]:
        """Make a copy of this proxy as standard Python :class:`dict`."""
        return dict(self.items())

    @abc.abstractmethod
    def _extract_value(self, element: etree._Element) -> t.Any:
        """Extract the dict value from the given element."""

    @abc.abstractmethod
    def _insert_value(self, element: etree._Element, value: t.Any) -> None:
        """Insert the dict value into the given element."""

    def _prepare_child(self, element: etree._Element, key: str) -> None:
        """Prepare a freshly created element for insertion into the XML.

        The key is already set on the element when this method is
        called; the extra argument is provided for convenience.

        If a subclass wants to abort inserting the element, it should
        raise a KeyError.
        """
