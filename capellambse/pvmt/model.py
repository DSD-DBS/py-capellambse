# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Provides easy access to the Polarsys Capella PVMT extensions."""

from __future__ import annotations

import typing as t

from lxml import etree

import capellambse._namespaces as _n

from . import exceptions
from .core import AttributeProperty, XMLDictProxy
from .types import (
    AppliedPropertyValueGroup,
    EnumerationPropertyType,
    select_property_loader,
)

XPTH_FIND_BY_XTYPE = '*[@xsi:type="{}"]'
X_PVMT = "org.polarsys.capella.core.data.capellacore:PropertyValuePkg"


class Group(XMLDictProxy):
    """PVMT Group."""

    parent: t.Any | None

    scope = AttributeProperty("xml_element", "description")

    def __init__(self, *args, parent=None, **kwargs):
        super().__init__(
            *args, **kwargs, childtag="ownedPropertyValues", keyattr="id"
        )
        self.parent = parent

    @property
    def properties(self):
        """Return a list of all properties defined in this group."""
        return list(self.values())

    @classmethod
    def from_xml_element(cls, element: etree._Element) -> Group:
        """Construct an object from the given XML element."""
        return super().from_xml_element(element)  # type:ignore[return-value]

    def _extract_value(self, element):
        prop = select_property_loader(element)
        prop.parent = self
        return prop

    def _prepare_child(self, element, key):
        raise NotImplementedError(
            "Adding new properties to a group is not implemented yet"
        )

    def _insert_value(self, element, value):
        raise NotImplementedError(
            "Modifying property definitions is not implemented yet"
        )


class Domain(XMLDictProxy):
    """A PVMT Domain."""

    def __init__(self, element, *args, parent=None, **kwargs):
        super().__init__(
            element,
            *args,
            **kwargs,
            childtag="ownedPropertyValueGroups",
            keyattr="id",
        )
        self.enums = _DomainEnums(element)
        self.parent = parent

    @property
    def groups(self):
        """Return a list of all property value groups in this domain."""
        return list(self.values())

    def _extract_value(self, element):
        group = Group.from_xml_element(element)
        group.parent = self
        return group

    def _prepare_child(self, element, key):
        raise NotImplementedError(
            "Adding groups to a domain is not implemented yet"
        )

    def _insert_value(self, element, value):
        raise NotImplementedError(
            "Modifying domain groups is not implemented yet"
        )


class _DomainEnums(XMLDictProxy):
    _extract_value = (
        EnumerationPropertyType.from_xml_element  # type: ignore[assignment]
    )

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            **kwargs,
            childtag="ownedEnumerationPropertyTypes",
            keyattr="id",
        )

    def _prepare_child(self, element, key):
        raise NotImplementedError(
            "Adding new enums to a domain is not implemented yet"
        )

    def _insert_value(self, element, value):
        raise NotImplementedError(
            "Modifying enum definitions is not implemented yet"
        )


class PVMTExtension(XMLDictProxy):
    """Facilitates access to property values."""

    def __init__(self, element, model=None):
        super().__init__(
            element, childtag="ownedPropertyValuePkgs", keyattr="id"
        )
        self.model = model

    @property
    def domains(self):
        """Return a list of all property value domains in the model."""
        return list(self.values())

    def get_element_pv(
        self, element, groupname, create=True
    ) -> AppliedPropertyValueGroup:
        """Return the named PVMT group on ``element``.

        Parameters
        ----------
        element
            An LXML element with property value groups.
        groupname
            The fully qualified name of the property value group, in the
            format "domain.group".
        create
            True to create (apply) the group if necessary.
        """
        if "." not in groupname:
            raise ValueError(
                "Please specify the fully qualified property value group name"
            )

        for child in element.iterchildren("ownedPropertyValueGroups"):
            if child.attrib["name"] == groupname:
                break
        else:
            if not create:
                raise exceptions.GroupNotAppliedError(
                    f"Property value group {groupname} was not "
                    "applied to this element"
                ) from None
            child = AppliedPropertyValueGroup.applyto(self, element, groupname)

        return AppliedPropertyValueGroup(self, child, model=self.model)

    def _extract_value(self, element):
        return Domain(element, parent=self)

    def _prepare_child(self, element, key):
        raise NotImplementedError(
            "Adding domains to the model is not implemented yet"
        )

    def _insert_value(self, element, value):
        raise NotImplementedError("Modifying domains is not implemented yet")


def load_pvmt_from_model(model):
    """Load the Property Value management extension for the given model.

    This function is the main entry point for the ``pvmt`` module.  It
    should be called after constructing a ``MelodyLoader`` instance on
    the model file.  It will return a ``PVMTExtension`` object, which
    can be used to easily access the property values of the model given
    during intialization.
    """
    pkgs = model.xpath(
        XPTH_FIND_BY_XTYPE.format(X_PVMT), namespaces=_n.NAMESPACES
    )
    if not pkgs:
        raise ValueError("Provided model does not have a PropertyValuePkg")
    return PVMTExtension(pkgs[0], model)
