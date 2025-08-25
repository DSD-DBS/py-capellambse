# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import enum
import sys
import typing as t
import warnings

import capellambse.model as m

from . import activity, behavior, capellacore, information, modellingcore
from . import namespaces as ns

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

NS = ns.FA


# TODO Remove _AbstractExchange when removing deprecated features
class _AbstractExchange(m.ModelElement):
    if not t.TYPE_CHECKING:

        @property
        def source(self) -> m.ModelElement:
            raise TypeError(
                "AbstractExchange is deprecated and will be removed soon,"
                " use the concrete FunctionalExchange or ComponentExchange"
                " class or another common superclass instead"
            )

        @property
        def target(self) -> m.ModelElement:
            raise TypeError(
                "AbstractExchange is deprecated and will be removed soon,"
                " use the concrete FunctionalExchange or ComponentExchange"
                " class or another common superclass instead"
            )


@m.stringy_enum
@enum.unique
class ComponentExchangeKind(enum.Enum):
    """The kind of a ComponentExchange."""

    UNSET = "UNSET"
    """Communication kind is not set."""
    DELEGATION = "DELEGATION"
    """Indicates that the connector is a delegation connector."""
    ASSEMBLY = "ASSEMBLY"
    """Indicates that the connector is an assembly connector."""
    FLOW = "FLOW"
    """Describes a flow communication."""


@m.stringy_enum
@enum.unique
class ComponentPortKind(enum.Enum):
    STANDARD = "STANDARD"
    """Describes a standard port.

    A port is an interaction point between a Block or sub-Block and its
    environment that supports Exchanges with other ports.
    """
    FLOW = "FLOW"
    """Describes a flow port.

    A flow port is an interaction point through which input and/or
    output of items such as data, material, or energy may flow.
    """


@m.stringy_enum
@enum.unique
class ControlNodeKind(enum.Enum):
    OR = "OR"
    AND = "AND"
    ITERATE = "ITERATE"


@m.stringy_enum
@enum.unique
class FunctionKind(enum.Enum):
    """The kind of a Function."""

    FUNCTION = "FUNCTION"
    DUPLICATE = "DUPLICATE"
    GATHER = "GATHER"
    SELECT = "SELECT"
    SPLIT = "SPLIT"
    ROUTE = "ROUTE"


@m.stringy_enum
@enum.unique
class FunctionalChainKind(enum.Enum):
    """The kind of a Functional Chain."""

    SIMPLE = "SIMPLE"
    COMPOSITE = "COMPOSITE"
    FRAGMENT = "FRAGMENT"


@m.stringy_enum
@enum.unique
class OrientationPortKind(enum.Enum):
    """Direction of component ports."""

    UNSET = "UNSET"
    """The port orientation is undefined."""
    IN = "IN"
    """The port represents an input of the component it is used in."""
    OUT = "OUT"
    """The port represents an output of the component it is used in."""
    INOUT = "INOUT"
    """The port represents both an input and on output of the component."""


class AbstractFunctionalArchitecture(
    capellacore.ModellingArchitecture, abstract=True
):
    function_pkg = m.Single["FunctionPkg"](
        m.Containment("ownedFunctionPkg", (NS, "FunctionPkg"))
    )
    component_exchanges = m.Containment["ComponentExchange"](
        "ownedComponentExchanges", (NS, "ComponentExchange")
    )
    component_exchange_categories = m.Containment["ComponentExchangeCategory"](
        "ownedComponentExchangeCategories", (NS, "ComponentExchangeCategory")
    )
    functional_links = m.Containment["ExchangeLink"](
        "ownedFunctionalLinks", (NS, "ExchangeLink")
    )
    functional_allocations = m.Containment["ComponentFunctionalAllocation"](
        "ownedFunctionalAllocations", (NS, "ComponentFunctionalAllocation")
    )
    component_exchange_realizations = m.Containment[
        "ComponentExchangeRealization"
    ](
        "ownedComponentExchangeRealizations",
        (NS, "ComponentExchangeRealization"),
    )

    @property
    def all_functions(self) -> m.ElementList[AbstractFunction]:
        return self._model.search((NS, "AbstractFunction"), below=self)

    @property
    def all_functional_chains(self) -> m.ElementList[FunctionalChain]:
        return self._model.search((NS, "FunctionalChain"), below=self)

    @property
    def all_function_exchanges(self) -> m.ElementList[FunctionalExchange]:
        return self._model.search((NS, "FunctionalExchange"), below=self)

    if not t.TYPE_CHECKING:
        function_package = m.DeprecatedAccessor("function_pkg")


