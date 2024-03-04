# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

# Eagerly initialize all submodules, so that they are known at type checking
# time. This allows type checking when only the 'metamodel' package was
# imported, without explicitly importing any submodules, e.g.:
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
    requirement,
    sa,
)
