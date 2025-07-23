# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Objects and relations for information capture and data modelling."""

from __future__ import annotations

import enum
import typing as t

import capellambse.model as m

from .. import behavior, capellacore, modellingcore
from .. import namespaces as ns

NS = ns.INFORMATION
NS_DV = ns.INFORMATION_DATAVALUE
NS_DT = ns.INFORMATION_DATATYPE
NS_COMM = ns.INFORMATION_COMMUNICATION


@m.stringy_enum
@enum.unique
class AggregationKind(enum.Enum):
    """Defines the specific kind of a relationship, as per UML definitions."""

    UNSET = "UNSET"
    """Used when value is not defined by the user."""
    ASSOCIATION = "ASSOCIATION"
    """A semantic relationship between typed instances.

    It has at least two ends represented by properties, each of which is
    connected to the type of the end. More than one end of the
    association may have the same type.

    Indicates that the property has no aggregation.
    """
    AGGREGATION = "AGGREGATION"
    """A semantic relationship between a part and a whole.

    The part has a lifecycle of its own, and is potentially shared among
    several aggregators.
    """
    COMPOSITION = "COMPOSITION"
    """A semantic relationship between whole and its parts.

    The parts lifecycles are tied to that of the whole, and they are not
    shared with any other aggregator.
    """


@m.stringy_enum
@enum.unique
class CollectionKind(enum.Enum):
    """Defines the specific kind of a Collection structure."""

    ARRAY = "ARRAY"
    """The collection is to be considered an array of elements."""
    SEQUENCE = "SEQUENCE"
    """The collection is to be considered as a sequence (list) of elements."""


@m.stringy_enum
@enum.unique
class ElementKind(enum.Enum):
    """The visibility options for features of a class."""

    TYPE = "TYPE"
    """The ExchangeItemElement is a type for its ExchangeItem."""
    MEMBER = "MEMBER"
    """The ExchangeItemElement is a member for its ExchangeItem."""


@m.stringy_enum
@enum.unique
class ExchangeMechanism(enum.Enum):
    """Enumeration of the different exchange mechanisms."""

    UNSET = "UNSET"
    """The exchange mechanism is not defined."""
    FLOW = "FLOW"
    """Continuous supply of data."""
    OPERATION = "OPERATION"
    """Sporadic supply of data with returned data."""
    EVENT = "EVENT"
    """Asynchronous information that is taken into account rapidly."""
    SHARED_DATA = "SHARED_DATA"


@m.stringy_enum
@enum.unique
class ParameterDirection(enum.Enum):
    """The direction in which data is passed along through a parameter."""

    IN = "IN"
    """The parameter represents an input of the operation it is used in."""
    OUT = "OUT"
    """The parameter represents an output of the operation it is used in."""
    INOUT = "INOUT"
    """The parameter represents both an input and output of the operation."""
    RETURN = "RETURN"
    """The parameter represents the return value of the operation."""
    EXCEPTION = "EXCEPTION"
    """The parameter is like an exception."""
    UNSET = "UNSET"
    """The CommunicationLink protocol is not yet set."""


@m.stringy_enum
@enum.unique
class PassingMode(enum.Enum):
    """The data passing mechanism for parameters of an operation."""

    UNSET = "UNSET"
    """The data passing mechanism is not precised."""
    BY_REF = "BY_REF"
    """The data is being passed by reference to the operation."""
    BY_VALUE = "BY_VALUE"
    """The data is being passed by value to the operation."""


@m.stringy_enum
@enum.unique
class SynchronismKind(enum.Enum):
    """The synchronicity of an operation invocation."""

    UNSET = "UNSET"
    SYNCHRONOUS = "SYNCHRONOUS"
    ASYNCHRONOUS = "ASYNCHRONOUS"


@m.stringy_enum
@enum.unique
class UnionKind(enum.Enum):
    UNION = "UNION"
    VARIANT = "VARIANT"