class AbstractFunctionalBlock(capellacore.ModellingBlock, abstract=True):
    functional_allocations = m.Containment["ComponentFunctionalAllocation"](
        "ownedFunctionalAllocation", (NS, "ComponentFunctionalAllocation")
    )
    allocated_functions = m.Allocation["AbstractFunction"](
        "ownedFunctionalAllocation",
        (NS, "ComponentFunctionalAllocation"),
        (NS, "AbstractFunction"),
        attr="targetElement",
        backattr="sourceElement",
    )
    component_exchanges = m.Containment["ComponentExchange"](
        "ownedComponentExchanges", (NS, "ComponentExchange")
    )
    component_exchange_categories = m.Containment["ComponentExchangeCategory"](
        "ownedComponentExchangeCategories", (NS, "ComponentExchangeCategory")
    )
    in_exchange_links = m.Association["ExchangeLink"](
        (NS, "ExchangeLink"), "inExchangeLinks"
    )
    out_exchange_links = m.Association["ExchangeLink"](
        (NS, "ExchangeLink"), "outExchangeLinks"
    )


class FunctionPkg(capellacore.Structure, abstract=True):
    functional_links = m.Containment["ExchangeLink"](
        "ownedFunctionalLinks", (NS, "ExchangeLink")
    )
    exchanges = m.Containment["FunctionalExchangeSpecification"](
        "ownedExchanges", (NS, "FunctionalExchangeSpecification")
    )
    exchange_specification_realizations = m.Containment[
        "ExchangeSpecificationRealization"
    ](
        "ownedExchangeSpecificationRealizations",
        (NS, "ExchangeSpecificationRealization"),
    )
    realized_exchange_specifications = m.Allocation["ExchangeSpecification"](
        "ownedExchangeSpecificationRealizations",
        (NS, "ExchangeSpecificationRealization"),
        (NS, "ExchangeSpecification"),
        attr="targetElement",
        backattr="sourceElement",
    )
    categories = m.Containment["ExchangeCategory"](
        "ownedCategories", (NS, "ExchangeCategory")
    )
    function_specifications = m.Containment["FunctionSpecification"](
        "ownedFunctionSpecifications", (NS, "FunctionSpecification")
    )


class FunctionSpecification(capellacore.Namespace, activity.AbstractActivity):
    in_exchange_links = m.Association["ExchangeLink"](
        (NS, "ExchangeLink"), "inExchangeLinks"
    )
    out_exchange_links = m.Association["ExchangeLink"](
        (NS, "ExchangeLink"), "outExchangeLinks"
    )
    ports = m.Containment["FunctionPort"](
        "ownedFunctionPorts", (NS, "FunctionPort")
    )


class ExchangeCategory(capellacore.NamedElement):
    _xmltag = "ownedCategories"

    exchanges = m.Association["FunctionalExchange"](
        (NS, "FunctionalExchange"), "exchanges"
    )


class ExchangeLink(capellacore.NamedRelationship):
    exchange_containment_links = m.Association["ExchangeContainment"](
        (NS, "ExchangeContainment"), "exchangeContainmentLinks"
    )
    exchange_containments = m.Containment["ExchangeContainment"](
        "ownedExchangeContainments", (NS, "ExchangeContainment")
    )
    sources = m.Association["FunctionSpecification"](
        (NS, "FunctionSpecification"), "sources"
    )
    destinations = m.Association["FunctionSpecification"](
        (NS, "FunctionSpecification"), "destinations"
    )


class ExchangeContainment(capellacore.Relationship):
    exchange = m.Single["ExchangeSpecification"](
        m.Association((NS, "ExchangeSpecification"), "exchange")
    )
    link = m.Single["ExchangeLink"](
        m.Association((NS, "ExchangeLink"), "link")
    )


class ExchangeSpecification(
    capellacore.NamedElement, activity.ActivityExchange, abstract=True
):
    link = m.Association["ExchangeContainment"](
        (NS, "ExchangeContainment"), "link"
    )


class FunctionalExchangeSpecification(ExchangeSpecification):
    pass


