# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""The MelodyLoader loads and provides access to a Capella model.

It is using LXML internally to efficiently parse and navigate through
the Capella-generated XML files. For more information about LXML, see
the `LXML Documentation`_.

.. _LXML Documentation: https://lxml.de/
"""

from .core import *
from .modelinfo import ModelInfo as ModelInfo
