# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""The Capella modeller module."""
from __future__ import annotations

import typing as t

from capellambse import modelv2 as m

from . import capellacore
from . import namespaces as ns

if t.TYPE_CHECKING:
    from . import epbs, la, oa, pa, sa

NS = ns.CAPELLAMODELLER


class Project(capellacore.Structure):
    key_value_pairs = m.Containment["capellacore.KeyValue"](
        "keyValuePairs", (ns.CAPELLACORE, "KeyValue")
    )
    folders = m.Containment["Folder"]("ownedFolders", (NS, "Folder"))
    model_roots = m.Containment["ModelRoot"](
        "ownedModelRoots", (NS, "ModelRoot")
    )
    model_root = m.Single["SystemEngineering"](
        m.TypeFilter("model_roots", (NS, "SystemEngineering")),
        enforce=False,
    )


class Folder(capellacore.Structure):
    folders = m.Containment["Folder"]("ownedFolders", (NS, "Folder"))
    model_roots = m.Containment["ModelRoot"](
        "ownedModelRoots", (NS, "ModelRoot")
    )


class ModelRoot(capellacore.CapellaElement, abstract=True):
    """A system engineering element or a package of those."""


class SystemEngineering(capellacore.AbstractModellingStructure, ModelRoot):
    """A system engineering element.

    System engineering is an interdisciplinary approach encompassing the entire
    technical effort to evolve and verify an integrated and life-cycle balanced
    set of system people, product, and process solutions that satisfy customer
    needs.

    Systems engineering encompasses:

    - the technical efforts related to the development, manufacturing,
      verification, deployment, operations, support, disposal of, and user
      training for, systems products and processes;
    - the definition and management of the system configuration;
    - the translation of the system definition into work breakdown structures;
    - and development of information for management decision making.

    [source:MIL-STD 499B standard]
    """

    oa = m.Single["oa.OperationalAnalysis"](
        m.TypeFilter("architectures", (ns.OA, "OperationalAnalysis")),
        enforce=False,
    )
    sa = m.Single["sa.SystemAnalysis"](
        m.TypeFilter("architectures", (ns.SA, "SystemAnalysis")),
        enforce=False,
    )
    la = m.Single["la.LogicalArchitecture"](
        m.TypeFilter("architectures", (ns.LA, "LogicalArchitecture")),
        enforce=False,
    )
    pa = m.Single["pa.PhysicalArchitecture"](
        m.TypeFilter("architectures", (ns.PA, "PhysicalArchitecture")),
        enforce=False,
    )
    epbs = m.Single["epbs.EPBSArchitecture"](
        m.TypeFilter("architectures", (ns.EPBS, "EPBSArchitecture")),
        enforce=False,
    )


class SystemEngineeringPkg(capellacore.Structure, ModelRoot):
    """A package that contains system engineering elements."""


class Library(Project):
    """A project that is primarily intended as a library of components."""
