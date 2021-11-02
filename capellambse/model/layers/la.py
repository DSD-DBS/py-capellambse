# Copyright 2021 DB Netz AG
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tools for the Logical Architecture layer.

.. diagram:: [CDB] LA ORM
"""
from __future__ import annotations

import operator

from .. import common as c
from .. import crosslayer, diagram
from ..crosslayer import capellacommon, capellacore, cs, fa, interaction
from . import ctx

XT_ARCH = "org.polarsys.capella.core.data.la:LogicalArchitecture"


@c.xtype_handler(XT_ARCH)
class LogicalFunction(c.GenericElement):
    """A logical function on the Logical Architecture layer."""

    _xmltag = "ownedLogicalFunctions"

    inputs = c.ProxyAccessor(fa.FunctionInputPort, aslist=c.ElementList)
    outputs = c.ProxyAccessor(fa.FunctionOutputPort, aslist=c.ElementList)
    is_leaf = property(lambda self: not self.functions)
    realized_system_functions = c.ProxyAccessor(
        ctx.SystemFunction,
        fa.FunctionRealization,
        aslist=c.ElementList,
        follow="targetElement",
    )

    owner: c.Accessor
    functions: c.Accessor


@c.xtype_handler(XT_ARCH)
class LogicalFunctionPkg(c.GenericElement):
    """A logical function package."""

    _xmltag = "ownedFunctionPkg"

    functions = c.ProxyAccessor(LogicalFunction, aslist=c.ElementList)

    packages: c.Accessor


@c.xtype_handler(XT_ARCH)
class LogicalComponent(cs.Component):
    """A logical component on the Logical Architecture layer."""

    _xmltag = "ownedLogicalComponents"

    functions = c.ProxyAccessor(
        LogicalFunction,
        fa.XT_FCALLOC,
        aslist=c.ElementList,
        follow="targetElement",
    )
    realized_components = c.ProxyAccessor(
        ctx.SystemComponent,
        cs.ComponentRealization,
        aslist=c.ElementList,
        follow="targetElement",
    )
    ports = c.ProxyAccessor(fa.ComponentPort, aslist=c.ElementList)

    components: c.Accessor


@c.xtype_handler(XT_ARCH)
class LogicalComponentPkg(c.GenericElement):
    """A logical component package."""

    _xmltag = "ownedLogicalComponentPkg"

    components = c.ProxyAccessor(LogicalComponent, aslist=c.ElementList)
    state_machines = c.ProxyAccessor(
        capellacommon.StateMachine, aslist=c.ElementList
    )

    packages: c.Accessor


@c.xtype_handler(XT_ARCH)
class CapabilityRealization(c.GenericElement):
    """A capability."""

    _xmltag = "ownedCapabilityRealizations"

    owned_chains = c.ProxyAccessor(fa.FunctionalChain, aslist=c.ElementList)
    involved_functions = c.ProxyAccessor(
        LogicalFunction,
        interaction.XT_CAP2ACT,
        aslist=c.ElementList,
        follow="involved",
    )
    involved_chains = c.ProxyAccessor(
        fa.FunctionalChain,
        interaction.XT_CAP2PROC,
        aslist=c.ElementList,
        follow="involved",
    )
    involved_components = c.ProxyAccessor(
        LogicalComponent,
        ctx.XT_CAP_INV,
        follow="involved",
        aslist=c.MixedElementList,
    )
    realized_capabilities = c.ProxyAccessor(
        ctx.Capability,
        interaction.XT_CAP_REAL,
        follow="targetElement",
        aslist=c.ElementList,
    )

    postcondition = c.AttrProxyAccessor(
        capellacore.Constraint, "postCondition"
    )
    precondition = c.AttrProxyAccessor(capellacore.Constraint, "preCondition")
    scenarios = c.ProxyAccessor(interaction.Scenario, aslist=c.ElementList)
    states = c.AttrProxyAccessor(
        capellacommon.State, "availableInStates", aslist=c.ElementList
    )

    packages: c.Accessor


@c.xtype_handler(XT_ARCH)
class CapabilityRealizationPkg(c.GenericElement):
    """A capability package that can hold capabilities."""

    _xmltag = "ownedAbstractCapabilityPkg"

    capabilities = c.ProxyAccessor(CapabilityRealization, aslist=c.ElementList)

    packages: c.Accessor


class LogicalArchitecture(crosslayer.BaseArchitectureLayer):
    """Provides access to the LogicalArchitecture layer of the model."""

    root_component = c.AttributeMatcherAccessor(
        LogicalComponent,
        attributes={"is_actor": False},
        rootelem=LogicalComponentPkg,
    )
    root_function = c.ProxyAccessor(
        LogicalFunction, rootelem=LogicalFunctionPkg
    )

    function_package = c.ProxyAccessor(LogicalFunctionPkg)
    component_package = c.ProxyAccessor(LogicalComponentPkg)
    capability_package = c.ProxyAccessor(CapabilityRealizationPkg)

    diagrams = diagram.DiagramAccessor(
        "Logical Architecture", cacheattr="_MelodyModel__diagram_cache"
    )
    actor_exchanges = c.ProxyAccessor(
        fa.ComponentExchange,
        aslist=c.ElementList,
        rootelem=LogicalComponentPkg,
    )
    component_exchanges = c.ProxyAccessor(
        fa.ComponentExchange,
        aslist=c.ElementList,
        rootelem=[LogicalComponentPkg, LogicalComponent],
        deep=True,
    )

    all_function_exchanges = c.ProxyAccessor(
        fa.FunctionalExchange,
        aslist=c.ElementList,
        rootelem=[LogicalFunctionPkg, LogicalFunction],
        deep=True,
    )
    all_component_exchanges = c.ProxyAccessor(
        fa.ComponentExchange,
        aslist=c.ElementList,
        deep=True,
    )
    all_components = c.ProxyAccessor(  # maybe this should exclude .is_actor
        LogicalComponent, aslist=c.ElementList, deep=True
    )
    all_actors: c.CustomAccessor[LogicalComponent] = c.CustomAccessor(  # type: ignore[misc]
        LogicalComponent,
        operator.attrgetter("all_components"),
        elmmatcher=lambda x, _: x.is_actor,  # type: ignore[attr-defined]
        aslist=c.ElementList,
    )
    all_functions = c.ProxyAccessor(
        LogicalFunction,
        aslist=c.ElementList,
        rootelem=LogicalFunctionPkg,
        deep=True,
    )
    all_capabilities = c.ProxyAccessor(
        CapabilityRealization, deep=True, aslist=c.ElementList
    )


c.set_accessor(
    LogicalFunction,
    "owner",
    c.CustomAccessor(
        LogicalComponent,
        operator.attrgetter("_model.la.all_components"),
        matchtransform=operator.attrgetter("functions"),
    ),
)
c.set_accessor(
    ctx.Capability,
    "realizing_capabilities",
    c.CustomAccessor(
        CapabilityRealization,
        operator.attrgetter("_model.la.all_capabilities"),
        matchtransform=operator.attrgetter("realized_capabilities"),
        aslist=c.ElementList,
    ),
)
c.set_accessor(
    ctx.SystemComponent,
    "realizing_logical_components",
    c.CustomAccessor(
        LogicalComponent,
        operator.attrgetter("_model.la.all_components"),
        matchtransform=operator.attrgetter("realized_components"),
        aslist=c.ElementList,
    ),
)
c.set_accessor(
    ctx.SystemFunction,
    "realizing_logical_functions",
    c.CustomAccessor(
        LogicalFunction,
        operator.attrgetter("_model.la.all_functions"),
        matchtransform=operator.attrgetter("realized_system_functions"),
        aslist=c.ElementList,
    ),
)
c.set_self_references(
    (LogicalComponent, "components"),
    (LogicalComponentPkg, "packages"),
    (LogicalFunction, "functions"),
    (LogicalFunctionPkg, "packages"),
)