class FunctionalChain(
    capellacore.NamedElement,
    capellacore.InvolverElement,
    capellacore.InvolvedElement,
):
    _xmltag = "ownedFunctionalChains"

    kind = m.EnumPOD("kind", FunctionalChainKind)
    involvements = m.Containment["FunctionalChainInvolvement"](
        "ownedFunctionalChainInvolvements", (NS, "FunctionalChainInvolvement")
    )

    @property
    def involved_functions(self) -> m.ElementList[AbstractFunction]:
        objs = self.involvements.map("involved").by_class(AbstractFunction)
        return m.ElementList(self._model, objs._elements, legacy_by_type=True)

    @property
    def involved_links(self) -> m.ElementList[FunctionalExchange]:
        objs = self.involvements.map("involved").by_class(FunctionalExchange)
        return m.ElementList(self._model, objs._elements, legacy_by_type=True)

    @property
    def involved_chains(self) -> m.ElementList[FunctionalChain]:
        return self.involvements.map("involved").by_class(FunctionalChain)

    @property
    def involved(self) -> m.ElementList[AbstractFunction | FunctionalExchange]:
        objs = self.involvements.map("involved").by_class(
            AbstractFunction, FunctionalExchange
        )
        return m.ElementList(self._model, objs._elements, legacy_by_type=True)

    involving_chains = m.Backref["FunctionalChain"](
        (NS, "FunctionalChain"), "involved_chains"
    )

    functional_chain_realizations = m.Containment[
        "FunctionalChainRealization"
    ]("ownedFunctionalChainRealizations", (NS, "FunctionalChainRealization"))
    realized_chains = m.Allocation["FunctionalChain"](
        "ownedFunctionalChainRealizations",
        (NS, "FunctionalChainRealization"),
        (NS, "FunctionalChain"),
        attr="targetElement",
        backattr="sourceElement",
    )
    realizing_chains = m.Backref["FunctionalChain"](
        (NS, "FunctionalChain"), "realized_chains"
    )
    available_in_states = m.Association["capellacommon.State"](
        (ns.CAPELLACOMMON, "State"), "availableInStates"
    )
    precondition = m.Single["capellacore.Constraint"](
        m.Association((ns.CAPELLACORE, "Constraint"), "preCondition")
    )
    postcondition = m.Single["capellacore.Constraint"](
        m.Association((ns.CAPELLACORE, "Constraint"), "postCondition")
    )
    sequence_nodes = m.Containment["ControlNode"](
        "ownedSequenceNodes", (NS, "ControlNode")
    )
    sequence_links = m.Containment["SequenceLink"](
        "ownedSequenceLinks", (NS, "SequenceLink")
    )

    if not t.TYPE_CHECKING:
        control_nodes = m.DeprecatedAccessor("sequence_nodes")


class AbstractFunctionalChainContainer(
    capellacore.CapellaElement, abstract=True
):
    functional_chains = m.Containment["FunctionalChain"](
        "ownedFunctionalChains", (NS, "FunctionalChain")
    )


class FunctionalChainInvolvement(capellacore.Involvement, abstract=True):
    _xmltag = "ownedFunctionalChainInvolvements"


class FunctionalChainReference(FunctionalChainInvolvement):
    involved = m.Single["FunctionalChain"](
        m.Association((NS, "FunctionalChain"), None)
    )


class FunctionPort(
    information.Port,
    capellacore.TypedElement,
    behavior.AbstractEvent,
    abstract=True,
):
    represented_component_port = m.Single["ComponentPort"](
        m.Association((NS, "ComponentPort"), "representedComponentPort")
    )
    realized_ports = m.Allocation["FunctionPort"](
        None, None, (NS, "FunctionPort")
    )
    allocated_ports = m.Allocation["FunctionPort"](
        None, None, (NS, "FunctionPort")
    )
    exchanges = m.Backref["FunctionalExchange"](
        (NS, "FunctionalExchange"), "source", "target"
    )

    if not t.TYPE_CHECKING:
        owner = m.DeprecatedAccessor("parent")


class FunctionInputPort(FunctionPort, activity.InputPin):
    """A function input port."""

    _xmltag = "inputs"

    exchange_items = m.Association["information.ExchangeItem"](
        (ns.INFORMATION, "ExchangeItem"), "incomingExchangeItems"
    )


class FunctionOutputPort(FunctionPort, activity.OutputPin):
    """A function output port."""

    _xmltag = "outputs"

    exchange_items = m.Association["information.ExchangeItem"](
        (ns.INFORMATION, "ExchangeItem"), "outgoingExchangeItems"
    )


