# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Enumeration types used by the MelodyModel."""
import enum as _enum
import typing as t


class _StringyEnumMixin:
    """Mixin for enums that makes members compare equal to their key name."""

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


class DiagramType(_StringyEnumMixin, _enum.Enum):
    """The types of diagrams that Capella knows about.

    Extracted from::

        $CAPELLA/eclipse/configuration/org.eclipse.osgi/635/0/.cp/description

    with::

        grep '<ownedRepresentations' *(.) \
        | grep --color=always -P '(?<=name=").*?(?=")'
    """

    UNKNOWN = "(Unknown Diagram Type)"
    # Common
    MSM = "Mode State Machine"
    # Capella Architecture?
    CDI = "Contextual Component Detailed Interfaces"
    CEI = "Contextual Component External Interfaces"
    CII = "Contextual Component Internal Interfaces"
    IDB = "Interfaces Diagram Blank"
    # Requirements?
    CRI = "Contextual Capability Realization Involvement"
    CRB = "Capability Realization Blank"
    PD = "Package Dependencies"
    ID = "Interface Delegations"
    CDB = "Class Diagram Blank"
    IS = "Component Interfaces Scenario"
    ES = "Component Exchanges Scenario"
    FS = "Functional Scenario"
    SFCD = LFCD = PFCD = "Functional Chain Description"
    # State And Mode - Matrix?
    # Contextual State And Mode - Matrix?
    # Modes and States Reference Matrix?
    # Operational Analysis
    # Operational Activities - Requirements?
    OEBD = "Operational Entity Breakdown"
    OAIB = "Operational Activity Interaction Blank"
    OAB = "Operational Entity Blank"
    OABD = "Operational Activity Breakdown"
    ORB = "Operational Role Blank"
    OES = "Operational Interaction Scenario"
    OAS = "Activity Interaction Scenario"
    OPD = "Operational Process Description"
    OCB = "Operational Capabilities Blank"
    # Requirements - Operational Activities?
    COC = "Contextual Operational Capability"
    # System Analysis
    CM = "Contextual Mission"
    MB = "Missions Blank"
    CC = "Contextual Capability"
    MCB = "Missions Capabilities Blank"
    # System Functions - Requirements?
    # System Functions - Operational Activities?
    SFBD = "System Function Breakdown"
    SDFB = "System Data Flow Blank"
    SAB = "System Architecture Blank"
    CSA = "Contextual System Actors"
    # System Actor - Operational Actor?
    # Interfaces - Capabilities?
    # Interfaces - Scenarios?
    # Interfaces - Capabilities and Scenarios?
    # System/Actors - System Functions?
    # Requirements - System Functions?
    # Logical Architecture
    # Logical Functions - Requirements?
    # Logical Components - Requirements?
    # Logical Functions - System Functions?
    # Logical Components - Logical Functions?
    # Logical Architecture Requirement Refinements?
    # Logical Interface - Context Interface?
    # Logical Actor - Context Actor?
    LCBD = "Logical Component Breakdown"
    LFBD = "Logical Function Breakdown"
    LDFB = "Logical Data Flow Blank"
    LAB = "Logical Architecture Blank"
    CRR = "Capability Realization Refinement"
    # Requirements - Logical Functions?
    # Physical Architecture
    # Physical Functions - Requirements?
    # Physical Components - Requirements?
    # Physical Functions - Logical Functions?
    # Physical Components - Logical Components?
    # Physical Components - Physical Functions?
    # Physical Interface - Logical Interface?
    PFBD = "Physical Function Breakdown"
    PDFB = "Physical Data Flow Blank"
    PCBD = "Physical Component Breakdown"
    PAB = "Physical Architecture Blank"
    # Physical Actor - Logical Actor?
    # Requirements - Physical Functions?
    PPD = "Physical Path Description"
    # EPBS
    # Configuration Items - Requirements?
    # Configuration Items - Physical Artifacts?
    # EPBS Requirement Refinements?
    EAB = "EPBS Architecture Blank"
    CIBD = "Configuration Items Breakdown"


class AggregationKind(_StringyEnumMixin, _enum.Enum):
    """Aggregation kind."""

    UNSET = _enum.auto()
    ASSOCIATION = _enum.auto()
    AGGREGATION = _enum.auto()
    COMPOSITION = _enum.auto()


class BinaryOperator(_StringyEnumMixin, _enum.Enum):
    """The operator of a binary expression."""

    UNSET = 0
    ADD = 1
    MUL = 2
    SUB = 3
    DIV = 4
    POW = 5
    MIN = 6
    MAX = 7
    EQU = 8
    IOR = 9
    XOR = 10
    AND = 11


class ChangeEventKind(_StringyEnumMixin, _enum.Enum):
    WHEN = 0


class CollectionKind(_StringyEnumMixin, _enum.Enum):
    ARRAY = 0
    SEQUENCE = 1


class CommunicationLinkKind(_StringyEnumMixin, _enum.Enum):
    UNSET = 0
    PRODUCE = 1
    CONSUME = 2
    SEND = 3
    RECEIVE = 4
    CALL = 5
    EXECUTE = 6
    WRITE = 7
    ACCESS = 8
    ACQUIRE = 9
    TRANSMIT = 10


