# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Tools for handling ReqIF Requirements."""

import typing as t
import warnings

from ._glue import *
from .capellarequirements import *
from .requirements import *

from .capellarequirements import NS as CapellaRequirementsNS  # isort: skip
from .requirements import NS as RequirementsNS  # isort: skip

if not t.TYPE_CHECKING:
    from .capellarequirements import __all__ as _cr_all
    from .requirements import __all__ as _rq_all

    __all__ = [
        "CapellaRequirementsNS",
        "RequirementsNS",
        *_cr_all,
        *_rq_all,
        "AbstractRequirementsAttribute",
        "AbstractRequirementsRelation",
    ]
    del _cr_all, _rq_all

    def __getattr__(name):
        if name == "AbstractRequirementsAttribute":
            warnings.warn(
                "AbstractRequirementsAttribute has been renamed to Attribute",
                FutureWarning,
                stacklevel=2,
            )
            return Attribute

        if name == "AbstractRequirementsRelation":
            warnings.warn(
                "AbstractRequirementsRelation has been renamed to AbstractRelation",
                FutureWarning,
                stacklevel=2,
            )
            return AbstractRelation

        raise AttributeError(f"{__name__} has no attribute {name}")


del t
