# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
"""Model-level PVMT configuration."""
from __future__ import annotations

__all__ = [
    "ManagedDomain",
    "PVMTConfiguration",
]

import logging
import typing as t

from lxml import etree

import capellambse
import capellambse.model.common as c
from capellambse.model.crosslayer.information import capellacore

LOGGER = logging.getLogger(__name__)


class ManagedDomain(c.GenericElement):
    """A "domain" in the property value management extension."""


class PVMTConfiguration:
    """Provides access to the model-wide PVMT configuration."""

    _model: capellambse.MelodyModel
    _element: etree._Element

    domains = c.DirectProxyAccessor(
        ManagedDomain, capellacore.PropertyValuePkg, aslist=c.ElementList
    )

    @classmethod
    def from_model(
        cls, model: capellambse.MelodyModel, element: etree._Element
    ) -> PVMTConfiguration:
        """Wrap the model for accessing its PVMT configuration."""
        self = cls.__new__(cls)
        self._model = model
        self._element = element
        return self


class PVMTConfigurationAccessor(c.Accessor[PVMTConfiguration]):
    """Finds the model-wide PVMT configuration and provides access to it."""

    @t.overload
    def __get__(self: c.A, obj: None, objtype: type[t.Any]) -> c.A:
        ...

    @t.overload
    def __get__(
        self, obj: c.ModelObject, objtype: type[c.ModelObject] | None = ...
    ) -> PVMTConfiguration:
        ...

    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:  # pragma: no cover
            return self

        try:
            ext = obj.property_value_packages.by_name("EXTENSIONS")
        except KeyError:
            LOGGER.debug("Creating EXTENSIONS package")
            ext = obj.property_value_packages.create(name="EXTENSIONS")
        return PVMTConfiguration.from_model(obj, ext._element)
