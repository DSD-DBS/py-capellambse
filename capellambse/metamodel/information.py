# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Objects and relations for information capture and data modelling."""
from __future__ import annotations

import typing as t

from capellambse import model as m

from . import behavior, capellacore
from . import information_datavalue as dv
from . import modellingcore, modeltypes
from . import namespaces as ns

if t.TYPE_CHECKING:
    from . import capellacommon, cs, fa
    from . import information_datatype as dt

NS = ns.INFORMATION
NS_COM = ns.INFORMATION_COMMUNICATION
NS_DT = ns.INFORMATION_DATATYPE
NS_DV = ns.INFORMATION_DATAVALUE


class MultiplicityElement(capellacore.CapellaElement):
    is_ordered = m.BoolPOD("ordered")
    is_unique = m.BoolPOD("unique")
    min_inclusive = m.BoolPOD("minInclusive")
    max_inclusive = m.BoolPOD("maxInclusive")

    default_value = m.Single(
        m.Containment["dv.DataValue"](
            "ownedDefaultValue", (NS_DV, "DataValue")
        ),
        enforce=False,
    )
    min_value = m.Single(
        m.Containment["dv.DataValue"]("ownedMinValue", (NS_DV, "DataValue")),
        enforce=False,
    )
    max_value = m.Single(
        m.Containment["dv.DataValue"]("ownedMaxValue", (NS_DV, "DataValue")),
        enforce=False,
    )
    null_value = m.Single(
        m.Containment["dv.DataValue"]("ownedNullValue", (NS_DV, "DataValue")),
        enforce=False,
    )
    min_card = m.Single(
        m.Containment["dv.NumericValue"](
            "ownedMinCard", (NS_DV, "NumericValue")
        ),
        enforce=False,
    )
    min_length = m.Single(
        m.Containment["dv.NumericValue"](
            "ownedMinLength", (NS_DV, "NumericValue")
        ),
        enforce=False,
    )
    max_card = m.Single(
        m.Containment["dv.NumericValue"](
            "ownedMaxCard", (NS_DV, "NumericValue")
        ),
        enforce=False,
    )
    max_length = m.Single(
        m.Containment["dv.NumericValue"](
            "ownedMaxLength", (NS_DV, "NumericValue")
        ),
        enforce=False,
    )


class Property(
    capellacore.Feature,
    capellacore.TypedElement,
    MultiplicityElement,
    modellingcore.FinalizableElement,
):
    """A Property of a Class."""

    aggregation_kind = m.EnumPOD(
        "aggregationKind", modeltypes.AggregationKind, default="UNSET"
    )
    is_derived = m.BoolPOD("isDerived")
    is_read_only = m.BoolPOD("isReadOnly")
    is_part_of_key = m.BoolPOD("isPartOfKey")

    association = m.Single(
        m.Backref["Association"]((NS, "Association"), lookup="roles"),
        enforce="max",
    )


class AbstractInstance(Property, abstract=True):
    pass


from . import information_communication as com


class AssociationPkg(capellacore.Structure):
    visibility = m.EnumPOD("visibility", modeltypes.VisibilityKind)
    associations = m.Containment["Association"](
        "ownedAssociations", (NS, "Association")
    )


class Association(capellacore.NamedRelationship):
    """An Association."""

    members = m.Containment["Property"]("ownedMembers", (NS, "Property"))
    navigable_members = m.Association["Property"](
        "navigableMembers", (NS, "Property")
    )


class Class(capellacore.GeneralClass):
    """A Class."""

    is_primitive = m.BoolPOD("isPrimitive")
    """Indicates if class is primitive."""

    state_machines = m.Containment["capellacommon.StateMachine"](
        "ownedStateMachines", (ns.CAPELLACOMMON, "StateMachine")
    )
    data_values = m.Containment["dv.DataValue"](
        "ownedDataValues", (NS_DV, "DataValue")
    )
    realized_classes = m.Allocation["Class"](
        (NS, "InformationRealization"),
        ("ownedInformationRealizations", "targetElement", "sourceElement"),
        (NS, "Class"),
    )
    realizing_classes = m.Backref["Class"](
        (NS, "Class"), lookup="realized_classes"
    )


