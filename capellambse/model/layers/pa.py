# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Tools for the Physical Architecture layer.

.. diagram:: [CDB] Physical Architecture [Ontology]
"""
from __future__ import annotations

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

    owner: c.Accessor[PhysicalComponent]
    realized_logical_functions = c.LinkAccessor[la.LogicalFunction](
        None,  # FIXME fill in tag
        fa.FunctionRealization,
        aslist=c.ElementList,
        attr="targetElement",
    )


@c.xtype_handler(XT_ARCH)
class PhysicalFunctionPkg(c.GenericElement):
    """A logical component package."""

    _xmltag = "ownedFunctionPkg"

    functions = c.DirectProxyAccessor(PhysicalFunction, aslist=c.ElementList)

    packages: c.Accessor


@c.xtype_handler(XT_ARCH)
class PhysicalComponent(cs.Component):
    """A physical component on the Physical Architecture layer."""

    _xmltag = "ownedPhysicalComponents"

    nature = c.EnumAttributeProperty("nature", modeltypes.Nature)
    kind = c.EnumAttributeProperty(
        "kind", modeltypes.Kind, default=modeltypes.Kind.UNSET
    )

    allocated_functions = c.LinkAccessor[PhysicalFunction](
        "ownedFunctionalAllocation",
        fa.XT_FCALLOC,
        aslist=c.ElementList,
        attr="targetElement",
    )
    realized_logical_components = c.LinkAccessor[la.LogicalComponent](
        None,  # FIXME fill in tag
        cs.ComponentRealization,
        aslist=c.ElementList,
        attr="targetElement",
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

    functions = c.DeprecatedAccessor[PhysicalFunction]("allocated_functions")


@c.xtype_handler(XT_ARCH)
class PhysicalComponentPkg(c.GenericElement):
    """A logical component package."""

    _xmltag = "ownedPhysicalComponentPkg"

    components = c.DirectProxyAccessor(PhysicalComponent, aslist=c.ElementList)
    exchanges = c.DirectProxyAccessor(
        fa.ComponentExchange, aslist=c.ElementList
    )
    state_machines = c.DirectProxyAccessor(
        capellacommon.StateMachine, aslist=c.ElementList
    )

    packages: c.Accessor


@c.xtype_handler(None)
class PhysicalArchitecture(crosslayer.BaseArchitectureLayer):
    """Provides access to the Physical Architecture layer of the model."""

    root_component = c.AttributeMatcherAccessor(
        PhysicalComponent,
        attributes={"is_actor": False},
        rootelem=PhysicalComponentPkg,
    )
    root_function = c.DirectProxyAccessor(
        PhysicalFunction, rootelem=PhysicalFunctionPkg
    )

    function_package = c.DirectProxyAccessor(PhysicalFunctionPkg)
    component_package = c.DirectProxyAccessor(PhysicalComponentPkg)
    capability_package = c.DirectProxyAccessor(la.CapabilityRealizationPkg)

    all_functions = c.DeepProxyAccessor(
        PhysicalFunction,
        aslist=c.ElementList,
        rootelem=PhysicalFunctionPkg,
    )
    all_capabilities = c.DeepProxyAccessor(
        la.CapabilityRealization, aslist=c.ElementList
    )
    all_components = c.DeepProxyAccessor(
        PhysicalComponent, aslist=c.ElementList
    )
    all_actors = property(
        lambda self: self._model.search(PhysicalComponent).by_is_actor(True)
    )

    all_function_exchanges = c.DeepProxyAccessor(
        fa.FunctionalExchange,
        aslist=c.ElementList,
        rootelem=[PhysicalFunctionPkg, PhysicalFunction],
    )
    all_physical_paths = c.DeepProxyAccessor(
        cs.PhysicalPath,
        aslist=c.ElementList,
        rootelem=PhysicalComponentPkg,
    )
    all_component_exchanges = c.DeepProxyAccessor(
        fa.ComponentExchange,
        aslist=c.ElementList,
        rootelem=PhysicalComponentPkg,
    )

    all_physical_exchanges = c.DeepProxyAccessor(
        fa.FunctionalExchange,
        aslist=c.ElementList,
        rootelem=[PhysicalFunctionPkg, PhysicalFunction],
    )
    all_physical_links = c.DeepProxyAccessor(
        cs.PhysicalLink, aslist=c.ElementList
    )

    diagrams = diagram.DiagramAccessor(
        "Physical Architecture", cacheattr="_MelodyModel__diagram_cache"
    )


c.set_accessor(
    la.LogicalComponent,
    "realizing_physical_components",
    c.ReferenceSearchingAccessor(
        PhysicalComponent, "realized_logical_components", aslist=c.ElementList
    ),
)
c.set_accessor(
    la.LogicalFunction,
    "realizing_physical_functions",
    c.ReferenceSearchingAccessor(
        PhysicalFunction, "realized_logical_functions", aslist=c.ElementList
    ),
)
c.set_accessor(
    PhysicalComponent,
    "deploying_components",
    c.ReferenceSearchingAccessor(
        PhysicalComponent, "deployed_components", aslist=c.ElementList
    ),
)
c.set_accessor(
    PhysicalFunction,
    "owner",
    c.ReferenceSearchingAccessor(PhysicalComponent, "allocated_functions"),
)
c.set_accessor(
    PhysicalFunction,
    "packages",
    c.DirectProxyAccessor(PhysicalFunctionPkg, aslist=c.ElementList),
)
c.set_self_references(
    (PhysicalComponent, "owned_components"),
    (PhysicalComponentPkg, "packages"),
    (PhysicalFunction, "functions"),
    (PhysicalFunctionPkg, "packages"),
)
