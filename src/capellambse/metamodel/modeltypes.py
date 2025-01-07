# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Enumeration types used by the MelodyModel."""

import enum as _enum
import typing as t


class _StringyEnumMixin:
    """Mixin for enums that makes members compare equal to their key name.

    :meta public:
    """

    name: t.Any
    _name_: t.Any

    def __eq__(self, other: object) -> bool:
        if isinstance(other, type(self)):
            return self is other
        if isinstance(other, str):
            return self.name == other
        return NotImplemented

    def __str__(self) -> str:
        return str(self.name)

    def __hash__(self):
        return hash(self._name_)


@_enum.unique
class AccessPolicy(_StringyEnumMixin, _enum.Enum):
    READ_ONLY = "readOnly"
    READ_AND_WRITE = "readAndWrite"


@_enum.unique
class AggregationKind(_StringyEnumMixin, _enum.Enum):
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


@_enum.unique
class BinaryOperator(_StringyEnumMixin, _enum.Enum):
    """Specifies the kind of this binary operator."""

    UNSET = "UNSET"
    """The binary operator is not initialized."""
    ADD = "ADD"
    """The binary operator refers to an addition."""
    MUL = "MUL"
    """The binary operator refers to a multiplication."""
    SUB = "SUB"
    """The binary operator refers to a substraction."""
    DIV = "DIV"
    """The binary operator refers to a division."""
    POW = "POW"
    """The binary operator refers to a power operation."""
    MIN = "MIN"
    """The binary operator refers to a min operation."""
    MAX = "MAX"
    """The binary operator refers to a max operation."""
    EQU = "EQU"
    """The binary operator refers to an equal operation."""
    IOR = "IOR"
    """The binary operator refers to a logical inclusive OR operation."""
    XOR = "XOR"
    """The binary operator refers to a logical exclusive OR operation."""
    AND = "AND"
    """The binary operator refers to a logical AND operation."""


@_enum.unique
class CatalogElementKind(_StringyEnumMixin, _enum.Enum):
    REC = "REC"
    RPL = "RPL"
    REC_RPL = "REC_RPL"
    GROUPING = "GROUPING"


@_enum.unique
class ChangeEventKind(_StringyEnumMixin, _enum.Enum):
    WHEN = "WHEN"


@_enum.unique
class CollectionKind(_StringyEnumMixin, _enum.Enum):
    """Defines the specific kind of a Collection structure."""

    ARRAY = "ARRAY"
    """The collection is to be considered an array of elements."""
    SEQUENCE = "SEQUENCE"
    """The collection is to be considered as a sequence (list) of elements."""


@_enum.unique
class CommunicationLinkKind(_StringyEnumMixin, _enum.Enum):
    """Enumeration listing the various possibilities of communication links."""

    UNSET = "UNSET"
    """The CommunicationLink protocol is not yet set."""
    PRODUCE = "PRODUCE"
    """The CommunicationLink describes a production of ExchangeItem."""
    CONSUME = "CONSUME"
    """The CommunicationLink describes a comsumption of ExchangeItem."""
    SEND = "SEND"
    """The CommunicationLink describes a sending of ExchangeItem."""
    RECEIVE = "RECEIVE"
    """The CommunicationLink describes a reception of ExchangeItem."""
    CALL = "CALL"
    """The CommunicationLink describes a call of ExchangeItem."""
    EXECUTE = "EXECUTE"
    """The CommunicationLink describes an execution of ExchangeItem."""
    WRITE = "WRITE"
    """The CommunicationLink describes a writing of ExchangeItem."""
    ACCESS = "ACCESS"
    """The CommunicationLink describes an access to the ExchangeItem."""
    ACQUIRE = "ACQUIRE"
    """The CommunicationLink describes an acquisition of ExchangeItem."""
    TRANSMIT = "TRANSMIT"
    """The CommunicationLink describes a transmission of ExchangeItem."""