class MultiplicityElement(capellacore.CapellaElement, abstract=True):
    is_ordered = m.BoolPOD("ordered")
    """Indicates if this element is ordered."""
    is_unique = m.BoolPOD("unique")
    """Indicates if this element is unique."""
    is_min_inclusive = m.BoolPOD("minInclusive")
    is_max_inclusive = m.BoolPOD("maxInclusive")
    default_value = m.Single["datavalue.DataValue"](
        m.Containment("ownedDefaultValue", (NS_DV, "DataValue"))
    )
    min_value = m.Single["datavalue.DataValue"](
        m.Containment("ownedMinValue", (NS_DV, "DataValue"))
    )
    max_value = m.Single["datavalue.DataValue"](
        m.Containment("ownedMaxValue", (NS_DV, "DataValue"))
    )
    null_value = m.Single["datavalue.DataValue"](
        m.Containment("ownedNullValue", (NS_DV, "DataValue"))
    )
    min_card = m.Single["datavalue.NumericValue"](
        m.Containment("ownedMinCard", (NS_DV, "NumericValue"))
    )
    min_length = m.Single["datavalue.NumericValue"](
        m.Containment("ownedMinLength", (NS_DV, "NumericValue"))
    )
    max_card = m.Single["datavalue.NumericValue"](
        m.Containment("ownedMaxCard", (NS_DV, "NumericValue"))
    )
    max_length = m.Single["datavalue.NumericValue"](
        m.Containment("ownedMaxLength", (NS_DV, "NumericValue"))
    )


class Property(
    capellacore.Feature,
    capellacore.TypedElement,
    MultiplicityElement,
    modellingcore.FinalizableElement,
):
    """A Property of a Class."""

    _xmltag = "ownedFeatures"

    aggregation_kind = m.EnumPOD("aggregationKind", AggregationKind)
    is_derived = m.BoolPOD("isDerived")
    """Indicates if property is abstract."""
    is_read_only = m.BoolPOD("isReadOnly")
    """Indicates if property is read-only."""
    is_part_of_key = m.BoolPOD("isPartOfKey")
    """Indicates if property is part of key."""
    association = m.Single["Association"](
        m.Backref((NS, "Association"), "roles")
    )

    if not t.TYPE_CHECKING:
        kind = m.DeprecatedAccessor("aggregation_kind")


class AbstractInstance(Property, abstract=True):
    pass


class AssociationPkg(capellacore.Structure, abstract=True):
    visibility = m.EnumPOD("visibility", capellacore.VisibilityKind)
    associations = m.Containment["Association"](
        "ownedAssociations", (NS, "Association")
    )


class Association(capellacore.NamedRelationship):
    _xmltag = "ownedAssociations"

    members = m.Containment["Property"]("ownedMembers", (NS, "Property"))
    navigable_members = m.Association["Property"](
        (NS, "Property"), "navigableMembers"
    )

    @property
    def roles(self) -> m.ElementList[Property]:
        assert isinstance(self.members, m.ElementList)
        assert isinstance(self.navigable_members, m.ElementList)
        roles = [i._element for i in self.members + self.navigable_members]
        return m.ElementList(self._model, roles, Property)


class Class(capellacore.GeneralClass):
    _xmltag = "ownedClasses"

    is_primitive = m.BoolPOD("isPrimitive")
    """Indicates if class is primitive."""
    key_parts = m.Association["KeyPart"]((NS, "KeyPart"), "keyParts")
    state_machines = m.Containment["capellacommon.StateMachine"](
        "ownedStateMachines", (ns.CAPELLACOMMON, "StateMachine")
    )
    data_values = m.Containment["datavalue.DataValue"](
        "ownedDataValues", (NS_DV, "DataValue")
    )
    information_realizations = m.Containment["InformationRealization"](
        "ownedInformationRealizations", (NS, "InformationRealization")
    )
    realized_classes = m.Allocation["Class"](
        "ownedInformationRealizations",
        (NS, "InformationRealization"),
        (NS, "Class"),
        attr="targetElement",
        backattr="sourceElement",
    )
    realized_by = m.Backref["Class"]((NS, "Class"), "realized_classes")

    owned_properties = m.Filter["Property"]("owned_features", (NS, "Property"))

    @property
    def properties(self) -> m.ElementList[Property]:
        """Return all owned and inherited properties."""
        return (
            self.owned_properties + self.super.properties
            if self.super is not None
            else self.owned_properties
        )

    if not t.TYPE_CHECKING:
        realizations = m.DeprecatedAccessor("information_realizations")


from . import datavalue as datavalue


class Collection(
    capellacore.Classifier,
    MultiplicityElement,
    datavalue.DataValueContainer,
    modellingcore.FinalizableElement,
):
    """A Collection."""

    _xmltag = "ownedCollections"

    is_primitive = m.BoolPOD("isPrimitive")
    visibility = m.EnumPOD("visibility", capellacore.VisibilityKind)
    kind = m.EnumPOD("kind", CollectionKind)
    aggregation_kind = m.EnumPOD("aggregationKind", AggregationKind)
    type = m.Association["capellacore.Type"]((ns.CAPELLACORE, "Type"), "type")
    index = m.Association["datatype.DataType"]((NS_DT, "DataType"), "index")


