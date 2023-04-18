# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

import capellambse
from capellambse import helpers
from capellambse.extensions import validation as v
from capellambse.model import common as c
from capellambse.model.layers import ctx, la

# pylint: disable-next=relative-beyond-top-level, useless-suppression
from .conftest import INSTALLED_PACKAGE  # type: ignore[import]

TEST_UUID = helpers.UUIDString("da12377b-fb70-4441-8faa-3a5c153c5de2")
TEST_RULE_ID = "Rule-001"
TEST_RULE_PARAMS = {
    "name": "Always True",
    "rationale": "True",
    "action": "Nothing",
    "applicable_to": "Nothing",
}


@pytest.mark.parametrize(
    "category,id",
    [
        (v.Category.REQUIRED, "REQ-1"),
        (v.Category.RECOMMENDED, "REC-1"),
        (v.Category.SUGGESTED, "SUG-1"),
    ],
)
def test_ValidationRule_discovery(
    model: capellambse.MelodyModel, category: v.Category, id: str
):
    expected = dict(TEST_RULE_PARAMS, id=id)

    @v.register_rule(category=category, types=[la.LogicalFunction], **expected)
    def always_true(_):
        return True

    rules = model.validation.rules[category]

    assert rules
    assert (rule := rules.by_type(la.LogicalFunction).by_id(id))
    for attr, expected_value in expected.items():
        assert getattr(rule, attr) == expected_value


@pytest.mark.parametrize(
    "types,id",
    [
        ([la.LogicalComponent, la.LogicalFunction], "RLA-1"),
        ([la.LogicalComponent, "LogicalFunction"], "RLAS-1"),
        ([ctx.SystemComponent, la.LogicalComponent], "RMIX-1"),
    ],
)
def test_ValidationRule_register_multiple_types(
    model: capellambse.MelodyModel,
    types: list[type[c.GenericElement] | str],
    id: str,
    monkeypatch: pytest.MonkeyPatch,
):
    expected = dict(TEST_RULE_PARAMS, id=id)
    monkeypatch.setattr(
        v._validate,
        "VALIDATION_RULES",
        v.Rules(
            {
                v.Category.REQUIRED: v.RuleList([]),
                v.Category.RECOMMENDED: v.RuleList([]),
                v.Category.SUGGESTED: v.RuleList([]),
            }
        ),
    )

    @v.register_rule(category=v.Category.REQUIRED, types=types, **expected)
    def always_true(_):
        return True

    rules = model.validation.rules

    assert rules
    for type_ in types:
        assert rules.by_type(type_).by_id(id)


def test_MelodyModel_rules_access(
    model: capellambse.MelodyModel,
):
    """Test convenient access of MelodyModel rules with by_id,... ."""
    rules = model.validation.rules[v.Category.REQUIRED]
    expected = TEST_RULE_ID

    assert rules == model.validation.rules["REQUIRED"]
    assert rules.by_name("Object has a description or summary").id == expected
    assert rules.by_type("SystemComponent").by_id(expected).id == expected
    assert rules.by_type(ctx.SystemComponent).by_id(expected).id == expected
    assert rules.by_category("REQUIRED").by_id(expected).id == expected
    assert (
        rules.by_category(v.Category.REQUIRED).by_id(expected).id == expected
    )


def test_ModelObject_rules_access(
    model: capellambse.MelodyModel,
):
    """Test convenient access of ModelObject rules with by_id,... ."""
    obj = model.by_uuid(TEST_UUID)
    assert isinstance(obj.validation, v.ElementValidation)

    assert obj.validation.rules
    assert (required_rules := obj.validation.rules["REQUIRED"])
    assert required_rules.by_id(TEST_RULE_ID)  # type: ignore[attr-defined]
    assert required_rules.by_category("REQUIRED")


def test_MelodyModel_validation(model: capellambse.MelodyModel):
    assert isinstance(model.validation, v.ModelValidation)
    assert model.validation.rules

    results = model.validate()

    assert results


@pytest.mark.parametrize(
    "params", [pytest.param((TEST_RULE_ID, 1, 1, 13, 13), id=TEST_RULE_ID)]
)
def test_MelodyModel_validation_access(
    model: capellambse.MelodyModel, params: tuple[str, int, int, int, int]
):
    rule_id, uuids, trues, categories, types = params
    assert isinstance(model.validation, v.ModelValidation)
    assert model.validation.rules

    results = model.validate()

    assert len(results.by_uuid(TEST_UUID)) == uuids
    assert len(results.by_value(True)[rule_id]) == trues
    assert len(results.by_category(v.Category.REQUIRED)[rule_id]) == categories
    assert len(results.by_type("SystemComponent")[rule_id]) == types


@pytest.mark.parametrize("type", [None, "SystemComponent"])
def test_get_passed_and_total_results(
    model: capellambse.MelodyModel, type: str | None
):
    assert isinstance(model.validation, v.ModelValidation)
    assert model.validation.rules

    results = model.validate()
    passed, total = v.get_passed_and_total(results, type=type)

    assert isinstance(passed, int) and isinstance(total, int)


def test_ModelObject_validation(model: capellambse.MelodyModel):
    obj = model.by_uuid(TEST_UUID)
    assert isinstance(obj.validation, v.ElementValidation)
    assert obj.validation.rules

    results = obj.validate()

    assert results


@pytest.mark.parametrize("rule_id", [TEST_RULE_ID])
def test_MelodyObject_validation_access(
    model: capellambse.MelodyModel, rule_id: str
):
    obj = model.by_uuid(TEST_UUID)
    assert isinstance(obj.validation, v.ElementValidation)
    assert obj.validation.rules

    results = obj.validate()

    assert len(results) == 1
    assert results[rule_id].uuid == obj.uuid


def test_validation_automatic_result_population(
    model: capellambse.MelodyModel,
):
    assert isinstance(model.validation, v.ModelValidation)
    assert model.validation.rules

    results = model.validation.results

    assert results


# TODO: Test runtime for large models (50k+) to access results and rules


def test_cli_writes_validation_report(tmp_path: pathlib.Path):
    output_file = tmp_path / "report.html"
    cli = subprocess.run(
        [
            sys.executable,
            "-mcapellambse.extensions.validation",
            "-mtest-5.0",
            "-o",
            output_file,
        ],
        cwd=INSTALLED_PACKAGE.parent,
        check=False,
    )

    assert cli.returncode == 0, "CLI process exited unsuccessfully"
    assert output_file.exists() and output_file.read_text(encoding="utf8")
