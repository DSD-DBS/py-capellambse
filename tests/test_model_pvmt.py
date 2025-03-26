# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

import shutil

import pytest

import capellambse
from capellambse import helpers
from capellambse.extensions import pvmt

from .conftest import Models  # type: ignore

TEST_ROOT = Models.pvmt
EXPECT_ROOT = Models.pvmt / "expected-output"


@pytest.fixture
def model(monkeypatch, tmp_path):
    new_test_root = tmp_path / "model"
    shutil.copytree(TEST_ROOT, new_test_root)
    monkeypatch.setitem(globals(), "TEST_ROOT", new_test_root)
    return capellambse.MelodyModel(new_test_root)


class TestPVMTConfiguration:
    def test_the_first_found_pvmt_configuration_is_used(self, model):
        model.project.property_value_pkgs.create(name="EXTENSIONS")
        assert len(model.project.property_value_pkgs) == 2

        domains = {i.name for i in model.pvmt.domains}

        assert domains

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
    def test_apply_outofscope(self, model, group: str):
        obj = model.by_uuid("d32caffc-b9a1-448e-8e96-65a36ba06292")
        domain = model.pvmt.domains["Out of scope"]
        assert isinstance(domain, pvmt.ManagedDomain)
        group_obj = domain.groups[group]
        assert isinstance(group_obj, pvmt.ManagedGroup)

        with pytest.raises(pvmt.ScopeError):
            group_obj.apply(obj)

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

    @helpers.deterministic_ids()
    def test_applying_sets_type_on_applied_enums(self, model):
        obj = model.pa.root_component.owned_components.create(
            name="Test extension card",
            nature="NODE",
        )
        assert not obj.property_value_groups, "PV group already exists?"
        domain = model.pvmt.domains["Computer"]
        group = domain.groups["Components"]
        expected_type = domain.types.by_name("ComponentType")

        ag = group.apply(obj)

        pv = ag.property_values.by_name("ComponentType")
        assert pv.type == expected_type


class TestAppliedPropertyValueGroupXML:
    """Tests that rely on writing back and comparing the output XML."""

    elem_uuid = "d32caffc-b9a1-448e-8e96-65a36ba06292"

    def compare_xml(self, model, expected_file):
        (pvmt_model_path,) = TEST_ROOT.glob("*.capella")
        expected_model_path = EXPECT_ROOT / expected_file

        model.save()
        actual = pvmt_model_path.read_text(encoding="utf-8")
        expected = expected_model_path.read_text(encoding="utf-8")

        assert actual == expected

    @helpers.deterministic_ids()
    def test_apply(self, model):
        elem = model.by_uuid(self.elem_uuid)

        elem.pvmt["External Data.Object IDs.Object ID"] = "CABLE-0001"

        self.compare_xml(model, "apply.capella")
