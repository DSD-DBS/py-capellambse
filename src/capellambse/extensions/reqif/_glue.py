# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Some additional glue to tie ReqIF into capellambse."""

__all__ = ["init"]

import capellambse.model as m
from capellambse.metamodel import cs

from . import capellarequirements as cr
from . import requirements as rq


def init() -> None:
    m.ModelElement.requirements = cr.ElementRelationAccessor()  # type: ignore[deprecated]
    m.ModelElement.requirements_relations = m.Backref[rq.AbstractRelation](
        (rq.NS, "AbstractRelation"), "source", "target"
    )
    cs.BlockArchitecture.requirement_modules = m.Filter(
        "extensions", (cr.NS, "CapellaModule")
    )
    cs.BlockArchitecture.requirement_types_folders = m.Filter(
        "extensions", (cr.NS, "CapellaTypesFolder")
    )

    cs.BlockArchitecture.all_requirements = property(
        lambda self: self._model.search((rq.NS, "Requirement"), below=self)
    )
    cs.BlockArchitecture.all_requirement_types = property(
        lambda self: self._model.search((rq.NS, "RequirementType"), below=self)
    )
    cs.BlockArchitecture.all_module_types = property(
        lambda self: self._model.search((rq.NS, "ModuleType"), below=self)
    )
    cs.BlockArchitecture.all_relation_types = property(
        lambda self: self._model.search((rq.NS, "RelationType"), below=self)
    )