class AbstractFunctionAllocation(capellacore.Allocation, abstract=True):
    pass


class ComponentFunctionalAllocation(AbstractFunctionAllocation):
    pass


class FunctionalChainRealization(capellacore.Allocation):
    pass


class ExchangeSpecificationRealization(capellacore.Allocation, abstract=True):
    pass


class FunctionalExchangeRealization(capellacore.Allocation):
    pass


class FunctionRealization(AbstractFunctionAllocation):
    """A realization that links to a function."""

    _xmltag = "ownedFunctionRealizations"


class FunctionalExchange(
    capellacore.Relationship,
    capellacore.InvolvedElement,
    activity.ObjectFlow,
    behavior.AbstractEvent,
    information.AbstractEventOperation,
    # NOTE: NamedElement is first in the upstream metamodel,
    # but that would result in an MRO conflict with AbstractEventOperation,
    # which inherits from NamedElement.
    capellacore.NamedElement,
    _AbstractExchange,
):
    _xmltag = "ownedFunctionalExchanges"

    exchange_specifications = m.Association["FunctionalExchangeSpecification"](
        (NS, "FunctionalExchangeSpecification"), "exchangeSpecifications"
    )
    exchanged_items = m.Association["information.ExchangeItem"](
        (ns.INFORMATION, "ExchangeItem"), "exchangedItems"
    )
    functional_exchange_realizations = m.Containment[
        "FunctionalExchangeRealization"
    ](
        "ownedFunctionalExchangeRealizations",
        (NS, "FunctionalExchangeRealization"),
    )
    realized_functional_exchanges = m.Allocation["FunctionalExchange"](
        "ownedFunctionalExchangeRealizations",
        (NS, "FunctionalExchangeRealization"),
        (NS, "FunctionalExchange"),
        attr="targetElement",
        backattr="sourceElement",
    )
    realizing_functional_exchanges = m.Backref["FunctionalExchange"](
        (NS, "FunctionalExchange"), "realized_functional_exchanges"
    )
    owner = m.Single["ComponentExchange"](
        m.Backref((NS, "ComponentExchange"), "allocated_functional_exchanges")
    )
    allocating_component_exchange = m.Alias["ComponentExchange"]("owner")
    categories = m.Backref["ExchangeCategory"](
        (NS, "ExchangeCategory"), "exchanges"
    )

    involving_functional_chains = m.Backref["FunctionalChain"](
        (NS, "FunctionalChain"), "involved_links"
    )

    if not t.TYPE_CHECKING:
        exchange_items = m.DeprecatedAccessor("exchanged_items")


class AbstractFunction(
    capellacore.Namespace,
    capellacore.InvolvedElement,
    information.AbstractInstance,
    AbstractFunctionalChainContainer,
    activity.CallBehaviorAction,
    behavior.AbstractEvent,
    abstract=True,
):
    """An abstract function."""

    _xmltag = "ownedFunctions"

    kind = m.EnumPOD("kind", FunctionKind)
    condition = m.StringPOD("condition")
    functions = m.Containment["AbstractFunction"](
        "ownedFunctions", (NS, "AbstractFunction")
    )
    function_realizations = m.Containment["FunctionRealization"](
        "ownedFunctionRealizations", (NS, "FunctionRealization")
    )
    realized_functions = m.Allocation["AbstractFunction"](
        "ownedFunctionRealizations",
        (NS, "FunctionRealization"),
        (NS, "AbstractFunction"),
        attr="targetElement",
        backattr="sourceElement",
    )
    realizing_functions = m.Backref["AbstractFunction"](
        (NS, "AbstractFunction"), "realized_functions", legacy_by_type=True
    )
    exchanges = m.Containment["FunctionalExchange"](
        "ownedFunctionalExchanges", (NS, "FunctionalExchange")
    )
    available_in_states = m.Association["capellacommon.State"](
        (ns.CAPELLACOMMON, "State"), "availableInStates"
    )

    related_exchanges = m.Backref["FunctionalExchange"](
        (NS, "FunctionalExchange"), "source.owner", "target.owner"
    )
    scenarios = m.Backref["interaction.Scenario"](
        (ns.INTERACTION, "Scenario"), "related_functions"
    )

    @property
    def is_leaf(self) -> bool:
        return not self.functions