@_enum.unique
class CommunicationLinkProtocol(_StringyEnumMixin, _enum.Enum):
    """The various possibilities for the protocol of the communication link."""

    UNSET = "UNSET"
    """The CommunicationLink protocol is not yet set."""
    UNICAST = "UNICAST"
    """Describes sending an ExchangeItem using the unicast protocol."""
    MULTICAST = "MULTICAST"
    """Describes sending an ExchangeItem using the multicast protocol."""
    BROADCAST = "BROADCAST"
    """Describes sending an ExchangeItem using the broadcast protocol."""
    SYNCHRONOUS = "SYNCHRONOUS"
    """Describes a call of the ExchangeItem using the synchronous protocol."""
    ASYNCHRONOUS = "ASYNCHRONOUS"
    """Describes a call of the ExchangeItem using the asynchronous protocol."""
    READ = "READ"
    """Describes access to the ExchangeItem by reading it."""
    ACCEPT = "ACCEPT"
    """Describes access to the ExchangeItem by accepting it."""


@_enum.unique
class ComponentExchangeKind(_StringyEnumMixin, _enum.Enum):
    """The kind of a ComponentExchange."""

    UNSET = "UNSET"
    """Communication kind is not set."""
    DELEGATION = "DELEGATION"
    """Indicates that the connector is a delegation connector."""
    ASSEMBLY = "ASSEMBLY"
    """Indicates that the connector is an assembly connector."""
    FLOW = "FLOW"
    """Describes a flow communication."""


@_enum.unique
class ComponentPortKind(_StringyEnumMixin, _enum.Enum):
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


@_enum.unique
class ConfigurationItemKind(_StringyEnumMixin, _enum.Enum):
    UNSET = "Unset"
    COTSCI = "COTSCI"
    """Commercial Off The Shelves Configuration Item."""
    CSCI = "CSCI"
    """Computer Software Configuration Item."""
    HWCI = "HWCI"
    """Hardware Configuration Item."""
    INTERFACE_CI = "InterfaceCI"
    """Interface Configuration Item."""
    NDICI = "NDICI"
    """Non Developmental Configuration Item."""
    PRIME_ITEM_CI = "PrimeItemCI"
    """Prime Item Configuration Item."""
    SYSTEM_CI = "SystemCI"
    """System Configuration Item."""


@_enum.unique
class ControlNodeKind(_StringyEnumMixin, _enum.Enum):
    OR = "OR"
    AND = "AND"
    ITERATE = "ITERATE"


@_enum.unique
class ElementKind(_StringyEnumMixin, _enum.Enum):
    """The visibility options for features of a class."""

    TYPE = "TYPE"
    """The ExchangeItemElement is a type for its ExchangeItem."""
    MEMBER = "MEMBER"
    """The ExchangeItemElement is a member for its ExchangeItem."""


@_enum.unique
class ExchangeMechanism(_StringyEnumMixin, _enum.Enum):
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


@_enum.unique
class FunctionalChainKind(_StringyEnumMixin, _enum.Enum):
    """The kind of a Functional Chain."""

    SIMPLE = "SIMPLE"
    COMPOSITE = "COMPOSITE"
    FRAGMENT = "FRAGMENT"


@_enum.unique
class FunctionKind(_StringyEnumMixin, _enum.Enum):
    """The kind of a Function."""

    FUNCTION = "FUNCTION"
    DUPLICATE = "DUPLICATE"
    GATHER = "GATHER"
    SELECT = "SELECT"
    SPLIT = "SPLIT"
    ROUTE = "ROUTE"


@_enum.unique
class InteractionOperatorKind(_StringyEnumMixin, _enum.Enum):
    UNSET = "UNSET"
    ALT = "ALT"
    OPT = "OPT"
    PAR = "PAR"
    LOOP = "LOOP"
    CRITICAL = "CRITICAL"
    NEG = "NEG"
    ASSERT = "ASSERT"
    STRICT = "STRICT"
    SEQ = "SEQ"
    IGNORE = "IGNORE"
    CONSIDER = "CONSIDER"


