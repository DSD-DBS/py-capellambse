# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Object-level managed property values."""

from __future__ import annotations

__all__ = ["ObjectPVMT"]

import typing as t

import markupsafe
import typing_extensions as te
from lxml import etree

import capellambse
import capellambse.model as m
from capellambse.metamodel import capellacore

from . import _config

e = markupsafe.escape


class ObjectPVMT:
    """Provides access to managed property values on an element.

    Managed property values can be accessed in different ways.

    1. The simplest way is to treat the 'pvmt' attribute like a
       dictionary, and assign and retrieve property values directly with
       subscripting syntax. To do this, provide the "path" to the
       property value as 'domain.group.property', like this:

       >>> obj = model.by_uuid("08e02248-504d-4ed8-a295-c7682a614f66")
       >>> obj.pvmt["DarkMagic.Power.Max"]
       1600
       >>> obj.pvmt["DarkMagic.Power.Max"] = 2000
       >>> obj.pvmt["DarkMagic.Power.Max"]
       2000

    2. It's also possible to retrieve a managed group with the same
       syntax, by omitting the 'property' part of the path. The
       resulting object can be used like a dictionary to access the
       property values.

       >>> power = obj.pvmt["DarkMagic.Power"]
       >>> power["Max"]
       2000
    """

    _model: capellambse.MelodyModel
    _element: etree._Element
    _constructed: bool

    owner = m.AlternateAccessor(m.ModelElement)

    @property
    def groupdefs(self) -> m.ElementList[_config.ManagedGroup]:
        groups = self._model.pvmt.domains.map("groups")
        return groups.filter(lambda i: i.applies_to(self.owner))

    @property
    def applied_groups(self) -> m.ElementList[capellacore.PropertyValueGroup]:
        elms: list[etree._Element] = []
        groupdefs = self.owner.property_value_groups
        for group in groupdefs:
            assert isinstance(group, capellacore.PropertyValueGroup)
            try:
                domain, groupname = group.name.split(".")
            except ValueError:
                continue
            try:
                groupdef = self._model.pvmt.domains[domain].groups[groupname]
            except KeyError:
                continue
            if not groupdef.applies_to(self.owner):
                continue
            elms.append(group._element)

        return m.ElementList(self._model, elms, capellacore.PropertyValueGroup)

    def __init__(self, *_a: t.Any, **_k: t.Any) -> None:
        raise TypeError(f"Cannot instantiate {type(self).__name__} directly")

    @classmethod
    def from_model(
        cls, model: capellambse.MelodyModel, element: etree._Element
    ) -> te.Self:
        """Wrap a model element for accessing its applied PVMT."""
        self = cls.__new__(cls)
        self._model = model
        self._element = element
        self._constructed = True
        return self

    def __getitem__(self, key: str) -> t.Any:
        path = key.split(".")
        if not 2 <= len(path) <= 3:
            raise ValueError("Provide name as 'dom.group' or 'dom.group.prop'")

        domain, groupname, *_ = path
        try:
            groupdef = self._model.pvmt.domains[domain].groups[groupname]
        except KeyError:
            raise KeyError(
                f"Domain or group not found: {domain}.{groupname}"
            ) from None

        group = groupdef.apply(self.owner)
        if len(path) < 3:
            return group
        return group.property_values[path[2]]

    def __setitem__(self, key: str, value: t.Any) -> None:
        path = key.split(".")
        if len(path) != 3:
            raise ValueError("Specify property to set as 'domain.group.prop'")
        dom, group, prop = path
        groupdef = self._model.pvmt.domains[dom].groups[group]
        groupdef.apply(self.owner).property_values[prop] = value

    def _short_repr_(self) -> str:
        return f"<Property Value Management for {self.owner._short_repr_()}>"

    def __repr__(self) -> str:
        fragments: list[str] = [self._short_repr_()]

        for group in self.groupdefs:
            try:
                groupobj = self[group.fullname]
            except KeyError:
                groupobj = None

            fragments.append(f'\nGroup "{group.fullname}"')
            if groupobj is None:
                fragments.append(" (not applied)")
                fragments.extend(
                    f"\n  - {prop.name}: (not applied)"
                    for prop in group.property_values
                )
            else:
                for prop in group.property_values:
                    fragments.append(f"\n  - {prop.name}: ")
                    if hasattr(prop.value, "_short_repr_"):
                        fragments.append(prop.value._short_repr_())
                    else:
                        fragments.append(repr(prop.value))

        return "".join(fragments)

    def _short_html_(self) -> markupsafe.Markup:
        return markupsafe.Markup(
            f"Property Value Management for {self.owner._short_html_()}"
        )

    def __html__(self) -> markupsafe.Markup:
        fragments: list[str] = [
            "<h1>Property Value Management</h1><p>Owner: ",
            self.owner._short_html_(),
            "</p><table><tbody>",
        ]

        for group in self.groupdefs:
            try:
                groupobj = self[group.fullname]
            except KeyError:
                groupobj = None

            fragments.append('<tr><th colspan="3" style="text-align:left;">')
            fragments.append(group._short_html_())
            if groupobj is None:
                fragments.append(" <em>(not applied)</em>")
            fragments.append("</th></tr>")
            for prop in group.property_values:
                if groupobj is None:
                    actual = "<em>not applied</em>"
                else:
                    actual_val = groupobj.property_values[prop.name]
                    if hasattr(actual_val, "_short_html_"):
                        actual = actual_val._short_html_()
                    else:
                        actual = e(actual_val)
                if hasattr(prop.value, "_short_html_"):
                    default = prop.value._short_html_()
                else:
                    default = e(prop.value)
                fragments.append(
                    "<tr>"
                    f"<td>{e(prop.name)}</td>"
                    f"<td>{actual}</td>"
                    f"<td>{default}</td>"
                    "</tr>"
                )

        fragments.append(
            "</tbody><thead><tr>"
            "<th>Property</th>"
            "<th>Value</th>"
            "<th>Default</th>"
            "</tr></thead></table>"
        )

        return markupsafe.Markup("".join(fragments))

    def _repr_html_(self) -> str:
        return self.__html__()