class ComponentExchange(
    behavior.AbstractEvent,
    information.AbstractEventOperation,
    # NOTE: NamedElement comes before ExchangeSpecification in the upstream
    # metamodel, but that would result in an MRO conflict.
    ExchangeSpecification,
    capellacore.NamedElement,
    _AbstractExchange,
):
    _xmltag = "ownedComponentExchanges"

    kind = m.EnumPOD("kind", ComponentExchangeKind)
    is_oriented = m.BoolPOD("oriented")

    functional_exchange_allocations = m.Containment[
        "ComponentExchangeFunctionalExchangeAllocation"
    ](
        "ownedComponentExchangeFunctionalExchangeAllocations",
        (NS, "ComponentExchangeFunctionalExchangeAllocation"),
    )
    allocated_functional_exchanges = m.Allocation["FunctionalExchange"](
        "ownedComponentExchangeFunctionalExchangeAllocations",
        (NS, "ComponentExchangeFunctionalExchangeAllocation"),
        (NS, "FunctionalExchange"),
        attr="targetElement",
        backattr="sourceElement",
    )
    component_exchange_realizations = m.Containment[
        "ComponentExchangeRealization"
    ](
        "ownedComponentExchangeRealizations",
        (NS, "ComponentExchangeRealization"),
    )
    realized_component_exchanges = m.Allocation["ComponentExchange"](
        "ownedComponentExchangeRealizations",
        (NS, "ComponentExchangeRealization"),
        (NS, "ComponentExchange"),
        attr="targetElement",
        backattr="sourceElement",
    )
    realizing_component_exchanges = m.Backref["ComponentExchange"](
        (NS, "ComponentExchange"), "realized_component_exchanges"
    )
    ends = m.Containment["ComponentExchangeEnd"](
        "ownedComponentExchangeEnds", (NS, "ComponentExchangeEnd")
    )
    categories = m.Backref["ComponentExchangeCategory"](
        (NS, "ComponentExchangeCategory"), "exchanges"
    )

    allocating_physical_links = m.Backref["cs.PhysicalLink"](
        (ns.CS, "PhysicalLink"), "allocated_component_exchanges"
    )
    allocating_physical_paths = m.Backref["cs.PhysicalPath"](
        (ns.CS, "PhysicalPath"), "allocated_component_exchanges"
    )

    @property
    @deprecated(
        (
            "ComponentExchange.allocating_physical_link is deprecated,"
            " because it only takes into account the first allocation link."
            " Use allocating_physical_links instead, which allows multiple links."
        ),
        category=FutureWarning,
    )
    def allocating_physical_link(self) -> cs.PhysicalLink | None:
        links = self.allocating_physical_links
        return links[0] if links else None

    @property
    @deprecated(
        (
            "ComponentExchange.owner is deprecated,"
            " because it only takes into account the first allocation link."
            " Use allocating_physical_links instead, which allows multiple links."
        ),
        category=FutureWarning,
    )
    def owner(self) -> cs.PhysicalLink | None:
        links = self.allocating_physical_links
        return links[0] if links else None

    @property
    def exchange_items(
        self,
    ) -> m.ElementList[modellingcore.AbstractExchangeItem]:
        return (
            self.convoyed_informations
            + self.allocated_functional_exchanges.map("exchanged_items")
        )

    if not t.TYPE_CHECKING:
        allocated_exchange_items = m.DeprecatedAccessor(
            "convoyed_informations"
        )


class ComponentExchangeAllocation(capellacore.Allocation):
    pass


class ComponentExchangeAllocator(capellacore.NamedElement, abstract=True):
    component_exchange_allocations = m.Containment[
        "ComponentExchangeAllocation"
    ]("ownedComponentExchangeAllocations", (NS, "ComponentExchangeAllocation"))
    allocated_component_exchanges = m.Allocation["ComponentExchange"](
        "ownedComponentExchangeAllocations",
        (NS, "ComponentExchangeAllocation"),
        (NS, "ComponentExchange"),
        attr="targetElement",
        backattr="sourceElement",
    )


class ComponentExchangeCategory(capellacore.NamedElement):
    _xmltag = "ownedComponentExchangeCategories"

    exchanges = m.Association["ComponentExchange"](
        (NS, "ComponentExchange"), "exchanges"
    )


