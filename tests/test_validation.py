# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import logging
import pathlib
import typing as t

import pytest
from click import testing as clitest

import capellambse
from capellambse import helpers
from capellambse.extensions import validation as v
from capellambse.extensions.validation import __main__
from capellambse.model import common as c
from capellambse.model.layers import ctx, la

TEST_UUID = helpers.UUIDString("da12377b-fb70-4441-8faa-3a5c153c5de2")
TEST_RULE_ID = "Rule-001"
TEST_RULE_PARAMS = {
    "name": "Always True",
    "rationale": "True",
    "action": "Nothing",
    "applicable_to": "Nothing",
}


def setup_validation_rule_register(monkeypatch: pytest.MonkeyPatch):
    """Initialization for validation rule registration tests."""
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


@pytest.mark.parametrize(
    "category,id",
    [
        (v.Category.REQUIRED, "REQ-1"),
        (v.Category.RECOMMENDED, "REC-1"),
        (v.Category.SUGGESTED, "SUG-1"),
    ],
)
def test_ValidationRule_discovery(
    model: capellambse.MelodyModel,
    category: v.Category,
    id: str,
    monkeypatch: pytest.MonkeyPatch,
):
    expected = dict(TEST_RULE_PARAMS, id=id)
    setup_validation_rule_register(monkeypatch)

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
    setup_validation_rule_register(monkeypatch)

    @v.register_rule(category=v.Category.REQUIRED, types=types, **expected)
    def always_true(_):
        return True

    rules = model.validation.rules

    assert rules
    for type_ in types:
        assert rules.by_type(type_).by_id(id)


@pytest.mark.parametrize(
    "types,id",
    [(la.LogicalComponent, "JR-1"), ("LogicalComponent", "JRS-1")],
)
def test_ValidationRule_register(
    model: capellambse.MelodyModel,
    types: type[c.GenericElement] | str,
    id: str,
    monkeypatch: pytest.MonkeyPatch,
):
    expected = dict(TEST_RULE_PARAMS, id=id)
    setup_validation_rule_register(monkeypatch)

    @v.register_rule(category=v.Category.REQUIRED, types=types, **expected)
    def always_true(_):
        return True

    rules = model.validation.rules

    assert rules
    for type_ in [types]:
        assert rules.by_type(type_).by_id(id)


def test_ValidationRule_register_with_same_id_fails(
    model: capellambse.MelodyModel,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    params_ = TEST_RULE_PARAMS.copy()
    del params_["name"]
    params = dict(
        params_, category=v.Category.REQUIRED, types=[la.LogicalComponent]
    )
    setup_validation_rule_register(monkeypatch)

    # pylint: disable=repeated-keyword
    @v.register_rule(
        id=TEST_RULE_ID, name="First", **params  # type: ignore[arg-type]
    )
    def _(_):
        return True

    with caplog.at_level(logging.WARNING):

        @v.register_rule(
            id=TEST_RULE_ID, name="Second", **params  # type: ignore[arg-type]
        )
        def _(_):
            return False

    assert "Second" in caplog.text
    assert TEST_RULE_ID in caplog.text
    assert model.validation.rules.by_category("REQUIRED")
    assert model.validation.rules.by_id(TEST_RULE_ID)


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

    rules = obj.validation.rules

    assert rules and isinstance(rules, v.Rules)
    assert isinstance(rules.by_id(TEST_RULE_ID), v.Rule)
    assert (required_rules := rules["REQUIRED"])
    assert rules.by_category("REQUIRED") == required_rules
    assert isinstance(required_rules, v.RuleList)
    assert isinstance(rules.by_type("SystemComponent"), v.Rules)
    assert required_rules.by_id(TEST_RULE_ID)
    assert required_rules.by_category("REQUIRED")


def test_MelodyModel_validation(model: capellambse.MelodyModel):
    assert isinstance(model.validation, v.ModelValidation)
    assert model.validation.rules

    results = model.validate()

    assert results


def test_MelodyModel_validation_access(model: capellambse.MelodyModel):
    assert isinstance(model.validation, v.ModelValidation)
    assert model.validation.rules

    results = model.validate()

    result: t.Any
    for result in results.by_uuid(TEST_UUID).values():
        assert result.uuid == TEST_UUID

    for result in results.by_value(True).values():
        assert all(result.values())

    for result in results.by_category(v.Category.REQUIRED).values():
        assert all(i.category == v.Category.REQUIRED for i in result.values())

    assert all(
        "SystemComponent" in rule.types
        for rule in results.by_type("SystemComponent")
    )


def test_ModelObject_validation(model: capellambse.MelodyModel):
    obj = model.by_uuid(TEST_UUID)
    assert isinstance(obj.validation, v.ElementValidation)
    assert obj.validation.rules

    results = obj.validate()

    assert results


@pytest.mark.parametrize("rule_id", [TEST_RULE_ID])
def test_ModelObject_validation_access(
    model: capellambse.MelodyModel, rule_id: str
):
    obj = model.by_uuid(TEST_UUID)
    assert isinstance(obj.validation, v.ElementValidation)
    assert obj.validation.rules

    results = obj.validate()

    assert len(results) == 1
    assert results[rule_id].uuid == obj.uuid


def test_validation_result_representation(model: capellambse.MelodyModel):
    obj = model.by_uuid(TEST_UUID)
    assert isinstance(obj.validation, v.ElementValidation)
    assert obj.validation.rules
    expected = (
        "Result(uuid='da12377b-fb70-4441-8faa-3a5c153c5de2', "
        "category=<Category.REQUIRED: 1>value=False, "
        "object=<SystemComponent 'Affleck'"
    )

    results = obj.validate()

    assert repr(results[TEST_RULE_ID]).startswith(expected)


def test_validation_automatic_result_population(
    model: capellambse.MelodyModel,
):
    assert isinstance(model.validation, v.ModelValidation)
    assert model.validation.rules

    results = model.validation.results

    assert results


class TestCLI:
    @staticmethod
    def test_validation_report(tmp_path: pathlib.Path):
        output_file = tmp_path / "report.html"
        runner = clitest.CliRunner()

        result = runner.invoke(
            __main__._main,  # type: ignore[arg-type]
            ["-m", "test-5.0", "-o", str(output_file)],
        )

        assert result.exit_code == 0, "CLI process exited unsuccessfully"
        assert output_file.exists() and output_file.read_text(encoding="utf8")