class Collection(
    capellacore.Classifier,
    MultiplicityElement,
    dv.DataValueContainer,
    modellingcore.FinalizableElement,
):
    """A Collection."""

    is_primitive = m.BoolPOD("isPrimitive")
    visibility = m.EnumPOD("visibility", modeltypes.VisibilityKind)
    kind = m.EnumPOD("kind", modeltypes.CollectionKind)
    aggregation_kind = m.EnumPOD("aggregationKind", modeltypes.AggregationKind)
    type = m.Single(
        m.Association["capellacore.Type"]("type", (ns.CAPELLACORE, "Type")),
        enforce="max",
    )


class AbstractCollectionValue(dv.DataValue, abstract=True):
    """Base class for type-specific collection values."""


class CollectionValue(AbstractCollectionValue):
    """A value that represents a collection of elements."""

    elements = m.Containment["dv.DataValue"](
        "ownedElements", (NS_DV, "DataValue")
    )
    default_element = m.Single(
        m.Containment["dv.DataValue"](
            "ownedDefaultElement", (NS_DV, "DataValue")
        ),
        enforce="max",
    )


class CollectionValueReference(AbstractCollectionValue):
    value = m.Association["AbstractCollectionValue"](
        "referencedValue", (NS, "AbstractCollectionValue")
    )
    property = m.Association["Property"](
        "referencedProperty", (NS, "Property")
    )


class DataPkg(
    capellacore.AbstractDependenciesPkg,
    capellacore.AbstractExchangeItemPkg,
    AssociationPkg,
    dv.DataValueContainer,
    com.MessageReferencePkg,
):
    """A data package that can hold classes."""

    packages = m.Containment["DataPkg"](
        "ownedDataPkgs", (ns.INFORMATION, "DataPkg")
    )
    classes = m.Containment["Class"]("ownedClasses", (NS, "Class"))
    key_parts = m.Containment["KeyPart"]("ownedKeyParts", (NS, "KeyPart"))
    collections = m.Containment["Collection"](
        "ownedCollections", (NS, "Collection")
    )
    units = m.Containment["Unit"]("ownedUnits", (NS, "Unit"))
    data_types = m.Containment["dt.DataType"](
        "ownedDataTypes", (NS_DT, "DataType")
    )
    signals = m.Containment["com.Signal"]("ownedSignals", (NS_COM, "Signal"))
    messages = m.Containment["com.Message"](
        "ownedMessages", (NS_COM, "Message")
    )
    exceptions = m.Containment["com.Exception"](
        "ownedExceptions", (NS_COM, "Exception")
    )
    state_events = m.Containment["capellacommon.StateEvent"](
        "ownedStateEvents", (ns.CAPELLACOMMON, "StateEvent")
    )


class DomainElement(Class):
    """A reinterpretable representation of information in a formalized manner.

    Suitable for communication, interpretation, or processing.
    """


class KeyPart(capellacore.Relationship):
    property = m.Single(
        m.Association["Property"]("property", (NS, "Property"))
    )


class AbstractEventOperation(capellacore.NamedElement, abstract=True):
    pass


class Operation(
    capellacore.Feature, behavior.AbstractEvent, AbstractEventOperation
):
    parameters = m.Containment["Parameter"](
        "ownedParameters", (NS, "Parameter")
    )
    allocated_operations = m.Allocation["Operation"](
        (NS, "OperationAllocation"),
        ("ownedOperationAllocations", "targetElement", "sourceElement"),
        (NS, "Operation"),
    )
    allocating_operations = m.Backref["Operation"](
        (NS, "Operation"), lookup="allocated_operations"
    )
    realized_exchange_items = m.Allocation["ExchangeItem"](
        (NS, "ExchangeItemRealization"),
        ("ownedExchangeItemRealizations", "targetElement", "sourceElement"),
        (NS, "ExchangeItem"),
    )