class AbstractCollectionValue(datavalue.DataValue, abstract=True):
    pass


class CollectionValue(AbstractCollectionValue):
    elements = m.Containment["datavalue.DataValue"](
        "ownedElements", (NS_DV, "DataValue")
    )
    default_element = m.Containment["datavalue.DataValue"](
        "ownedDefaultElement", (NS_DV, "DataValue")
    )


class CollectionValueReference(AbstractCollectionValue):
    value = m.Association["AbstractCollectionValue"](
        (NS, "AbstractCollectionValue"), "referencedValue"
    )
    property = m.Association["Property"](
        (NS, "Property"), "referencedProperty"
    )


from . import communication as communication


class DataPkg(
    capellacore.AbstractDependenciesPkg,
    capellacore.AbstractExchangeItemPkg,
    AssociationPkg,
    datavalue.DataValueContainer,
    communication.MessageReferencePkg,
):
    """A data package that can hold classes."""

    _xmltag = "ownedDataPkgs"

    packages = m.Containment["DataPkg"]("ownedDataPkgs", (NS, "DataPkg"))
    classes = m.Containment["Class"]("ownedClasses", (NS, "Class"))
    unions = m.Filter["Union"]("classes", (NS, "Union"))
    key_parts = m.Containment["KeyPart"]("ownedKeyParts", (NS, "KeyPart"))
    collections = m.Containment["Collection"](
        "ownedCollections", (NS, "Collection")
    )
    units = m.Containment["Unit"]("ownedUnits", (NS, "Unit"))
    data_types = m.Containment["datatype.DataType"](
        "ownedDataTypes", (NS_DT, "DataType")
    )
    enumerations = m.Filter["datatype.Enumeration"](
        "data_types", (NS_DT, "Enumeration")
    )
    signals = m.Containment["communication.Signal"](
        "ownedSignals", (NS_COMM, "Signal")
    )
    messages = m.Containment["communication.Message"](
        "ownedMessages", (NS_COMM, "Message")
    )
    exceptions = m.Containment["communication.Exception"](
        "ownedExceptions", (NS_COMM, "Exception")
    )
    state_events = m.Containment["capellacommon.StateEvent"](
        "ownedStateEvents", (ns.CAPELLACOMMON, "StateEvent")
    )

    if not t.TYPE_CHECKING:
        datatypes = m.DeprecatedAccessor("data_types")
        owned_associations = m.DeprecatedAccessor("associations")


class DomainElement(Class):
    pass


class KeyPart(capellacore.Relationship):
    property = m.Single["Property"](
        m.Association((NS, "Property"), "property")
    )


class AbstractEventOperation(capellacore.NamedElement, abstract=True):
    pass


class Operation(
    capellacore.Feature,
    behavior.AbstractEvent,
    AbstractEventOperation,
    abstract=True,
):
    parameters = m.Containment["Parameter"](
        "ownedParameters", (NS, "Parameter")
    )
    operation_allocations = m.Containment["OperationAllocation"](
        "ownedOperationAllocation", (NS, "OperationAllocation")
    )
    allocated_operations = m.Allocation["Operation"](
        "ownedOperationAllocation",
        (NS, "OperationAllocation"),
        (NS, "Operation"),
        attr="targetElement",
        backattr="sourceElement",
    )
    allocating_operations = m.Backref["Operation"](
        (NS, "Operation"), "allocated_operations"
    )
    exchange_item_realizations = m.Containment["ExchangeItemRealization"](
        "ownedExchangeItemRealizations", (NS, "ExchangeItemRealization")
    )
    realized_exchange_items = m.Allocation["ExchangeItem"](
        "ownedExchangeItemRealizations",
        (NS, "ExchangeItemRealization"),
        (NS, "ExchangeItem"),
        attr="targetElement",
        backattr="sourceElement",
    )


class OperationAllocation(capellacore.Allocation):
    pass


class Parameter(
    capellacore.TypedElement,
    MultiplicityElement,
    modellingcore.AbstractParameter,
):
    direction = m.EnumPOD("direction", ParameterDirection)
    passing_mode = m.EnumPOD("passingMode", PassingMode)


