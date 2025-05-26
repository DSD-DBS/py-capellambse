# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Some additional glue to tie ReqIF into capellambse."""

__all__ = ["init"]

import capellambse.model as m
from capellambse.metamodel import cs

from . import capellarequirements as cr
from . import requirements as rq


def init() -> None:
    cr.CapellaModule.requirement_types_folders = m.DirectProxyAccessor(  # TODO
        cr.CapellaTypesFolder, aslist=m.ElementList
    )

    m.ModelElement.requirements = cr.ElementRelationAccessor()
    cs.BlockArchitecture.requirement_modules = m.DirectProxyAccessor(
        cr.CapellaModule, aslist=m.ElementList
    )
    cs.BlockArchitecture.requirement_types_folders = m.DirectProxyAccessor(
        cr.CapellaTypesFolder, aslist=m.ElementList
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
