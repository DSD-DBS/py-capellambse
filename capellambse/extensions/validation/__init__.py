# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""The module provides management and evaluation of validation rules.

Validation rules are conditions ensuring that specific modeling
guidelines are followed. These rules apply to particular types of model
elements or to diagrams, and values of metrics. By evaluating each rule,
the module generates validation results, indicating whether the
corresponding guideline has been satisfied or not. This way, the module
helps maintain the quality and consistency of the model.
"""

from ._validate import *

from . import rules  # isort: skip


def init() -> None:
    # pylint: disable=redefined-outer-name # false-positive
    import capellambse
    from capellambse.model import common as c

    c.set_accessor(
        capellambse.MelodyModel,
        "validation",
        c.AlternateAccessor(ModelValidation),
    )
    capellambse.MelodyModel.validate = property(  # type: ignore[attr-defined]
        lambda self: self.validation.validate
    )

    c.set_accessor(
        c.GenericElement, "validation", c.AlternateAccessor(ElementValidation)
    )
    c.GenericElement.validate = property(  # type: ignore[attr-defined]
        lambda self: self.validation.validate
    )
