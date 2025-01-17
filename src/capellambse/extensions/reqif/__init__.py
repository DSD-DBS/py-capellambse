# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Tools for handling ReqIF Requirements.

.. diagram:: [CDB] Requirements ORM
"""

import typing as t

from ._capellareq import *
from ._glue import *
from ._requirements import *

from ._capellareq import NS as CapellaRequirementsNS  # isort: skip
from ._requirements import NS as RequirementsNS  # isort: skip

if not t.TYPE_CHECKING:
    from ._capellareq import __all__ as _cr_all
    from ._requirements import __all__ as _rq_all

    __all__ = [
        "CapellaRequirementsNS",
        "RequirementsNS",
        *_cr_all,
        *_rq_all,
    ]
    del _cr_all, _rq_all
del t
