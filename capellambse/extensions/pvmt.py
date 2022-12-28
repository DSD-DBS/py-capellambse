# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Property Value Management extension for CapellaMBSE."""
from __future__ import annotations

import typing as t

from lxml import etree

import capellambse
import capellambse.model.common as c
import capellambse.pvmt.exceptions as pvexc


class PropertyValueProxy:
    # pylint: disable=line-too-long
    """Provides access to an element's property values.

    Example for accessing property values on any object that has pvmt::

        >>> model.la.all_functions[0].pvmt['domain.group.property']
        'property'
        >>> model.la.all_functions[0].pvmt['domain.group']
        <pvmt.AppliedPropertyValueGroup "domain.group"(abcdef01-2345-6789-abcd-ef0123456789)>

    .. note::
        Access is only given if the PVMT Extension is successfully
        loaded on loading the model with the :class:`MelodyModel`.
    """
    # pylint: enable=line-too-long

    _model: capellambse.MelodyModel
    _element: etree._Element

    @classmethod
    def from_model(
        cls, model: capellambse.MelodyModel, element: etree._Element
    ) -> PropertyValueProxy:
        """Create a PropertyValueProxy for an element."""
        if not hasattr(model, "_pvext") or model._pvext is None:
            raise RuntimeError("Cannot access PVMT: extension is not loaded")

        self = cls.__new__(cls)
        self._model = model
        self._element = element
        return self

    def __init__(self, **kw: t.Any) -> None:
        raise TypeError("Cannot create PropertyValueProxy this way")

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._element is other._element

    def __getitem__(self, key):
        path = key.split(".")
        if len(path) < 1 or len(path) > 3:
            raise ValueError(
                "Provide a name as `domain`, `domain.group` or"
                " `domain.group.prop`"
            )

        domain = _PVMTDomain(self._model, self._element, path[0])
        if len(path) == 1:
            return domain
        else:
            return domain[".".join(path[1:])]


class _PVMTDomain:
    def __init__(
        self,
        model: capellambse.MelodyModel,
        element: etree._Element,
        domain: str,
    ):
        self._model = model
        self._element = element
        self._domain = domain

    def __getitem__(self, key):
        path = key.split(".")
        if len(path) < 1 or len(path) > 2:
            raise ValueError("Provide a name as `group` or `group.prop`")

        try:
            pvgroup = self._model._pvext.get_element_pv(
                self._element, f"{self._domain}.{path[0]}", create=False
            )
        except pvexc.GroupNotAppliedError:
            return None

        if len(path) == 1:
            return pvgroup
        else:
            return pvgroup[path[1]]

    def __repr__(self) -> str:
        return f"<PVMTDomain {self._domain!r} on {self._model!r}>"


def init() -> None:
    c.set_accessor(
        c.GenericElement, "pvmt", c.AlternateAccessor(PropertyValueProxy)
    )
