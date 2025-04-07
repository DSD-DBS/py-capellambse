# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Some additional glue to tie ReqIF into capellambse."""

__all__ = ["init"]

import capellambse.model as m
from capellambse.metamodel import cs

from . import _capellareq as cr
from . import _requirements as rq


def init() -> None:
    rq.Folder.folders = m.DirectProxyAccessor(rq.Folder, aslist=m.ElementList)
    m.ModelElement.requirements = cr.ElementRelationAccessor()
    cs.ComponentArchitecture.requirement_modules = m.DirectProxyAccessor(
        cr.CapellaModule, aslist=m.ElementList
    )
    cs.ComponentArchitecture.all_requirements = m.DeepProxyAccessor(
        rq.Requirement, aslist=m.ElementList, rootelem=cr.CapellaModule
    )
    cs.ComponentArchitecture.requirement_types_folders = m.DirectProxyAccessor(
        cr.CapellaTypesFolder, aslist=m.ElementList
    )
    cr.CapellaModule.requirement_types_folders = m.DirectProxyAccessor(
        cr.CapellaTypesFolder, aslist=m.ElementList
    )
    cs.ComponentArchitecture.all_requirement_types = m.DeepProxyAccessor(
        rq.RequirementType,
        aslist=m.ElementList,
        rootelem=cr.CapellaTypesFolder,
    )
    cs.ComponentArchitecture.all_module_types = m.DeepProxyAccessor(
        rq.ModuleType, aslist=m.ElementList, rootelem=cr.CapellaTypesFolder
    )
    cs.ComponentArchitecture.all_relation_types = m.DeepProxyAccessor(
        rq.RelationType,
        aslist=m.ElementList,
        rootelem=cr.CapellaTypesFolder,
    )
