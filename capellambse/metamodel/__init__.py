# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Metamodel definitions for Capella models."""

__import__("warnings").warn(
    (
        f"The {__name__} module is experimental and may change at any time."
        " Productive use is not yet recommended. Use at your own risk."
    ),
    UserWarning,
    stacklevel=2,
)

# Eagerly initialize all submodules. This allows using them when only the
# 'metamodel' package was imported, without explicitly importing any
# submodules, for example:
#
#   import capellambse.metamodel as M
#   some_attr: M.la.LogicalComponent
from . import (
    activity,
    behavior,
    capellacommon,
    capellacore,
    capellamodeller,
    cs,
    epbs,
    fa,
    information,
    information_datatype,
    information_datavalue,
    interaction,
    la,
    libraries,
    modellingcore,
    modeltypes,
    namespaces,
    oa,
    pa,
    pa_deployment,
    sa,
)
