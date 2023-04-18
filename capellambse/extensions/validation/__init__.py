# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

import capellambse
from capellambse.model import common as c

from . import rules
from ._validate import *


def init() -> None:
    c.set_accessor(
        capellambse.MelodyModel,
        "validation",
        c.AlternateAccessor(ModelValidation),
    )
    c.set_accessor(
        c.GenericElement, "validation", c.AlternateAccessor(ElementValidation)
    )
