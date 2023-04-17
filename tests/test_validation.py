# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

import pytest

import capellambse
from capellambse import helpers
from capellambse.extensions import validation as v
from capellambse.model.layers import la

HOGWARTS_UUID = helpers.UUIDString("0d2edb8f-fa34-4e73-89ec-fb9a63001440")


@pytest.mark.parametrize(
    "category",
    [
        v.Category.REQUIRED,
        v.Category.RECOMMENDED,
        v.Category.SUGGESTED,
    ],
)
def test_ValidationRule_discovery(
    model: capellambse.MelodyModel, category: v.Category
):
    name = "Always True"

    @v.register_rule(
        category=category,
        types=[la.LogicalFunction],
        id="R1",
        name=name,
        rationale="True",
        action="Nothing",
        applicable_to="Nothing",
    )
    def always_true(_):
        return True

    assert category in model.validation.rules
    assert (rules := model.validation.rules[category][la.LogicalFunction])
    assert rules[0].name == name
    assert rules[0].id == "R1"


def test_MelodyModel_rules_access(
    model: capellambse.MelodyModel,
):  # pylint: disable=[unused-argument]
    """Test convenient access of MelodyModel rules with by_id,... ."""
    # TODO


def test_ModelObject_rules_access(
    model: capellambse.MelodyModel,
):  # pylint: disable=[unused-argument]
    """Test convenient access of ModelObject rules with by_id,... ."""
    # TODO


def test_MelodyModel_validation(model: capellambse.MelodyModel):
    assert isinstance(model.validation, v.ModelValidation)
    assert model.validation.rules

    results = model.validate()

    assert results


@pytest.mark.parametrize("rule_id", ["Rule-001"])
def test_MelodyModel_validation_access(
    model: capellambse.MelodyModel, rule_id: str
):
    assert isinstance(model.validation, v.ModelValidation)
    assert model.validation.rules

    results = model.validate(rule=rule_id)

    assert len(results.by_uuid(HOGWARTS_UUID)[rule_id]) == 1
    assert len(results.by_value(True)[rule_id]) == 4
    assert len(results.by_category(v.Category.REQUIRED)[rule_id]) == 17


def test_ModelObject_validation(model: capellambse.MelodyModel):
    obj = model.by_uuid(HOGWARTS_UUID)
    assert isinstance(obj.validation, v.ElementValidation)
    assert obj.validation.rules

    results = obj.validate()

    assert results


@pytest.mark.parametrize("rule_id", ["Rule-001"])
def test_MelodyObject_validation_access(
    model: capellambse.MelodyModel, rule_id: str
):
    obj = model.by_uuid(HOGWARTS_UUID)
    assert isinstance(obj.validation, v.ElementValidation)
    assert obj.validation.rules

    results = obj.validate(rule=rule_id)

    assert len(results[rule_id]) == 1
    assert results[rule_id][HOGWARTS_UUID]


# TODO: Test runtime for large models (50k+) to access results and rules
