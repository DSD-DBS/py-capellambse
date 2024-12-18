# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from . import capellacommon as capellacommon
from . import capellacore as capellacore
from . import capellamodeller as capellamodeller
from . import cs as cs
from . import fa as fa
from . import interaction as interaction
from . import la as la
from . import modellingcore as modellingcore
from . import oa as oa
from . import pa as pa
from . import sa as sa

import capellambse.model as m  # isort: skip

m.set_accessor(
    capellacommon.State,
    "functions",
    m.Backref(
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
    m.ModelElement,
    "property_value_packages",
    m.DirectProxyAccessor(
        capellacore.PropertyValuePkg,
        aslist=m.ElementList,
        mapkey="name",
    ),
)

del m
