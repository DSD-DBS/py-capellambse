# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
import enum

from . import namespaces as ns

NS = ns.LIBRARIES


@enum.unique
class AccessPolicy(enum.Enum):
    READ_ONLY = "readOnly"
    READ_AND_WRITE = "readAndWrite"
