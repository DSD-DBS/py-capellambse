# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import capellambse.model as m

from . import capellacore
from . import namespaces as ns

NS = ns.CAPELLAMODELLER


class Project(capellacore.Structure):
    key_value_pairs = m.Containment["capellacore.KeyValue"](
        "keyValuePairs", (ns.CAPELLACORE, "KeyValue")
    )
    folders = m.Containment["Folder"]("ownedFolders", (NS, "Folder"))
    model_roots = m.Containment["ModelRoot"](
        "ownedModelRoots", (NS, "ModelRoot")
    )

    @property
    def model_root(self) -> ModelRoot:
        if self.model_roots:
            return self.model_roots[0]
        return self.model_roots.create("SystemEngineering")


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

    @property
    def oa(self) -> oa.OperationalAnalysis:
        from . import oa  # noqa: PLC0415

        try:
            return next(
                i
                for i in self.architectures
                if isinstance(i, oa.OperationalAnalysis)
            )
        except StopIteration:
            raise AttributeError(
                f"OperationalAnalysis not found on {self._short_repr_()}"
            ) from None

    @property
    def sa(self) -> sa.SystemAnalysis:
        from . import sa  # noqa: PLC0415

        try:
            return next(
                i
                for i in self.architectures
                if isinstance(i, sa.SystemAnalysis)
            )
        except StopIteration:
            raise AttributeError(
                f"SystemAnalysis not found on {self._short_repr_()}"
            ) from None

    @property
    def la(self) -> la.LogicalArchitecture:
        from . import la  # noqa: PLC0415

        try:
            return next(
                i
                for i in self.architectures
                if isinstance(i, la.LogicalArchitecture)
            )
        except StopIteration:
            raise AttributeError(
                f"LogicalArchitecture not found on {self._short_repr_()}"
            ) from None

    @property
    def pa(self) -> pa.PhysicalArchitecture:
        from . import pa  # noqa: PLC0415

        try:
            return next(
                i
                for i in self.architectures
                if isinstance(i, pa.PhysicalArchitecture)
            )
        except StopIteration:
            raise AttributeError(
                f"PhysicalArchitecture not found on {self._short_repr_()}"
            ) from None

    @property
    def epbs(self) -> epbs.EPBSArchitecture:
        from . import epbs  # noqa: PLC0415

        try:
            return next(
                i
                for i in self.architectures
                if isinstance(i, epbs.EPBSArchitecture)
            )
        except StopIteration:
            raise AttributeError(
                f"EPBSArchitecture not found on {self._short_repr_()}"
            ) from None


class SystemEngineeringPkg(capellacore.Structure, ModelRoot):
    """A package that contains system engineering elements."""

    system_engineerings = m.Containment["SystemEngineering"](
        "ownedSystemEngineerings", (NS, "SystemEngineering")
    )


class Library(Project):
    """A project that is primarily intended as a library of components."""


from . import epbs, la, oa, pa, sa
