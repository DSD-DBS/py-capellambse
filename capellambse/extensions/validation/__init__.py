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

from . import rules as rules  # isort: skip


def init() -> None:
    import capellambse
    import capellambse.model as m
    from capellambse.metamodel import cs

    capellambse.MelodyModel.validation = property(  # type: ignore[attr-defined]
        ModelValidation
    )
    capellambse.MelodyModel.validate = property(  # type: ignore[attr-defined]
        lambda self: self.validation.validate
    )

    m.set_accessor(
        m.ModelElement, "validation", m.AlternateAccessor(ElementValidation)
    )
    m.ModelElement.validate = property(  # type: ignore[attr-defined]
        lambda self: self.validation.validate
    )
    m.set_accessor(
        cs.ComponentArchitecture,
        "validation",
        m.AlternateAccessor(LayerValidation),
    )
