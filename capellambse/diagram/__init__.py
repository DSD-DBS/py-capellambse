# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Various diagramming related tools.

This module is used to create diagrams, which can then be exported in
various formats (such as SVG).
"""
# isort: off
from ._vector2d import *

from .capstyle import *
from ._diagram import *
from ._json_enc import *
from ._styleclass import *

import typing as t

if not t.TYPE_CHECKING:
    from ._vector2d import __all__ as _all1
    from .capstyle import __all__ as _all2
    from ._diagram import __all__ as _all3
    from ._json_enc import __all__ as _all4
    from ._styleclass import __all__ as _all5

    __all__ = [*_all1, *_all2, *_all3, *_all4, *_all5]

    del _all1, _all2, _all3, _all4, _all5
del t
