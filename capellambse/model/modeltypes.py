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
class CollectionKind(_StringyEnumMixin, _enum.Enum):
    """Defines the specific kind of a Collection structure."""

    ARRAY = "ARRAY"
    """The collection is to be considered an array of elements."""
    SEQUENCE = "SEQUENCE"
    """The collection is to be considered as a sequence (list) of elements."""


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
class ControlNodeKind(_StringyEnumMixin, _enum.Enum):
    OR = "OR"
    AND = "AND"
    ITERATE = "ITERATE"


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
class NumericTypeKind(_StringyEnumMixin, _enum.Enum):
    """The kind of this numeric data type."""

    INTEGER = "INTEGER"
    FLOAT = "FLOAT"


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
class ScenarioKind(_StringyEnumMixin, _enum.Enum):
    UNSET = "UNSET"
    INTERFACE = "INTERFACE"
    DATA_FLOW = "DATA_FLOW"
    INTERACTION = "INTERACTION"
    FUNCTIONAL = "FUNCTIONAL"


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


if not t.TYPE_CHECKING:
    __replaced_names = {
        "ExchangeItemType": ExchangeMechanism,
        "Kind": PhysicalComponentKind,
        "Nature": PhysicalComponentNature,
        "FPortDir": OrientationPortKind,
    }

    def __getattr__(name):
        if replacement := __replaced_names.get(name):
            import warnings

            warnings.warn(
                f"{name} is deprecated; use {replacement.__name__} instead",
                DeprecationWarning,
                stacklevel=2,
            )
            return replacement
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
