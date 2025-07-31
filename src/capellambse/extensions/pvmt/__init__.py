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
    pkgs = model.project.property_value_pkgs
    assert pkgs.is_coupled()
    extension_pkgs = pkgs.by_name("EXTENSIONS", single=False)
    if not extension_pkgs:
        LOGGER.debug("Creating EXTENSIONS package")
        ext = pkgs.create(name="EXTENSIONS")
    else:
        ext = pkgs[0]
        if len(extension_pkgs) > 1:
            LOGGER.warning(
                (
                    "Model contains %d PVMT configuration packages,"
                    " only the first one will be used"
                ),
                len(extension_pkgs),
            )
    assert isinstance(ext, mm.capellacore.PropertyValuePkg)
    return m.wrap_xml(model, ext._element, type=PVMTConfiguration)


def init() -> None:
    """Initialize the PVMT extension."""
    m.MelodyModel.pvmt = property(_get_pvmt_configuration)  # type: ignore[attr-defined]
    m.ModelElement.pvmt = m.AlternateAccessor(ObjectPVMT)


if not t.TYPE_CHECKING:
    from ._config import __all__ as _all1
    from ._objects import __all__ as _all2

    __all__ = [*_all1, *_all2]
