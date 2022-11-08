# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
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
    vars()["M&S"] = "Modes & States"
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
class FPortDir(_StringyEnumMixin, _enum.Flag):
    """Direction of component and function ports."""

    IN = _enum.auto()
    OUT = _enum.auto()
    INOUT = IN | OUT


@_enum.unique
class ExchangeItemType(_StringyEnumMixin, _enum.Enum):
    r"""The "TYPE" of ``ExchangeItem``\ s."""

    UNSET = _enum.auto()
    EVENT = _enum.auto()
    FLOW = _enum.auto()
    OPERATION = _enum.auto()
    SHARED_DATA = _enum.auto()


class Nature(_StringyEnumMixin, _enum.Enum):
    r"""The "NATURE" of ``PhysicalComponent``\ s."""

    NODE = _enum.auto()
    BEHAVIOR = _enum.auto()


class Kind(_StringyEnumMixin, _enum.Enum):
    r"""The "KIND" of ``PhysicalComponent``\ s."""

    UNSET = _enum.auto()
    HARDWARE = _enum.auto()
    PROCESSES = _enum.auto()
    SOFTWARE_DEPLOYMENT_UNIT = _enum.auto()
    DATA = _enum.auto()
    HARDWARE_COMPUTER = _enum.auto()
    SERVICES = _enum.auto()
    SOFTWARE_EXECUTION_UNIT = _enum.auto()
    FACILITIES = _enum.auto()
    MATERIALS = _enum.auto()
    SOFTWARE = _enum.auto()
    FIRMWARE = _enum.auto()
    PERSON = _enum.auto()
    SOFTWARE_APPLICATION = _enum.auto()


class VisibilityKind(_StringyEnumMixin, _enum.Enum):
    """Visibility kind."""

    UNSET = _enum.auto()
    PUBLIC = _enum.auto()
    PROTECTED = _enum.auto()
    PRIVATE = _enum.auto()
    PACKAGE = _enum.auto()


class CollectionKind(_StringyEnumMixin, _enum.Enum):
    ARRAY = _enum.auto()
    SEQUENCE = _enum.auto()


class UnionKind(_StringyEnumMixin, _enum.Enum):
    UNION = _enum.auto()
    VARIANT = _enum.auto()


class AggregationKind(_StringyEnumMixin, _enum.Enum):
    """Aggregation kind."""

    UNSET = _enum.auto()
    ASSOCIATION = _enum.auto()
    AGGREGATION = _enum.auto()
    COMPOSITION = _enum.auto()
