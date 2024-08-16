# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Property Value Management extension for |project|."""

from __future__ import annotations

import logging
import typing as t

import capellambse.metamodel as mm
import capellambse.model as m

from ._config import *
from ._objects import *

LOGGER = logging.getLogger(__name__)


def _get_pvmt_configuration(model: m.MelodyModel) -> PVMTConfiguration:
    pkgs = model.project.property_value_packages
    assert pkgs.is_coupled()
    try:
        ext = pkgs.by_name("EXTENSIONS")
    except KeyError:
        LOGGER.debug("Creating EXTENSIONS package")
        ext = pkgs.create(name="EXTENSIONS")
    assert isinstance(ext, mm.capellacore.PropertyValuePkg)
    return PVMTConfiguration.from_model(model, ext._element)


def init() -> None:
    """Initialize the PVMT extension."""
    m.MelodyModel.pvmt = property(_get_pvmt_configuration)  # type: ignore[attr-defined]
    m.set_accessor(m.ModelElement, "pvmt", m.AlternateAccessor(ObjectPVMT))


if not t.TYPE_CHECKING:
    from ._config import __all__ as _all1
    from ._objects import __all__ as _all2

    __all__ = [*_all1, *_all2]
