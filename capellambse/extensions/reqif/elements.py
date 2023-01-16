# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

__all__ = [
    "AbstractRequirementsAttribute",
    "AbstractRequirementsRelation",
    "AbstractType",
    "AttributeDefinition",
    "AttributeDefinitionEnumeration",
    "BooleanValueAttribute",
    "DataTypeDefinition",
    "DateValueAttribute",
    "EnumDataTypeDefinition",
    "EnumValue",
    "EnumerationValueAttribute",
    "IntegerValueAttribute",
    "ModuleType",
    "RealValueAttribute",
    "RelationType",
    "RelationsList",
    "ReqIFElement",
    "Requirement",
    "RequirementType",
    "RequirementsFolder",
    "RequirementsIncRelation",
    "RequirementsIntRelation",
    "RequirementsModule",
    "RequirementsOutRelation",
    "RequirementsTypesFolder",
    "StringValueAttribute",
    "XT_FOLDER",
    "XT_INC_RELATION",
    "XT_INT_RELATION",
    "XT_MODULE",
    "XT_MODULE_TYPE",
    "XT_OUT_RELATION",
    "XT_RELATION_TYPE",
    "XT_REQUIREMENT",
    "XT_REQ_ATTRIBUTES",
    "XT_REQ_ATTR_BOOLEANVALUE",
    "XT_REQ_ATTR_DATEVALUE",
    "XT_REQ_ATTR_ENUMVALUE",
    "XT_REQ_ATTR_INTEGERVALUE",
    "XT_REQ_ATTR_REALVALUE",
    "XT_REQ_ATTR_STRINGVALUE",
    "XT_REQ_TYPE",
    "XT_REQ_TYPES",
    "XT_REQ_TYPES_DATA_DEF",
    "XT_REQ_TYPES_F",
    "XT_REQ_TYPE_ATTR_DEF",
    "XT_REQ_TYPE_ATTR_ENUM",
    "XT_REQ_TYPE_ENUM",
    "XT_REQ_TYPE_ENUM_DEF",
    "init",
]

# pylint: disable=unused-import, wildcard-import

import collections.abc as cabc
import logging
import os
import re
import typing as t

import markupsafe
from lxml import etree

import capellambse.model
import capellambse.model.common as c
from capellambse.loader import xmltools
from capellambse.model import crosslayer

from . import exporter

XT_REQUIREMENT = "Requirements:Requirement"
XT_REQ_ATTR_STRINGVALUE = "Requirements:StringValueAttribute"
XT_REQ_ATTR_REALVALUE = "Requirements:RealValueAttribute"
XT_REQ_ATTR_INTEGERVALUE = "Requirements:IntegerValueAttribute"
XT_REQ_ATTR_DATEVALUE = "Requirements:DateValueAttribute"
XT_REQ_ATTR_BOOLEANVALUE = "Requirements:BooleanValueAttribute"
XT_REQ_ATTR_ENUMVALUE = "Requirements:EnumerationValueAttribute"
XT_REQ_ATTRIBUTES = {
    XT_REQ_ATTR_ENUMVALUE,
    XT_REQ_ATTR_STRINGVALUE,
    XT_REQ_ATTR_REALVALUE,
    XT_REQ_ATTR_INTEGERVALUE,
    XT_REQ_ATTR_DATEVALUE,
    XT_REQ_ATTR_BOOLEANVALUE,
}
XT_INC_RELATION = "CapellaRequirements:CapellaIncomingRelation"
XT_OUT_RELATION = "CapellaRequirements:CapellaOutgoingRelation"
XT_INT_RELATION = "Requirements:InternalRelation"
XT_MODULE = "CapellaRequirements:CapellaModule"
XT_FOLDER = "Requirements:Folder"

XT_REQ_TYPES_F = "CapellaRequirements:CapellaTypesFolder"
XT_REQ_TYPES_DATA_DEF = "Requirements:DataTypeDefinition"
XT_REQ_TYPE = "Requirements:RequirementType"
XT_RELATION_TYPE = "Requirements:RelationType"
XT_MODULE_TYPE = "Requirements:ModuleType"
XT_REQ_TYPE_ENUM = "Requirements:EnumerationDataTypeDefinition"
XT_REQ_TYPE_ATTR_ENUM = "Requirements:EnumValue"
XT_REQ_TYPE_ATTR_DEF = "Requirements:AttributeDefinition"
XT_REQ_TYPE_ENUM_DEF = "Requirements:AttributeDefinitionEnumeration"
XT_REQ_TYPES = {
    XT_REQ_TYPES_F,
    XT_REQ_TYPES_DATA_DEF,
    XT_REQ_TYPE,
    XT_RELATION_TYPE,
    XT_MODULE_TYPE,
    XT_REQ_TYPE_ENUM,
    XT_REQ_TYPE_ATTR_ENUM,
    XT_REQ_TYPE_ATTR_DEF,
    XT_REQ_TYPE_ENUM_DEF,
}

logger = logging.getLogger("reqif")

from . import (
    AbstractRequirementsAttribute,
    AbstractRequirementsRelation,
    AbstractType,
    AttributeDefinition,
    AttributeDefinitionEnumeration,
    BooleanValueAttribute,
)
from . import CapellaIncomingRelation as RequirementsIncRelation
from . import CapellaModule as RequirementsModule
from . import CapellaOutgoingRelation as RequirementsOutRelation
from . import CapellaTypesFolder as RequirementsTypesFolder
from . import DataTypeDefinition, DateValueAttribute
from . import EnumerationDataTypeDefinition as EnumDataTypeDefinition
from . import EnumerationValueAttribute, EnumValue
from . import Folder as RequirementsFolder
from . import IntegerValueAttribute
from . import InternalRelation as RequirementsIntRelation
from . import (
    ModuleType,
    RealValueAttribute,
    RelationsList,
    RelationType,
    ReqIFElement,
    Requirement,
    RequirementType,
    StringValueAttribute,
    init,
)
