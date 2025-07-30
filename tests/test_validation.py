# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import pathlib

import pytest
from click import testing as clitest

import capellambse.metamodel as mm
import capellambse.model as m
from capellambse._scripts import validate as cli_main
from capellambse.extensions import validation

TEST_UUID = "da12377b-fb70-4441-8faa-3a5c153c5de2"
TEST_RULE_ID = "Rule-001"
TEST_RULE_PARAMS = {
    "name": "Always True",
    "rationale": "True",
    "action": "Nothing",
}


@pytest.fixture
def fake_registry(monkeypatch):
    registry = validation.Rules()
    monkeypatch.setattr(validation._validate, "_VALIDATION_RULES", registry)
    return registry


def test_decorated_rules_are_added_to_global_registry(fake_registry):
    @validation.rule(
        TEST_RULE_ID,
        validation.Category.REQUIRED,
        types=[mm.la.LogicalFunction],
        **TEST_RULE_PARAMS,
    )
    def testrule(_):
        return True

    assert list(fake_registry.items()) == [(testrule.id, testrule)]


def test_rules_can_be_filtered_by_object_type(fake_registry):
    @validation.rule(
        TEST_RULE_ID,
        validation.Category.REQUIRED,
        types=[mm.la.LogicalComponent, mm.la.LogicalFunction],
        **TEST_RULE_PARAMS,
    )
    def testrule(_):
        return True

    assert list(fake_registry.items()) == [(testrule.id, testrule)]
    assert fake_registry.by_class(mm.la.LogicalComponent) == [testrule]
    assert fake_registry.by_class(mm.la.LogicalFunction) == [testrule]
    assert fake_registry.by_class(mm.sa.SystemFunction) == []


def test_model_gives_access_to_the_full_set_of_rules(
    model: m.MelodyModel,
) -> None:
    assert len(model.validation.rules) > 0


def test_model_object_gives_access_to_rules_that_apply_to_it(
    model: m.MelodyModel,
):
    obj = model.by_uuid(TEST_UUID)
    assert isinstance(obj.validation, validation.ElementValidation)

    rules = obj.validation.rules

    assert len(rules) > 0
    assert all(rule.applies_to(obj) for rule in rules)


@pytest.mark.usefixtures("fake_registry")
def test_validation_results_filtering(model: m.MelodyModel) -> None:
    @validation.rule(
        "TEST-LC",
        validation.Category.REQUIRED,
        types=[mm.la.LogicalComponent],
        **TEST_RULE_PARAMS,
    )
    def rule_lc(_: m.ModelElement) -> bool:
        return True

    @validation.rule(
        "TEST-LF",
        validation.Category.RECOMMENDED,
        types=[mm.la.LogicalFunction],
        **TEST_RULE_PARAMS,
    )
    def rule_lf(_: m.ModelElement) -> bool:
        return True

    assert model.search(mm.la.LogicalComponent), "Empty test model?"
    assert model.search(mm.la.LogicalFunction), "Empty test model?"

    results = model.validation.validate()
    assert results

    required = results.by_category("REQUIRED")
    assert len(required) > 0
    assert all(i.category.name == "REQUIRED" for i in required.iter_rules())

    component = results.by_class("LogicalComponent")
    assert len(component) > 0
    assert sum(1 for _ in component.iter_objects()) == len(
        model.search("LogicalComponent")
    )
    assert all(
        type(i).__name__ == "LogicalComponent"
        for i in component.iter_objects()
    )

    function = results.by_class("LogicalFunction")
    assert len(function) > 0
    assert (
        sum(1 for _ in function.iter_objects())
        # -1 because the root function is not validated
        == len(model.search("LogicalFunction")) - 1
    )
    assert all(
        type(i).__name__ == "LogicalFunction" for i in function.iter_objects()
    )


def test_MelodyModel_validation(model: m.MelodyModel):
    assert isinstance(model.validation, validation.ModelValidation)
    assert model.validation.rules

    results = model.validate()

    assert results


def test_ModelObject_validation(model: m.MelodyModel):
    obj = model.by_uuid(TEST_UUID)
    assert isinstance(obj.validation, validation.ElementValidation)
    assert obj.validation.rules

    results = obj.validate()

    assert results


def test_cli_creates_a_validation_report(tmp_path: pathlib.Path):
    output_file = tmp_path / "report.html"
    runner = clitest.CliRunner()

    result = runner.invoke(
        cli_main.main,
        ["-mtest-7.0", f"-o{output_file}"],
    )

    assert result.exit_code == 0, f"CLI returned code {result.exit_code}"
    assert output_file.exists()
    assert output_file.read_bytes() != b""
