# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import capellambse.model as m

from . import la, oa, pa, sa


@m.xtype_handler(None)
class SystemEngineering(m.ModelElement):
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

    architectures = m.Containment(
        "ownedArchitectures", m.ModelElement, aslist=m.ElementList
    )

    @property
    def oa(self) -> oa.OperationalAnalysis:
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


@m.xtype_handler(None)
class Project(m.ModelElement):
    model_roots = m.Containment(
        "ownedModelRoots", SystemEngineering, aslist=m.ElementList
    )

    @property
    def model_root(self) -> SystemEngineering:
        if self.model_roots:
            return self.model_roots[0]
        return self.model_roots.create()


@m.xtype_handler(None)
class Library(Project):
    """A project that is primarily intended as a library of components."""
