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
"""Enumeration types used by the MelodyModel."""
import enum as _enum


class StringyEnum(_enum.Enum):
    """An enum whose members compare equal to their key name string."""

    def __eq__(self, other: object) -> bool:
        if isinstance(other, type(self)):
            return self is other
        if isinstance(other, str):
            return self.name == other
        return NotImplemented

    def __str__(self) -> str:
        return str(self.name)


class DiagramType(StringyEnum):
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
    LFCD = "Functional Chain Description"
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
class FPortDir(StringyEnum, _enum.Flag):
    """Direction of component and function ports."""

    IN = _enum.auto()
    OUT = _enum.auto()
    INOUT = IN | OUT


@_enum.unique
class ExchangeItemType(StringyEnum):
    r"""The "TYPE" of ``ExchangeItem``\ s."""

    UNSET = _enum.auto()
    EVENT = _enum.auto()
    FLOW = _enum.auto()
    OPERATION = _enum.auto()
    SHARED_DATA = _enum.auto()
