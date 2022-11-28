# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Classes that represent different property value types."""

from __future__ import annotations

import abc
import collections.abc as cabc

import capellambse._namespaces as _n

from . import model, validation
from .core import AttributeProperty, Generic, XMLDictProxy

NAMESPACED_PV = "org.polarsys.capella.core.data.capellacore:{}"
XTYPE_KEY = f"{{{_n.NAMESPACES['xsi']}}}type"


class GenericPropertyValue(Generic, metaclass=abc.ABCMeta):
    """Base class for property value types."""

    description = AttributeProperty("xml_element", "description")
    xtype = AttributeProperty(
        "xml_element", f"{{{_n.NAMESPACES['xsi']}}}type", writable=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent = None

    @staticmethod
    def applyto(pvmt_ext, defelem, modelobj, targetelem):
        """Apply a property value to ``targetelem``.

        Parameters
        ----------
        pvmt_ext
            The PVMT Extension object.
        defelem
            The ``ownedPropertyValues`` element that should be applied.
        modelobj
            A model object's XML element that will be a (direct or
            indirect) parent to this property value.
        targetelem
            The new ``ownedPropertyValues`` element.
        """
        for attr in (f"{{{_n.NAMESPACES['xsi']}}}type", "name", "value"):
            try:
                targetelem.attrib[attr] = defelem.attrib[attr]
            except KeyError:
                pass

        targetelem.attrib.update(
            {
                "id": pvmt_ext.model.generate_uuid(modelobj),
                "appliedPropertyValues": (
                    pvmt_ext.model.create_link(modelobj, defelem)
                ),
            }
        )

    @staticmethod
    @abc.abstractmethod
    def cast(value):
        """Cast the given string into an appropriate Python object."""

    def serialize(self, value, element=None):
        """Serialize the given value into an XML string.

        This function must be able to handle two types of input values:

        1. The type produced by ``.cast()``, which shall be turned back
           into its XML form, so that it can be passed into ``.cast()``
           again.
        2. The XML representation of a valid value, i.e. its own output.

        If it is ambiguous which of the two types is being handled, the
        former shall be assumed.

        Note that escaping of XML special characters is handled by the
        underlying XML library.

        The default implementation works for the simple case where
        ``cast`` is a type constructor, but for more complex cases it
        should be overridden.

        Parameters
        ----------
        value
            The value that should be serialized.
        element
            The XML element into which the value will be inserted.  This
            may be used to construct links across fragment boundaries.
            This parameter may be None, in which case it is assumed that
            all elements exist within the same fragment.
        """
        del element

        if not isinstance(self.cast, type):
            type_name = type(self).__name__
            raise TypeError(
                f"{type_name}.cast is not a simple type;"
                f"please implement {type_name}.serialize"
            )
        # pylint: disable=isinstance-second-argument-not-valid-type
        if isinstance(value, self.cast):
            return str(value)
        return str(self.cast(value))


class StringPropertyValue(GenericPropertyValue):
    """A string property value."""

    cast = str


class BooleanPropertyValue(GenericPropertyValue):
    """A boolean property value."""

    @staticmethod
    def cast(value):
        if value == "true":
            return True
        if value == "false":
            return False
        raise ValueError(
            f"Boolean values must be either 'true' or 'false', not {value!r}"
        )

    @classmethod
    def serialize(cls, value, element=None):
        del element
        if isinstance(value, str):
            value = cls.cast(value)
        return "true" if value else "false"


class IntegerPropertyValue(GenericPropertyValue):
    """An integer property value."""

    cast = int

    @property
    def unit(self):
        """Return the measurement unit of this property value."""
        unit = self.xml_element.xpath('*[@name="__UNIT__"]/@value')
        return unit[0] if unit else None


class FloatPropertyValue(GenericPropertyValue):
    """A floating point property value."""

    cast = float

    @property
    def unit(self):
        """Return the measurement unit of this property value."""
        unit = self.xml_element.xpath('*[@name="__UNIT__"]/@value')
        return unit[0] if unit else None


class EnumerationPropertyValue(GenericPropertyValue):
    """An enumeration property value."""

    def __init__(self, *args, typedef=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.typedef = typedef

    @property  # FIXME: what's the type?
    def parent(self):
        """Return the parent group of this property value."""
        return self._parent

    @parent.setter
    def parent(self, parent):
        self._parent = parent
        self._typedef = None

    @property
    def typedef(self):
        """Return the type definition of this enumeration."""
        if self._typedef is None:
            if self.parent is None:
                raise TypeError("Cannot resolve typedef: No parent")
            domain = self.parent.parent
            assert isinstance(domain, model.Domain)
            self._typedef = domain.enums[
                self.xml_element.attrib["type"].split("#")[-1]
            ]
        return self._typedef

    @typedef.setter
    def typedef(self, typedef):
        self._typedef = typedef

    @property
    def default_value(self):
        """Return this property's default value."""
        return self.typedef[self.xml_element.attrib["value"].split("#")[-1]]

    @staticmethod
    def applyto(pvmt_ext, defelem, modelobj, targetelem):
        super().applyto(pvmt_ext, defelem, modelobj, targetelem)

        typeelem = pvmt_ext.model[defelem.attrib["type"].split("#")[-1]]
        valelem = pvmt_ext.model[defelem.attrib["value"].split("#")[-1]]
        targetelem.attrib.update(
            {
                "type": pvmt_ext.model.create_link(modelobj, typeelem),
                "value": pvmt_ext.model.create_link(modelobj, valelem),
            }
        )

    def cast(self, value):
        return self.typedef[value.split("#")[-1]]["name"]

    def serialize(self, value, element=None):
        if not isinstance(value, str):
            raise TypeError("Enumeration values must be str")

        if element is None:
            element = self.xml_element

        pvext = self.parent.parent.parent

        for typeitem in self.typedef.items():
            if value == typeitem[1]["name"]:
                return pvext.model.create_link(
                    element, pvext.model[typeitem[0]]
                )

        value = value.split("#")[-1]
        if value in self.typedef:
            # It's already the UUID.  Normalize it.
            return pvext.model.create_link(element, pvext.model[value])

        raise ValueError(f"Not a valid value for this enumeration: {value}")


class EnumerationPropertyType(XMLDictProxy):
    """Maps the literals' UUIDs to their human-readable values."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, **kwargs, childtag="ownedLiterals", keyattr="id"
        )

    @property
    def literals(self):
        """Return a list of valid literal values for this enumeration."""
        return list(self.values())

    def _extract_value(self, element):
        return dict(element.attrib)

    def _insert_value(self, element, value):
        element.attrib.update(value)


PROPERTY_LOADER: cabc.Mapping[str, type[GenericPropertyValue]] = {
    "EnumerationPropertyValue": EnumerationPropertyValue,
    "StringPropertyValue": StringPropertyValue,
    "FloatPropertyValue": FloatPropertyValue,
    "BooleanPropertyValue": BooleanPropertyValue,
    "IntegerPropertyValue": IntegerPropertyValue,
}


def select_property_loader(element):
    """Execute the appropriate loader for the PV definition element."""
    xtype = str(element.attrib[XTYPE_KEY]).rsplit(":", maxsplit=1)[-1]
    if xtype not in PROPERTY_LOADER:
        raise Exception(f"XSI type {xtype} is not yet supported")
    return PROPERTY_LOADER[xtype](element)


class AppliedPropertyValueGroup(XMLDictProxy):
    """A group of applied property values."""

    def __init__(self, pvmt_ext, *args, **kwargs):
        """Create an AppliedPropertyValueGroup.

        Parameters
        ----------
        pvmt_ext
            The :class:`PVMTExtension` object of the model.
        """
        super().__init__(
            *args, childtag="ownedPropertyValues", keyattr="name", **kwargs
        )
        self._groupdef = self._get_named_pv_group(
            pvmt_ext, self.xml_element.attrib["name"]
        )
        self._pvmt_ext = pvmt_ext

    def get_definition(self, key):
        """Return the PV definition instance for the given key."""
        for propdef in self._groupdef.values():
            if propdef.name == key:
                return propdef
        raise KeyError(f"Key {key} is not defined in the group")

    def _extract_value(self, element):
        pvtype = self._groupdef[
            element.attrib["appliedPropertyValues"].split("#")[-1]
        ]
        if "value" in element.attrib:
            return pvtype.cast(element.attrib["value"])
        else:
            return None

    def _prepare_child(self, element, key):
        super()._prepare_child(element, key)
        propdef = self.get_definition(key)
        propdef.applyto(
            self._pvmt_ext,
            propdef.xml_element,
            self._groupdef.xml_element,
            element,
        )

    def _insert_value(self, element, value):
        pvtype = self._groupdef[
            element.attrib["appliedPropertyValues"].split("#")[-1]
        ]
        element.set("value", pvtype.serialize(value, element))

    @classmethod
    def applyto(cls, pvmt_ext, xml_element, groupname):
        """Apply the named property value group to the given element.

        Parameters
        ----------
        pvmt_ext
            The PVMT extension object
        xml_element
            The XML element of the target object
        groupname
            The fully qualified name of the PVMT group

        Returns
        -------
        element
            The newly created XML element, a child of xml_element.
        """
        groupdef = cls._get_named_pv_group(pvmt_ext, groupname)
        validation.validate_group_scope(pvmt_ext, groupdef, xml_element)

        groupelem = xml_element.makeelement(
            "ownedPropertyValueGroups",
            attrib={
                f"{{{_n.NAMESPACES['xsi']}}}type": (
                    NAMESPACED_PV.format("PropertyValueGroup")
                ),
                "id": pvmt_ext.model.generate_uuid(xml_element),
                "name": groupname,
                "appliedPropertyValueGroups": (
                    pvmt_ext.model.create_link(
                        xml_element, groupdef.xml_element
                    )
                ),
            },
        )

        # Apply the group's property values
        for defelem in groupdef.xml_element.iterchildren(
            "ownedPropertyValues"
        ):
            propelem = groupelem.makeelement("ownedPropertyValues")
            PROPERTY_LOADER[
                defelem.get(f"{{{_n.NAMESPACES['xsi']}}}type").split(":")[-1]
            ].applyto(pvmt_ext, defelem, xml_element, propelem)
            groupelem.append(propelem)

        xml_element.append(groupelem)
        pvmt_ext.model.idcache_index(groupelem)
        if "appliedPropertyValueGroups" in xml_element.attrib:
            xml_element.attrib["appliedPropertyValueGroups"] = " ".join(
                [
                    xml_element.attrib["appliedPropertyValueGroups"],
                    f'#{groupelem.attrib["id"]}',
                ]
            )
        else:
            xml_element.attrib[
                "appliedPropertyValueGroups"
            ] = f'#{groupelem.attrib["id"]}'
        return groupelem

    @staticmethod
    def _get_named_pv_group(pvmt_ext, groupname):
        domainname, groupname = groupname.split(".")
        domain = [d for d in pvmt_ext.values() if d.name == domainname]
        if len(domain) != 1:
            raise ValueError(f"Domain {domainname!r} not found in model")

        group = [g for g in domain[0].values() if g.name == groupname]
        if len(group) != 1:
            raise ValueError(
                f"Group {groupname!r} not found in model domain {domainname!r}"
            )

        return group[0]
