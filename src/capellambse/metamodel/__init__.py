# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Metamodel definitions for Capella models."""

from . import activity as activity
from . import behavior as behavior
from . import capellacommon as capellacommon
from . import capellacore as capellacore
from . import capellamodeller as capellamodeller
from . import cs as cs
from . import epbs as epbs
from . import fa as fa
from . import information as information
from . import interaction as interaction
from . import la as la
from . import libraries as libraries
from . import modellingcore as modellingcore
from . import oa as oa
from . import pa as pa
from . import pa_deployment as pa_deployment
from . import sa as sa

import capellambse.model as m  # isort: skip

capellacommon.State.functions = m.Backref(
    (
        oa.OperationalActivity,
        sa.SystemFunction,
        la.LogicalFunction,
        pa.PhysicalFunction,
    ),
    "available_in_states",
)
m.ModelElement.property_value_pkgs = m.DirectProxyAccessor(
    capellacore.PropertyValuePkg,
    aslist=m.ElementList,
    mapkey="name",
)

del m
