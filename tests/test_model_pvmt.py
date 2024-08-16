# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

import pathlib
import shutil

import pytest

import capellambse
from capellambse.extensions import pvmt

TEST_ROOT = pathlib.Path(__file__).parent / "data" / "pvmt"
MODEL_FILE = "PVMTTest.aird"


@pytest.fixture
def model(monkeypatch, tmp_path):
    new_test_root = tmp_path / "model"
    shutil.copytree(TEST_ROOT, new_test_root)
    monkeypatch.setitem(globals(), "TEST_ROOT", new_test_root)
    return capellambse.MelodyModel(new_test_root)


class TestPVMTConfiguration:
    def test_domains(self, model):
        expected = {
            "02e0c435-f085-471f-9f6e-e12fe5f27687": "Computer",
            "12a02f1b-8b97-4188-95ea-2afd377c4c41": "Out of scope",
            "ae15f861-2f15-40d2-a1b9-57dfdf7fabae": "In scope",
            "c2d3e3a3-f9bb-4ff7-964d-2109c7065bc2": "External Data",
        }

        actual = {i.uuid: i.name for i in model.pvmt.domains}

        assert actual == expected

    @pytest.mark.parametrize(
        ("enum_uuid", "enum_vals"),
        [
            (
                "03e5e5ae-0a61-473d-a792-e003ce601ff4",
                {"UNSET", "Trace", "Cable"},
            ),
            (
                "ae279311-6a75-40b7-9bf3-a19c136d0573",
                {"UNSET", "Core Component", "External"},
            ),
        ],
    )
    def test_enums(self, model, enum_uuid, enum_vals):
        enum = model.by_uuid(enum_uuid)
        domain = model.pvmt.domains["Computer"]
        assert enum in domain.enumeration_property_types

        actual = {i.name for i in enum.literals}
        assert actual == enum_vals

    def test_groups(self, model):
        expected = {"Components", "Cables", "Physical Cables"}

        model_groups = model.pvmt.domains["Computer"].groups
        actual = {g.name for g in model_groups}

        assert actual == expected

    @pytest.mark.parametrize(
        "group",
        [
            "Architecture",
            "Property (Bool, not equal)",
            "Property (Enum, equal)",
            "Property (Enum, not equal)",
            "Property (Float, equal)",
            "Property (Float, not equal)",
            "Property (Float, greater than)",
            "Property (Float, less than)",
            "Property (Float, greater or equal)",
            "Property (Float, less or equal)",
            "Property (Integer, equal)",
            "Property (Integer, not equal)",
            "Property (Integer, greater than)",
            "Property (Integer, less than)",
            "Property (Integer, greater or equal)",
            "Property (Integer, less or equal)",
            "Property (String, equal)",
            "Property (String, not equal)",
            "Property (String, contains)",
            "Property (String, starts with)",
            "Property (String, ends with)",
        ],
    )
    def test_apply_outofscope(self, model, group):
        obj = model.by_uuid("d32caffc-b9a1-448e-8e96-65a36ba06292")
        domain = model.pvmt.domains["Out of scope"]
        group = domain.groups[group]
        with pytest.raises(pvmt.ScopeError):
            group.apply(obj)

    @pytest.mark.parametrize(
        "group",
        [
            "Property (Bool, equal)",
            "Property (String, equal)",
        ],
    )
    def test_apply_inscope(self, model, group):
        obj = model.by_uuid("d32caffc-b9a1-448e-8e96-65a36ba06292")
        domain = model.pvmt.domains["In scope"]
        group = domain.groups[group]

        ag = group.apply(obj)

        assert ag is not None
        assert ag.name == f"In scope.{group.name}"
        assert len(ag.property_values) == len(group.property_values)
        applied_values = {i.name: i.value for i in ag.property_values}
        default_values = {i.name: i.value for i in group.property_values}
        assert applied_values == default_values


class TestAppliedPropertyValueGroupXML:
    """Tests that rely on writing back and comparing the output XML."""

    expect_root = TEST_ROOT / "expected-output"

    elem_uuid = "d32caffc-b9a1-448e-8e96-65a36ba06292"

    def compare_xml(self, model, expected_file):
        pvmt_model_path = (TEST_ROOT / MODEL_FILE).with_suffix(".capella")
        expected_model_path = self.expect_root / expected_file

        model.save()
        actual = pvmt_model_path.read_text(encoding="utf-8")
        expected = expected_model_path.read_text(encoding="utf-8")

        assert actual == expected

    def test_apply(self, model, monkeypatch):
        call_count = 0

        def mock_generate_uuid(*__, **_):
            nonlocal call_count
            call_count += 1
            return f"00000000-0000-0000-0000-{call_count:012x}"

        monkeypatch.setattr(
            "capellambse.loader.MelodyLoader.generate_uuid",
            mock_generate_uuid,
        )

        elem = model.by_uuid(self.elem_uuid)

        elem.pvmt["External Data.Object IDs.Object ID"] = "CABLE-0001"

        assert call_count == 2
        self.compare_xml(model, "apply.capella")