class CommunicationLinkProtocol(_StringyEnumMixin, _enum.Enum):
    UNSET = 0
    UNICAST = 1
    MULTICAST = 2
    BROADCAST = 3
    SYNCHRONOUS = 4
    ASYNCHRONOUS = 5
    READ = 6
    ACCEPT = 7


class ComponentExchangeKind(_StringyEnumMixin, _enum.Enum):
    """The KIND of a ComponentExchange."""

    UNSET = 0
    DELEGATION = 1
    ASSEMBLY = 2
    FLOW = 3


class ComponentPortKind(_StringyEnumMixin, _enum.Enum):
    STANDARD = 0
    FLOW = 1


class ControlNodeKind(_StringyEnumMixin, _enum.Enum):
    OR = 0
    AND = 1
    ITERATE = 2


class ElementKind(_StringyEnumMixin, _enum.Enum):
    TYPE = 0
    MEMBER = 1


@_enum.unique
class ExchangeMechanism(_StringyEnumMixin, _enum.Enum):
    """Mechanisms for exchanging ExchangeItems."""

    UNSET = 0
    FLOW = 1
    OPERATION = 2
    EVENT = 3
    SHARED_DATA = 4


class FunctionalChainKind(_StringyEnumMixin, _enum.Enum):
    """The kind of a Functional Chain."""

    SIMPLE = _enum.auto()
    COMPOSITE = _enum.auto()
    FRAGMENT = _enum.auto()


class FunctionKind(_StringyEnumMixin, _enum.Enum):
    """The KIND of a Function."""

    FUNCTION = 0
    DUPLICATE = 1
    GATHER = 2
    SELECT = 3
    SPLIT = 4
    ROUTE = 5


class NumericTypeKind(_StringyEnumMixin, _enum.Enum):
    """Specifies the kind of this numeric data type."""

    INTEGER = _enum.auto()
    FLOAT = _enum.auto()


class ObjectNodeKind(_StringyEnumMixin, _enum.Enum):
    UNSPECIFIED = 0
    NO_BUFFER = 1
    OVERWRITE = 2


class ObjectNodeOrderingKind(_StringyEnumMixin, _enum.Enum):
    FIFO = 0
    LIFO = 1
    ORDERED = 2
    UNORDERED = 3


class OrientationPortKind(_StringyEnumMixin, _enum.Enum):
    """Direction of component ports."""

    UNSET = 0
    IN = 1
    OUT = 2
    INOUT = 3


class ParameterDirection(_StringyEnumMixin, _enum.Enum):
    """The direction in which data is passed along through a parameter."""

    IN = 0
    OUT = 1
    INOUT = 2
    RETURN = 3
    EXCEPTION = 4
    UNSET = 5


class ParameterEffectKind(_StringyEnumMixin, _enum.Enum):
    """The effect of a parameter."""

    CREATE = 2
    READ = 0
    UPDATE = 1
    DELETE = 3


class PassingMode(_StringyEnumMixin, _enum.Enum):
    """The passing mode of a parameter."""

    UNSET = 0
    BY_REF = 1
    BY_VALUE = 2


class PhysicalComponentKind(_StringyEnumMixin, _enum.Enum):
    """The kind of a physical component."""

    UNSET = 0
    HARDWARE = 1
    HARDWARE_COMPUTER = 2
    SOFTWARE = 3
    SOFTWARE_DEPLOYMENT_UNIT = 4
    SOFTWARE_EXECUTION_UNIT = 5
    SOFTWARE_APPLICATION = 6
    FIRMWARE = 7
    PERSON = 8
    FACILITIES = 9
    DATA = 10
    MATERIALS = 11
    SERVICES = 12
    PROCESSES = 13


class PhysicalComponentNature(_StringyEnumMixin, _enum.Enum):
    """The nature of a physical component."""

    UNSET = 0
    BEHAVIOR = 1
    NODE = 2


class RateKind(_StringyEnumMixin, _enum.Enum):
    UNSPECIFIED = 0
    CONTINUOUS = 1
    DISCRETE = 2


class ScenarioKind(_StringyEnumMixin, _enum.Enum):
    UNSET = _enum.auto()
    DATA_FLOW = _enum.auto()
    FUNCTIONAL = _enum.auto()
    INTERACTION = _enum.auto()
    INTERFACE = _enum.auto()


class SynchronismKind(_StringyEnumMixin, _enum.Enum):
    """The synchronism kind of a message."""

    UNSET = 0
    SYNCHRONOUS = 1
    ASYNCHRONOUS = 2


class TimeEventKind(_StringyEnumMixin, _enum.Enum):
    AT = 0
    AFTER = 1


class TransitionKind(_StringyEnumMixin, _enum.Enum):
    INTERNAL = 0
    LOCAL = 1
    EXTERNAL = 2


class UnaryOperator(_StringyEnumMixin, _enum.Enum):
    """The operator of a unary expression."""

    UNSET = 0
    NOT = 1
    POS = 2
    VAL = 3
    SUC = 4
    PRE = 5


class UnionKind(_StringyEnumMixin, _enum.Enum):
    UNION = 0
    VARIANT = 1


class VisibilityKind(_StringyEnumMixin, _enum.Enum):
    """Visibility kind."""

    UNSET = _enum.auto()
    PUBLIC = _enum.auto()
    PROTECTED = _enum.auto()
    PRIVATE = _enum.auto()
    PACKAGE = _enum.auto()
