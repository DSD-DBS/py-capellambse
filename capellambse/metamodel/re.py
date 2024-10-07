# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
import enum

from . import namespaces as ns

NS = ns.RE


@enum.unique
class CatalogElementKind(enum.Enum):
    REC = "REC"
    RPL = "RPL"
    REC_RPL = "REC_RPL"
    GROUPING = "GROUPING"
