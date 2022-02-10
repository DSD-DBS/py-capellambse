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
"""Tools for the Physical Architecture layer.

.. diagram:: [CDB] Physical Architecture [Ontology]
"""
from __future__ import annotations

import operator

from capellambse.loader import xmltools

from .. import common as c
from .. import crosslayer, diagram, modeltypes
from ..crosslayer import capellacommon, cs, fa
from . import la

XT_ARCH = "org.polarsys.capella.core.data.pa:PhysicalArchitecture"

XT_LA_COMP_REAL = (
    "org.polarsys.capella.core.data.pa:LogicalComponentRealization"
)


@c.xtype_handler(XT_ARCH)
class PhysicalFunction(fa.Function):
    """A physical function on the Physical Architecture layer."""

    _xmltag = "ownedPhysicalFunctions"

    owner = c.CustomAccessor(
        c.GenericElement,
        operator.attrgetter("_model.pa.all_components"),
        matchtransform=operator.attrgetter("functions"),
    )
    realized_logical_functions = c.ProxyAccessor(
        la.LogicalFunction,
        fa.FunctionRealization,
        aslist=c.ElementList,
        follow="targetElement",
    )


@c.xtype_handler(XT_ARCH)
class PhysicalFunctionPkg(c.GenericElement):
    """A logical component package."""

    _xmltag = "ownedFunctionPkg"

    components = c.ProxyAccessor(PhysicalFunction, aslist=c.ElementList)

    packages: c.Accessor


@c.xtype_handler(XT_ARCH)
class PhysicalComponent(cs.Component):
    """A physical component on the Physical Architecture layer."""

    _xmltag = "ownedPhysicalComponents"

    nature = xmltools.EnumAttributeProperty(
        "_element", "nature", modeltypes.Nature
    )
    kind = xmltools.EnumAttributeProperty(
        "_element", "kind", modeltypes.Kind, default=modeltypes.Kind.UNSET
    )

    functions = c.ProxyAccessor(
        PhysicalFunction,
        fa.XT_FCALLOC,
        aslist=c.ElementList,
        follow="targetElement",
    )
    realized_logical_components = c.ProxyAccessor(
        la.LogicalComponent,
        cs.ComponentRealization,
        aslist=c.ElementList,
        follow="targetElement",
    )

    owned_components: c.Accessor
    deploying_components: c.Accessor

    @property
    def deployed_components(
        self,
    ) -> c.ElementList[PhysicalComponent]:
        items = [
            cmp.type._element
            for part in self.parts
            for cmp in part.deployed_parts
        ]
        return c.ElementList(self._model, items, PhysicalComponent)

    @property
    def components(self) -> c.ElementList[PhysicalComponent]:
        return self.deployed_components + self.owned_components


@c.xtype_handler(XT_ARCH)
class PhysicalComponentPkg(c.GenericElement):
    """A logical component package."""

    _xmltag = "ownedPhysicalComponentPkg"

    components = c.ProxyAccessor(PhysicalComponent, aslist=c.ElementList)
    state_machines = c.ProxyAccessor(
        capellacommon.StateMachine, aslist=c.ElementList
    )

    packages: c.Accessor


class PhysicalArchitecture(crosslayer.BaseArchitectureLayer):
    """Provides access to the Physical Architecture layer of the model."""

    root_component = c.AttributeMatcherAccessor(
        PhysicalComponent,
        attributes={"is_actor": False},
        rootelem=PhysicalComponentPkg,
    )
    root_function = c.ProxyAccessor(
        PhysicalComponent, rootelem=PhysicalFunctionPkg
    )

    function_package = c.ProxyAccessor(PhysicalFunctionPkg)
    component_package = c.ProxyAccessor(PhysicalComponentPkg)
    capability_package = c.ProxyAccessor(la.CapabilityRealizationPkg)

    all_functions = c.ProxyAccessor(
        PhysicalFunction,
        aslist=c.ElementList,
        rootelem=PhysicalFunctionPkg,
        deep=True,
    )
    all_capabilities = c.ProxyAccessor(
        la.CapabilityRealization, deep=True, aslist=c.ElementList
    )
    all_components = c.ProxyAccessor(
        PhysicalComponent, aslist=c.ElementList, deep=True
    )
    all_actors = property(
        lambda self: self._model.search(PhysicalComponent).by_is_actor(True)
    )

    all_function_exchanges = c.ProxyAccessor(
        fa.FunctionalExchange,
        aslist=c.ElementList,
        rootelem=[PhysicalFunctionPkg, PhysicalFunction],
        deep=True,
    )
    all_physical_paths = c.ProxyAccessor(
        cs.PhysicalPath,
        aslist=c.ElementList,
        rootelem=PhysicalComponentPkg,
        deep=True,
    )
    all_component_exchanges = c.ProxyAccessor(
        fa.ComponentExchange,
        aslist=c.ElementList,
        rootelem=PhysicalComponentPkg,
        deep=True,
    )

    all_physical_exchanges = c.ProxyAccessor(
        fa.FunctionalExchange,
        aslist=c.ElementList,
        rootelem=[PhysicalFunctionPkg, PhysicalFunction],
        deep=True,
    )
    all_physical_links = c.ProxyAccessor(
        cs.PhysicalLink, aslist=c.ElementList, deep=True
    )

    diagrams = diagram.DiagramAccessor(
        "Physical Architecture", cacheattr="_MelodyModel__diagram_cache"
    )  # type: ignore[assignment]


c.set_accessor(
    la.LogicalComponent,
    "realizing_physical_components",
    c.CustomAccessor(
        PhysicalComponent,
        operator.attrgetter("_model.pa.all_components"),
        matchtransform=operator.attrgetter("realized_logical_components"),
        aslist=c.ElementList,
    ),
)
c.set_accessor(
    la.LogicalFunction,
    "realizing_physical_functions",
    c.CustomAccessor(
        PhysicalFunction,
        operator.attrgetter("_model.pa.all_functions"),
        matchtransform=operator.attrgetter("realized_logical_functions"),
        aslist=c.ElementList,
    ),
)
c.set_accessor(
    PhysicalComponent,
    "deploying_components",
    c.CustomAccessor(
        PhysicalComponent,
        operator.attrgetter("_model.pa.all_components"),
        matchtransform=operator.attrgetter("deployed_components"),
        aslist=c.ElementList,
    ),
)
c.set_accessor(
    PhysicalFunction,
    "packages",
    c.ProxyAccessor(
        PhysicalFunctionPkg,
        aslist=c.ElementList,
    ),
)
c.set_self_references(
    (PhysicalComponent, "owned_components"),
    (PhysicalComponentPkg, "packages"),
    (PhysicalFunction, "functions"),
    (PhysicalFunctionPkg, "packages"),
)