class ComponentExchangeEnd(
    modellingcore.InformationsExchanger, capellacore.CapellaElement
):
    port = m.Single["information.Port"](
        m.Association((ns.INFORMATION, "Port"), "port")
    )
    part = m.Single["cs.Part"](m.Association((ns.CS, "Part"), "part"))


class ComponentExchangeFunctionalExchangeAllocation(
    AbstractFunctionAllocation
):
    pass


class ComponentExchangeRealization(ExchangeSpecificationRealization):
    pass


class ComponentPort(
    information.Port, modellingcore.InformationsExchanger, information.Property
):
    """A component port."""

    _xmltag = "ownedFeatures"

    orientation = m.EnumPOD("orientation", OrientationPortKind)
    kind = m.EnumPOD("kind", ComponentPortKind)
    exchanges = m.Backref["ComponentExchange"](
        (NS, "ComponentExchange"), "source", "target"
    )

    if not t.TYPE_CHECKING:
        direction = m.DeprecatedAccessor("orientation")
        owner = m.DeprecatedAccessor("parent")


class ComponentPortAllocation(capellacore.Allocation):
    ends = m.Containment["ComponentPortAllocationEnd"](
        "ownedComponentPortAllocationEnds", (NS, "ComponentPortAllocationEnd")
    )


class ComponentPortAllocationEnd(capellacore.CapellaElement):
    port = m.Single["information.Port"](
        m.Association((ns.INFORMATION, "Port"), "port")
    )
    part = m.Single["cs.Part"](m.Association((ns.CS, "Part"), "part"))


class ReferenceHierarchyContext(modellingcore.ModelElement, abstract=True):
    source_reference_hierarchy = m.Association["FunctionalChainReference"](
        (NS, "FunctionalChainReference"), "sourceReferenceHierarchy"
    )
    target_reference_hierarchy = m.Association["FunctionalChainReference"](
        (NS, "FunctionalChainReference"), "targetReferenceHierarchy"
    )


class FunctionalChainInvolvementLink(
    FunctionalChainInvolvement, ReferenceHierarchyContext
):
    exchange_context = m.Single["capellacore.Constraint"](
        m.Association((ns.CAPELLACORE, "Constraint"), "exchangeContext")
    )
    exchanged_items = m.Association["information.ExchangeItem"](
        (ns.INFORMATION, "ExchangeItem"), "exchangedItems"
    )
    source = m.Single["FunctionalChainInvolvementFunction"](
        m.Association((NS, "FunctionalChainInvolvementFunction"), "source")
    )
    target = m.Single["FunctionalChainInvolvementFunction"](
        m.Association((NS, "FunctionalChainInvolvementFunction"), "target")
    )

    if not t.TYPE_CHECKING:
        context = m.DeprecatedAccessor("exchange_context")


class SequenceLink(capellacore.CapellaElement, ReferenceHierarchyContext):
    condition = m.Single["capellacore.Constraint"](
        m.Association((ns.CAPELLACORE, "Constraint"), "condition")
    )
    links = m.Association["FunctionalChainInvolvementLink"](
        (NS, "FunctionalChainInvolvementLink"), "links"
    )
    source = m.Single["SequenceLinkEnd"](
        m.Association((NS, "SequenceLinkEnd"), "source")
    )
    target = m.Single["SequenceLinkEnd"](
        m.Association((NS, "SequenceLinkEnd"), "target")
    )


class SequenceLinkEnd(capellacore.CapellaElement, abstract=True):
    pass


class FunctionalChainInvolvementFunction(
    FunctionalChainInvolvement, SequenceLinkEnd
):
    pass


class ControlNode(SequenceLinkEnd):
    _xmltag = "ownedSequenceNodes"

    kind = m.EnumPOD("kind", ControlNodeKind)


if not t.TYPE_CHECKING:

    def __getattr__(attr):
        if attr == "AbstractExchange":
            warnings.warn(
                (
                    "AbstractExchange is deprecated and will be removed soon,"
                    " use the concrete FunctionalExchange or ComponentExchange"
                    " class or another common superclass instead"
                ),
                DeprecationWarning,
                stacklevel=2,
            )
            return _AbstractExchange

        if attr == "Function":
            warnings.warn(
                "Function has been merged into AbstractFunction",
                DeprecationWarning,
                stacklevel=2,
            )
            return AbstractFunction

        raise AttributeError(f"{__name__} has no attribute {attr}")


from . import capellacommon, cs, interaction  # noqa: F401