class Service(Operation):
    synchronism_kind = m.EnumPOD("synchronismKind", SynchronismKind)
    thrown_exceptions = m.Association["communication.Exception"](
        (NS_COMM, "Exception"), "thrownExceptions"
    )
    message_references = m.Association["communication.MessageReference"](
        (NS_COMM, "MessageReference"), "messageReferences"
    )


class Union(Class):
    """A Union."""

    _xmltag = "ownedClasses"

    kind = m.EnumPOD("kind", UnionKind)
    discriminant = m.Association["UnionProperty"](
        (NS, "UnionProperty"), "discriminant"
    )
    default_property = m.Association["UnionProperty"](
        (NS, "UnionProperty"), "defaultProperty"
    )


class UnionProperty(Property):
    qualifier = m.Association["datavalue.DataValue"](
        (NS_DV, "DataValue"), "qualifier"
    )


class Unit(capellacore.NamedElement):
    _xmltag = "ownedUnits"


class Port(capellacore.NamedElement, abstract=True):
    protocols = m.Containment["capellacommon.StateMachine"](
        "ownedProtocols", (ns.CAPELLACOMMON, "StateMachine")
    )
    provided_interfaces = m.Association["cs.Interface"](
        (ns.CS, "Interface"), "providedInterfaces"
    )
    required_interfaces = m.Association["cs.Interface"](
        (ns.CS, "Interface"), "requiredInterfaces"
    )
    port_realizations = m.Containment["PortRealization"](
        "ownedPortRealizations", (NS, "PortRealization")
    )
    realized_ports = m.Allocation["Port"](
        "ownedPortRealizations",
        (NS, "PortRealization"),
        (NS, "Port"),
        attr="targetElement",
        backattr="sourceElement",
    )
    port_allocations = m.Containment["PortAllocation"](
        "ownedPortAllocations", (NS, "PortAllocation")
    )
    allocated_ports = m.Allocation["Port"](
        "ownedPortRealizations",
        (NS, "PortRealization"),
        (NS, "Port"),
        attr="targetElement",
        backattr="sourceElement",
    )

    if not t.TYPE_CHECKING:
        state_machines = m.DeprecatedAccessor("protocols")


class PortRealization(capellacore.Allocation):
    pass


class PortAllocation(capellacore.Allocation):
    _xmltag = "ownedPortAllocations"


class ExchangeItem(
    modellingcore.AbstractExchangeItem,
    behavior.AbstractEvent,
    behavior.AbstractSignal,
    modellingcore.FinalizableElement,
    capellacore.GeneralizableElement,
):
    _xmltag = "ownedExchangeItems"

    exchange_mechanism = m.EnumPOD("exchangeMechanism", ExchangeMechanism)
    elements = m.Containment["ExchangeItemElement"](
        "ownedElements", (NS, "ExchangeItemElement")
    )
    information_realizations = m.Containment["InformationRealization"](
        "ownedInformationRealizations", (NS, "InformationRealization")
    )
    instances = m.Containment["ExchangeItemInstance"](
        "ownedExchangeItemInstances", (NS, "ExchangeItemInstance")
    )

    @property
    def exchanges(
        self,
    ) -> m.ElementList[fa.ComponentExchange | fa.FunctionalExchange]:
        """Exchanges using this ExchangeItem."""
        CX = (ns.FA, "ComponentExchange")
        FX = (ns.FA, "FunctionalExchange")
        cxs = self._model.search(CX).by_convoyed_informations(self)
        fxs = self._model.search(FX).by_exchanged_items(self)
        return cxs + fxs

    if not t.TYPE_CHECKING:
        type = m.DeprecatedAccessor("exchange_mechanism")


class ExchangeItemElement(
    MultiplicityElement, capellacore.TypedElement, capellacore.NamedElement
):
    _xmltag = "ownedElements"

    kind = m.EnumPOD("kind", ElementKind)
    direction = m.EnumPOD("direction", ParameterDirection)
    is_composite = m.BoolPOD("composite")
    referenced_properties = m.Association["Property"](
        (NS, "Property"), "referencedProperties"
    )

    if not t.TYPE_CHECKING:
        abstract_type = m.DeprecatedAccessor("type")
        owner = m.DeprecatedAccessor("parent")


class ExchangeItemInstance(AbstractInstance):
    pass


class InformationRealization(capellacore.Allocation):
    _xmltag = "ownedInformationRealizations"


class ExchangeItemRealization(capellacore.Allocation):
    pass


from .. import capellacommon, cs, fa  # noqa: F401
from . import datatype as datatype