@_enum.unique
class MessageKind(_StringyEnumMixin, _enum.Enum):
    """Identifies the type of message.

    This concept is similar to UML ``MessageSort``.
    """

    UNSET = "UNSET"
    """The message kind is not specified."""
    ASYNCHRONOUS_CALL = "ASYNCHRONOUS_CALL"
    """The message was generated by an asynchronous call to an operation.

    Equivalent to UML ``MessageSort::asynchCall``.
    """
    SYNCHRONOUS_CALL = "SYNCHRONOUS_CALL"
    """The message was generated by a synchronous call to an operation.

    Equivalent to UML ``MessageSort::synchCall``.
    """
    REPLY = "REPLY"
    """The message is a reply message to an operation call.

    Equivalent to UML ``MessageSort::reply``.
    """
    DELETE = "DELETE"
    """The message designates the termination of another lifeline.

    Equivalent to UML ``MessageSort::deleteMessage``.
    """
    CREATE = "CREATE"
    """The message designates the creation of an instance role."""
    TIMER = "TIMER"


@_enum.unique
class NumericTypeKind(_StringyEnumMixin, _enum.Enum):
    """The kind of this numeric data type."""

    INTEGER = "INTEGER"
    FLOAT = "FLOAT"


@_enum.unique
class ObjectNodeKind(_StringyEnumMixin, _enum.Enum):
    """The behavior type of the object node with respect to incoming data."""

    UNSPECIFIED = "Unspecified"
    """Used when incoming object node management policy is not specified."""
    NO_BUFFER = "NoBuffer"
    """Discard incoming tokens if they are refused.

    When the "nobuffer" stereotype is applied to object nodes, tokens
    arriving at the node are discarded if they are refused by outgoing
    edges, or refused by actions for object nodes that are input pins.
    """
    OVERWRITE = "Overwrite"
    """Incoming tokens may overwrite existing ones.

    When the "overwrite" stereotype is applied to object nodes, a token
    arriving at a full object node replaces the ones already there. A
    full object node has as many tokens as allowed by its upper bound.
    """


@_enum.unique
class ObjectNodeOrderingKind(_StringyEnumMixin, _enum.Enum):
    """Indicates queuing order within a node."""

    FIFO = "FIFO"
    """First In First Out ordering."""
    LIFO = "LIFO"
    """Last In First Out ordering."""
    ORDERED = "ordered"
    """Indicates that object node tokens are ordered."""
    UNORDERED = "unordered"
    """Indicates that object node tokens are unordered."""


@_enum.unique
class OrientationPortKind(_StringyEnumMixin, _enum.Enum):
    """Direction of component ports."""

    UNSET = "UNSET"
    """The port orientation is undefined."""
    IN = "IN"
    """The port represents an input of the component it is used in."""
    OUT = "OUT"
    """The port represents an output of the component it is used in."""
    INOUT = "INOUT"
    """The port represents both an input and on output of the component."""


@_enum.unique
class ParameterDirection(_StringyEnumMixin, _enum.Enum):
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


@_enum.unique
class ParameterEffectKind(_StringyEnumMixin, _enum.Enum):
    """A behavior's effect on values passed in or out of its parameters."""

    CREATE = "create"
    """The parameter value is being created upon behavior execution."""
    READ = "read"
    """The parameter value is only being read upon behavior execution."""
    UPDATE = "update"
    """The parameter value is being updated upon behavior execution."""
    DELETE = "delete"
    """The parameter value is being deleted upon behavior execution."""


@_enum.unique
class PassingMode(_StringyEnumMixin, _enum.Enum):
    """The data passing mechanism for parameters of an operation."""

    UNSET = "UNSET"
    """The data passing mechanism is not precised."""
    BY_REF = "BY_REF"
    """The data is being passed by reference to the operation."""
    BY_VALUE = "BY_VALUE"
    """The data is being passed by value to the operation."""


@_enum.unique
class PhysicalComponentKind(_StringyEnumMixin, _enum.Enum):
    """Categories of physical components.

    Allows to categorize a physical component, with respect to real life
    physical entities.
    """

    UNSET = "UNSET"
    """The physical component kind is not specified."""
    HARDWARE = "HARDWARE"
    """The physical component is a hardware resource."""
    HARDWARE_COMPUTER = "HARDWARE_COMPUTER"
    """The physical component is a computing resource."""
    SOFTWARE = "SOFTWARE"
    """The physical component is a software entity."""
    SOFTWARE_DEPLOYMENT_UNIT = "SOFTWARE_DEPLOYMENT_UNIT"
    """The physical component is a software deployment unit."""
    SOFTWARE_EXECUTION_UNIT = "SOFTWARE_EXECUTION_UNIT"
    """The physical component is a software execution unit."""
    SOFTWARE_APPLICATION = "SOFTWARE_APPLICATION"
    """The physical component is a software application."""
    FIRMWARE = "FIRMWARE"
    """The physical component is a firmware part."""
    PERSON = "PERSON"
    """The physical component is a person."""
    FACILITIES = "FACILITIES"
    """The physical component refers to Facilities."""
    DATA = "DATA"
    """The physical component represents a set of data."""
    MATERIALS = "MATERIALS"
    """The physical component represents a bunch of materials."""
    SERVICES = "SERVICES"
    """The physical component represents a set of services."""
    PROCESSES = "PROCESSES"
    """The physical component represents a set of processes."""


