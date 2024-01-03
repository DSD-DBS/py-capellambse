# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Provides easy access to the Polarsys Capella PVMT extension.

The public API of this submodule uses raw LXML elements. For a more
object oriented and user friendly way to access property values in a
model, see the :class:`capellambse.MelodyModel` class.
"""

from .exceptions import ScopeError
from .model import PVMTExtension, load_pvmt_from_model
