# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

import warnings

warnings.warn(
    "{__name__} is deprecated, use capellambse.diagram instead",
    DeprecationWarning,
    stacklevel=2,
)
del warnings

# pylint: disable=unused-wildcard-import, wildcard-import
from capellambse.diagram import *
from capellambse.diagram._diagram import __all__
