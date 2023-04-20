# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
"""The module provides management and evaluation of validation rules.

Validation rules are conditions ensuring that specific modeling
guidelines are followed. These rules apply to particular types of model
elements or to diagrams, and values of metrics. By evaluating each rule,
the module generates validation results, indicating whether the
corresponding guideline has been satisfied or not. This way, the module
helps maintain the quality and consistency of the model.
"""

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
