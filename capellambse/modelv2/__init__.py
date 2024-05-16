# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Implementation of the Capella model and its elements."""

__import__("warnings").warn(
    (
        f"The {__name__} module is experimental and may change at any time."
        " Productive use is not yet recommended. Use at your own risk."
    ),
    UserWarning,
    stacklevel=2,
)

import typing as t

from ._meta import *
from ._model import *
from ._obj import *

if not t.TYPE_CHECKING:
    from ._meta import __all__ as _all_1
    from ._model import __all__ as _all_2
    from ._obj import __all__ as _all_3

    __all__ = [*_all_1, *_all_2, *_all_3]
del t
