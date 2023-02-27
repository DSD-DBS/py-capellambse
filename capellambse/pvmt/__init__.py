# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Provides easy access to the Polarsys Capella PVMT extension.

.. deprecated:: 0.5.1

   Use the :class:`~capellambse.MelodyModel` API instead. See the
   :ref:`documentation of the PVMT model extension <pvmt>`.

The public API of this submodule uses raw LXML elements.  For a more
object oriented and user friendly way to access property values in a
model, see the :class:`capellambse.MelodyModel` class.
"""

import warnings

warnings.warn(
    "The 'capellambse.pvmt' module is deprecated, please migrate your code to"
    " use the new API through 'MelodyModel.pvmt' and the 'pvmt' attribute on"
    " model objects",
    DeprecationWarning,
    stacklevel=2,
)
del warnings

from .exceptions import ScopeError
from .model import PVMTExtension, load_pvmt_from_model
