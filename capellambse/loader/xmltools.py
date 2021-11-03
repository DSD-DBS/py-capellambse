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
"""Useful helpers for making object-oriented XML proxy classes."""
from __future__ import annotations

import abc
import collections.abc as cabc
import enum
import typing as t

from lxml import etree

import capellambse.loader


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
        if optional:
            self.default = default
        else:
            self.default = self.NOT_OPTIONAL

        self.__name__ = "(unknown)"
        self.__objclass__: type[t.Any] | None = None
        self.__doc__ = __doc__

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
            return self.returntype(xml_element.attrib[self.attribute])
        except KeyError:
            if self.default is not self.NOT_OPTIONAL:
                return self.default and self.returntype(
                    self.default.format(self=obj, xml=xml_element)
                )
            raise AttributeError(
                "Mandatory XML attribute {!r} not found on {!r}".format(
                    self.attribute, xml_element
                )
            ) from None

    def __set__(self, obj, value) -> None:
        if not self.writable:
            try:
                curval = self.__get__(obj, type(obj))
            except AttributeError:
                curval = None
            if curval is not None:
                raise AttributeError(
                    "Cannot set attribute {1!r} on {0!r} objects".format(
                        type(obj).__name__, self.__name__
                    )
                ) from None

        getattr(obj, self.xmlattr).attrib[self.attribute] = value

    def __delete__(self, obj: t.Any) -> None:
        if not self.writable:
            raise AttributeError(
                "Cannot delete attribute {1!r} on {0!r} objects".format(
                    type(obj).__name__, self.__name__
                )
            )

        getattr(obj, self.xmlattr).set(self.attribute, None)

    def __set_name__(self, owner: type[t.Any], name: str) -> None:
        self.__name__ = name
        self.__objclass__ = owner


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

        try:
            return super().__get__(obj, objtype) == "true"
        except AttributeError:
            return False

    def __set__(self, obj, value) -> None:
        value = bool(value)
        if value == self.default:
            self.__delete__(obj)
        else:
            super().__set__(obj, value)


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
    any of the Enum's members, a KeyError will be raised by default.  By
    setting the constructor kwarg ``badstring`` to True, you can instead
    retrieve the raw string value that was placed in the XML.  Note that
    even with ``badstring=True``, the Property will still disallow
    setting such values.
    """

    __slots__ = ("enumcls", "badstring", "default", "__name__", "__objclass__")

    def __init__(
        self,
        xmlattr: str,
        attribute: str,
        enumcls: type[enum.Enum],
        *args: t.Any,
        default: str | enum.Enum | None = None,
        badstring: bool = False,
        **kw: t.Any,
    ) -> None:
        """Create an EnumAttributeProperty.

        Parameters
        ----------
        enumcls
            The :class:`enum.Enum` subclass to use.  The class' members'
            values are used as the possible values for the XML
            attribute.
        default
            The default value to return if the attribute is not present
            in the XML.  If None, an AttributeError will be raised
            instead.
        badstring
            True to return bad XML values as raw string instead of
            raising a KeyError.
        """
        if not (isinstance(enumcls, type) and issubclass(enumcls, enum.Enum)):
            raise TypeError(
                "enumcls must be an Enum subclass, not {!r}".format(enumcls)
            )

        super().__init__(xmlattr, attribute, *args, **kw)
        self.badstring = badstring
        self.enumcls = enumcls
        if default is None or isinstance(default, enumcls):
            self.default = default
        elif isinstance(default, str):
            self.default = enumcls[default]
        else:
            raise TypeError(
                "default must be a member (or its name) of {!r}, not {!r}".format(
                    enumcls, default
                )
            )

    def __get__(self, obj: t.Any, objtype: type | None = None) -> t.Any:
        if obj is None:
            return self

        try:
            rawvalue = super().__get__(obj, objtype)
        except AttributeError:
            if self.default is not None:
                return self.default
            raise

        try:
            return self.enumcls[rawvalue]
        except KeyError:
            if self.badstring:
                return rawvalue
            raise

    def __set__(self, obj: t.Any, value: t.Any) -> None:
        assert self.__objclass__ is not None
        if isinstance(value, str):
            try:
                value = self.enumcls[value]
            except KeyError:
                raise ValueError(
                    "{!r} is not a valid value for {}.{}".format(
                        value, self.__objclass__.__name__, self.__name__
                    )
                ) from None
        elif not isinstance(value, self.enumcls):
            raise TypeError(
                "Expected str or member of {}, not {!r}".format(
                    self.enumcls, value
                )
            )

        return super().__set__(obj, value.value)

    def __set_name__(self, owner: type[t.Any], name: str) -> None:
        self.__name__ = name
        self.__objclass__ = owner


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
