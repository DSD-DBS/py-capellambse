# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Some additional glue to tie ReqIF into capellambse."""

__all__ = ["init"]

from capellambse.model import common as c
from capellambse.model import crosslayer

from . import _capellareq as cr
from . import _requirements as rq


def init() -> None:
    c.set_accessor(
        rq.Folder,
        "folders",
        c.DirectProxyAccessor(rq.Folder, aslist=c.ElementList),
    )
    c.set_accessor(
        c.GenericElement, "requirements", cr.ElementRelationAccessor()
    )
    c.set_accessor(
        crosslayer.BaseArchitectureLayer,
        "requirement_modules",
        c.DirectProxyAccessor(cr.CapellaModule, aslist=c.ElementList),
    )
    c.set_accessor(
        crosslayer.BaseArchitectureLayer,
        "all_requirements",
        c.DeepProxyAccessor(
            rq.Requirement, aslist=c.ElementList, rootelem=cr.CapellaModule
        ),
    )
    c.set_accessor(
        crosslayer.BaseArchitectureLayer,
        "requirement_types_folders",
        c.DirectProxyAccessor(cr.CapellaTypesFolder, aslist=c.ElementList),
    )
    c.set_accessor(
        cr.CapellaModule,
        "requirement_types_folders",
        c.DirectProxyAccessor(cr.CapellaTypesFolder, aslist=c.ElementList),
    )
    c.set_accessor(
        crosslayer.BaseArchitectureLayer,
        "all_requirement_types",
        c.DeepProxyAccessor(
            rq.RequirementType,
            aslist=c.ElementList,
            rootelem=cr.CapellaTypesFolder,
        ),
    )
    c.set_accessor(
        crosslayer.BaseArchitectureLayer,
        "all_module_types",
        c.DeepProxyAccessor(
            rq.ModuleType, aslist=c.ElementList, rootelem=cr.CapellaTypesFolder
        ),
    )
    c.set_accessor(
        crosslayer.BaseArchitectureLayer,
        "all_relation_types",
        c.DeepProxyAccessor(
            rq.RelationType,
            aslist=c.ElementList,
            rootelem=cr.CapellaTypesFolder,
        ),
    )