@_enum.unique
class PhysicalComponentNature(_StringyEnumMixin, _enum.Enum):
    """The nature of a physical component."""

    UNSET = "UNSET"
    """The physical component nature is not specified."""
    BEHAVIOR = "BEHAVIOR"
    """The physical component nature is behavioral.

    This typically means a piece of software.
    """
    NODE = "NODE"
    """The physical component is a host for behavioral components.

    This typically means a computing resource.
    """


@_enum.unique
class RateKind(_StringyEnumMixin, _enum.Enum):
    """The possible caracterizations for the rate of a streaming parameter."""

    UNSPECIFIED = "Unspecified"
    """The rate kind is not specified."""
    CONTINUOUS = "Continuous"
    """The rate characterizes a continuous flow."""
    DISCRETE = "Discrete"
    """The rate characterizes a discrete flow."""


@_enum.unique
class ScenarioKind(_StringyEnumMixin, _enum.Enum):
    UNSET = "UNSET"
    INTERFACE = "INTERFACE"
    DATA_FLOW = "DATA_FLOW"
    INTERACTION = "INTERACTION"
    FUNCTIONAL = "FUNCTIONAL"


@_enum.unique
class SynchronismKind(_StringyEnumMixin, _enum.Enum):
    """The synchronicity of an operation invocation."""

    UNSET = "UNSET"
    SYNCHRONOUS = "SYNCHRONOUS"
    ASYNCHRONOUS = "ASYNCHRONOUS"


@_enum.unique
class TimeEventKind(_StringyEnumMixin, _enum.Enum):
    AT = "AT"
    """Trigger at a specific time.

    An absolute time trigger is specified with the keyword 'at' followed
    by an expression that evaluates to a time value, such as 'Jan. 1,
    2000, Noon'.
    """
    AFTER = "AFTER"
    """Trigger after a relative time duration has passed.

    A relative time trigger is specified with the keyword 'after'
    followed by an expression that evaluates to a time value, such as
    'after (5 seconds)'.
    """


@_enum.unique
class TransitionKind(_StringyEnumMixin, _enum.Enum):
    INTERNAL = "internal"
    LOCAL = "local"
    EXTERNAL = "external"


@_enum.unique
class UnaryOperator(_StringyEnumMixin, _enum.Enum):
    """The operator of a unary expression."""

    UNSET = "UNSET"
    """The unary operator is not initialized."""
    NOT = "NOT"
    """The unary operator refers to a NOT operation."""
    POS = "POS"
    """The unary operator refers to a position operation."""
    VAL = "VAL"
    """The unary operator refers to a value operation."""
    SUC = "SUC"
    """The unary operator refers to a successor operation."""
    PRE = "PRE"
    """The unary operator refers to a predecessor operation."""


@_enum.unique
class UnionKind(_StringyEnumMixin, _enum.Enum):
    UNION = "UNION"
    VARIANT = "VARIANT"


@_enum.unique
class VisibilityKind(_StringyEnumMixin, _enum.Enum):
    """The possibilities regarding the visibility of a feature of a class."""

    UNSET = "UNSET"
    """Visibility is not specified."""
    PUBLIC = "PUBLIC"
    """The feature offers public access."""
    PROTECTED = "PROTECTED"
    """The feature offers visibility only to children of the class."""
    PRIVATE = "PRIVATE"
    """The feature is only visible/accessible from the class itself."""
    PACKAGE = "PACKAGE"
    """The feature is accessible from any element within the same package."""
