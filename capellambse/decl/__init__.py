# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
"""Support for YAML-based declarative modelling.

A YAML-based approach to describing how to create and modify
``capellambse`` compatible models.

For an in-depth explanation, please refer to the :ref:`full
documentation about declarative modelling <declarative-modelling>`.
"""
from __future__ import annotations

__all__ = [
    "Promise",
    "UUIDReference",
    "UnfulfilledPromisesError",
    "YDMDumper",
    "YDMLoader",
    "apply",
    "dump",
    "load",
    "diff",
]


from capellambse.decl._decl import *
from capellambse.decl.diff import *