class Parameter(
    capellacore.TypedElement,
    MultiplicityElement,
    modellingcore.AbstractParameter,
):
    direction = m.EnumPOD("direction", modeltypes.ParameterDirection)
    passing_mode = m.EnumPOD("passingMode", modeltypes.PassingMode)


class Service(Operation):
    synchronism_kind = m.EnumPOD("synchronismKind", modeltypes.SynchronismKind)
    thrown_exceptions = m.Association["com.Exception"](
        "thrownExceptions", (NS_COM, "Exception")
    )
    message_references = m.Association["com.Message"](
        "messageReferences", (NS_COM, "MessageReference")
    )


class Union(Class):
    """A Union."""

    kind = m.EnumPOD("kind", modeltypes.UnionKind)
    discriminant = m.Single(
        m.Association["UnionProperty"]("discriminant", (NS, "UnionProperty")),
        enforce="max",
    )
    default_property = m.Single(
        m.Association["UnionProperty"](
            "defaultProperty", (NS, "UnionProperty")
        ),
        enforce="max",
    )


class UnionProperty(Property):
    qualifier = m.Association["dv.DataValue"](
        "qualifier", (NS_DV, "DataValue")
    )


class Unit(capellacore.NamedElement):
    """A unit.

    A Unit is a quantity in terms of which the magnitudes of other
    quantities that have the same dimension can be stated. A unit often
    relies on precise and reproducible ways to measure the unit. For
    example, a unit of length such as meter may be specified as a
    multiple of a particular wavelength of light. A unit may also
    specify less stable or precise ways to express some value, such as a
    cost expressed in some currency, or a severity rating measured by a
    numerical scale.
    """


class Port(capellacore.NamedElement, abstract=True):
    protocols = m.Containment["capellacommon.StateMachine"](
        "ownedProtocols", (ns.CAPELLACOMMON, "StateMachine")
    )
    provided_interfaces = m.Association["cs.Interface"](
        "providedInterfaces", (ns.CS, "Interface")
    )
    required_interfaces = m.Association["cs.Interface"](
        "requiredInterfaces", (ns.CS, "Interface")
    )
    realized_ports = m.Allocation["Port"](
        (NS, "PortRealization"),
        ("ownedPortAllocations", "targetElement", "sourceElement"),
        (NS, "Port"),
    )
    allocated_ports = m.Allocation["Port"](
        (NS, "PortAllocation"),
        ("ownedPortAllocations", "targetElement", "sourceElement"),
        (NS, "Port"),
    )


class ExchangeItem(
    modellingcore.AbstractExchangeItem,
    behavior.AbstractEvent,
    behavior.AbstractSignal,
    modellingcore.FinalizableElement,
    capellacore.GeneralizableElement,
):
    mechanism = m.EnumPOD("exchangeMechanism", modeltypes.ExchangeMechanism)
    elements = m.Containment["ExchangeItemElement"](
        "ownedElements", (NS, "ExchangeItemElement")
    )
    realized_exchange_items = m.Allocation["ExchangeItem"](
        (NS, "ExchangeItemRealization"),
        ("ownedInformationRealizations", "targetElement", "sourceElement"),
        (NS, "ExchangeItem"),
    )
    instances = m.Containment["ExchangeItemInstance"](
        "ownedExchangeItemInstances", (NS, "ExchangeItemInstance")
    )
    exchanges = m.Backref["fa.ComponentExchange | fa.FunctionalExchange"](
        (ns.FA, "ComponentExchange"),
        (ns.FA, "FunctionalExchange"),
        lookup=["exchange_items", "allocated_exchange_items"],
    )


class ExchangeItemElement(
    MultiplicityElement,
    capellacore.TypedElement,
    # NOTE: NamedElement is first in the upstream metamodel,
    # but that would result in an MRO conflict with TypedElement
    capellacore.NamedElement,
):
    kind = m.EnumPOD("kind", modeltypes.ElementKind)
    direction = m.EnumPOD("Direction", modeltypes.ParameterDirection)
    is_composite = m.BoolPOD("composite")
    referenced_properties = m.Association["Property"](
        "referencedProperties", (NS, "Property")
    )


class ExchangeItemInstance(AbstractInstance):
    pass
