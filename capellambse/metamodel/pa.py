# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Tools for the Physical Architecture layer.

.. diagram:: [CDB] Physical Architecture [Ontology]
"""

from __future__ import annotations

import capellambse.model as m

from . import capellacommon, cs, fa, la, modeltypes


@m.xtype_handler(None)
class PhysicalFunction(fa.Function):
    """A physical function on the Physical Architecture layer."""

    owner: m.Accessor[PhysicalComponent]
    realized_logical_functions = m.TypecastAccessor(
        la.LogicalFunction, "realized_functions"
    )


@m.xtype_handler(None)
class PhysicalFunctionPkg(m.ModelElement):
    """A logical component package."""

    _xmltag = "ownedFunctionPkg"

    functions = m.Containment(
        "ownedPhysicalFunctions", PhysicalFunction, aslist=m.ElementList
    )

    packages: m.Accessor
    categories = m.DirectProxyAccessor(
        fa.ExchangeCategory, aslist=m.ElementList
    )


@m.xtype_handler(None)
class PhysicalComponent(cs.Component):
    """A physical component on the Physical Architecture layer."""

    _xmltag = "ownedPhysicalComponents"

    nature = m.EnumPOD(
        "nature", modeltypes.PhysicalComponentNature, default="UNSET"
    )
    kind = m.EnumPOD("kind", modeltypes.PhysicalComponentKind, default="UNSET")

    allocated_functions = m.Allocation[PhysicalFunction](
        "ownedFunctionalAllocation",
        fa.ComponentFunctionalAllocation,
        aslist=m.ElementList,
        attr="targetElement",
        backattr="sourceElement",
    )
    realized_logical_components = m.TypecastAccessor(
        la.LogicalComponent,
        "realized_components",
    )

    owned_components: m.Accessor
    deploying_components: m.Accessor

    @property
    def deployed_components(
        self,
    ) -> m.ElementList[PhysicalComponent]:
        items = [
            cmp.type._element
            for part in self.parts
            for cmp in part.deployed_parts
        ]
        return m.ElementList(self._model, items, PhysicalComponent)

    @property
    def components(self) -> m.ElementList[PhysicalComponent]:
        return self.deployed_components + self.owned_components


@m.xtype_handler(None)
class PhysicalComponentPkg(m.ModelElement):
    """A logical component package."""

    _xmltag = "ownedPhysicalComponentPkg"

    components = m.DirectProxyAccessor(PhysicalComponent, aslist=m.ElementList)
    exchanges = m.DirectProxyAccessor(
        fa.ComponentExchange, aslist=m.ElementList
    )
    state_machines = m.DirectProxyAccessor(
        capellacommon.StateMachine, aslist=m.ElementList
    )

    packages: m.Accessor
    exchange_categories = m.DirectProxyAccessor(
        fa.ComponentExchangeCategory, aslist=m.ElementList
    )


@m.xtype_handler(None)
class PhysicalArchitecture(cs.ComponentArchitecture):
    """Provides access to the Physical Architecture layer of the model."""

    root_component = m.AttributeMatcherAccessor(
        PhysicalComponent,
        attributes={"is_actor": False},
        rootelem=PhysicalComponentPkg,
    )
    root_function = m.DirectProxyAccessor(
        PhysicalFunction, rootelem=PhysicalFunctionPkg
    )

    function_package = m.DirectProxyAccessor(PhysicalFunctionPkg)
    component_package = m.DirectProxyAccessor(PhysicalComponentPkg)
    capability_package = m.DirectProxyAccessor(la.CapabilityRealizationPkg)

    all_functions = m.DeepProxyAccessor(
        PhysicalFunction,
        aslist=m.ElementList,
        rootelem=PhysicalFunctionPkg,
    )
    all_capabilities = m.DeepProxyAccessor(
        la.CapabilityRealization, aslist=m.ElementList
    )
    all_components = m.DeepProxyAccessor(
        PhysicalComponent, aslist=m.ElementList
    )
    all_actors = property(
        lambda self: self._model.search(PhysicalComponent).by_is_actor(True)
    )

    all_function_exchanges = m.DeepProxyAccessor(
        fa.FunctionalExchange,
        aslist=m.ElementList,
        rootelem=[PhysicalFunctionPkg, PhysicalFunction],
    )
    all_physical_paths = m.DeepProxyAccessor(
        cs.PhysicalPath,
        aslist=m.ElementList,
        rootelem=PhysicalComponentPkg,
    )
    all_component_exchanges = m.DeepProxyAccessor(
        fa.ComponentExchange,
        aslist=m.ElementList,
        rootelem=PhysicalComponentPkg,
    )

    all_physical_exchanges = m.DeepProxyAccessor(
        fa.FunctionalExchange,
        aslist=m.ElementList,
        rootelem=[PhysicalFunctionPkg, PhysicalFunction],
    )
    all_physical_links = m.DeepProxyAccessor(
        cs.PhysicalLink, aslist=m.ElementList
    )
    all_functional_chains = property(
        lambda self: self._model.search(fa.FunctionalChain, below=self)
    )

    diagrams = m.DiagramAccessor(
        "Physical Architecture", cacheattr="_MelodyModel__diagram_cache"
    )


m.set_accessor(
    la.LogicalComponent,
    "realizing_physical_components",
    m.Backref(
        PhysicalComponent, "realized_logical_components", aslist=m.ElementList
    ),
)
m.set_accessor(
    la.LogicalFunction,
    "realizing_physical_functions",
    m.Backref(
        PhysicalFunction, "realized_logical_functions", aslist=m.ElementList
    ),
)
m.set_accessor(
    PhysicalComponent,
    "deploying_components",
    m.Backref(PhysicalComponent, "deployed_components", aslist=m.ElementList),
)
m.set_accessor(
    PhysicalFunction,
    "owner",
    m.Backref(PhysicalComponent, "allocated_functions"),
)
m.set_accessor(
    PhysicalFunction,
    "packages",
    m.DirectProxyAccessor(PhysicalFunctionPkg, aslist=m.ElementList),
)
m.set_self_references(
    (PhysicalComponent, "owned_components"),
    (PhysicalComponentPkg, "packages"),
    (PhysicalFunction, "functions"),
    (PhysicalFunctionPkg, "packages"),
)
