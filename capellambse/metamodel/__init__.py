# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from . import (
    capellacommon,
    capellacore,
    capellamodeller,
    cs,
    fa,
    interaction,
    la,
    modellingcore,
    oa,
    pa,
    sa,
)

import capellambse.model as m  # isort: skip

m.set_accessor(
    capellacommon.State,
    "functions",
    m.ReferenceSearchingAccessor(
        (
            oa.OperationalActivity,
            sa.SystemFunction,
            la.LogicalFunction,
            pa.PhysicalFunction,
        ),
        "available_in_states",
        aslist=m.ElementList,
    ),
)
m.set_accessor(
    m.GenericElement,
    "property_value_packages",
    m.DirectProxyAccessor(
        capellacore.PropertyValuePkg,
        aslist=m.ElementList,
        mapkey="name",
    ),
)

del m
