# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=redefined-outer-name
import pathlib
import shutil
import tempfile

import pytest

from capellambse import loader, pvmt

TEST_ROOT = pathlib.Path(__file__).parent / "data" / "pvmt"
MODEL_FILE = "PVMTTest.aird"


@pytest.fixture
def model():
    global TEST_ROOT

    orig_test_root = TEST_ROOT
    with tempfile.TemporaryDirectory() as tempdir:
        TEST_ROOT = pathlib.Path(tempdir, "model")
        shutil.copytree(orig_test_root, TEST_ROOT)

        yield loader.MelodyLoader(TEST_ROOT / MODEL_FILE)

    TEST_ROOT = orig_test_root


@pytest.fixture
def pvext(model):
    return pvmt.load_pvmt_from_model(model)


class TestPVMTBase:
    """Tests for basic PVMT functionality."""

    domain_uuid = "02e0c435-f085-471f-9f6e-e12fe5f27687"
    domain_name = "Computer"

    enum_names = {
        "03e5e5ae-0a61-473d-a792-e003ce601ff4": "Cable Type",
        "ae279311-6a75-40b7-9bf3-a19c136d0573": "ComponentType",
    }
    enum_values = {
        "03e5e5ae-0a61-473d-a792-e003ce601ff4": ["UNSET", "Trace", "Cable"],
        "ae279311-6a75-40b7-9bf3-a19c136d0573": [
            "UNSET",
            "Core Component",
            "External",
        ],
    }

    def test_domains(self, pvext):
        assert {k: v.name for k, v in pvext.items()} == {
            self.domain_uuid: self.domain_name,
            "12a02f1b-8b97-4188-95ea-2afd377c4c41": "Out of scope",
            "ae15f861-2f15-40d2-a1b9-57dfdf7fabae": "In scope",
            "c2d3e3a3-f9bb-4ff7-964d-2109c7065bc2": "External Data",
        }

    def test_enums(self, pvext):
        model_enums = pvext[self.domain_uuid].enums
        assert {k: v.name for k, v in model_enums.items()} == self.enum_names

        for enum_uuid, vals in self.enum_values.items():
            actual_vals = set(
                v["name"] for _, v in model_enums[enum_uuid].items()
            )
            assert actual_vals == set(vals)

    def test_enum_defaults(self, pvext):
        group = "0fb1fbfb-43a6-4f96-9ec3-2cb83d80c702"
        pv_id = "f3f9b7ec-f00d-4b2f-8a48-900a22c43853"
        epv = pvext[self.domain_uuid][group][pv_id]
        assert epv.default_value["name"] == "UNSET"

    def test_groups(self, pvext):
        model_groups = pvext[self.domain_uuid].groups
        assert set(g.name for g in model_groups) == {
            "Components",
            "Cables",
            "Physical Cables",
        }

    def test_int(self, pvext):
        group = "cdc24b8b-3c4c-4513-9aad-99c0f7d884dc"
        pv_id = "7130121b-0242-49b7-885c-44b868c4d7b7"
        ipv = pvext[self.domain_uuid][group][pv_id]

        assert ipv.name == "Price"
        assert ipv.unit == "€"

    def test_apply_outofscope(self, model, pvext):
        elem = model["d32caffc-b9a1-448e-8e96-65a36ba06292"]
        domain = pvext["12a02f1b-8b97-4188-95ea-2afd377c4c41"]
        for group in domain.groups:
            with pytest.raises(pvmt.ScopeError):
                pvext.get_element_pv(
                    elem, f"{domain.name}.{group.name}", create=True
                )

    def test_apply_inscope(self, model, pvext):
        elem = model["d32caffc-b9a1-448e-8e96-65a36ba06292"]
        domain = pvext["ae15f861-2f15-40d2-a1b9-57dfdf7fabae"]
        for group in domain.groups:
            pvext.get_element_pv(
                elem, f"{domain.name}.{group.name}", create=True
            )


class TestAppliedPropertyValueGroup:
    """Tests for all methods of the ``AppliedPropertyValueGroup`` object."""

    elem_uuid = "d32caffc-b9a1-448e-8e96-65a36ba06292"
    pvg_name = "Computer.Physical Cables"

    def test___iter__(self, model, pvext):
        elem_pv = pvext.get_element_pv(model[self.elem_uuid], self.pvg_name)
        keys = set(elem_pv)
        assert keys == {"In Stock", "Label", "Plugs per side", "Price"}

    def test___len__(self, model, pvext):
        elem_pv = pvext.get_element_pv(model[self.elem_uuid], self.pvg_name)
        assert len(elem_pv) == 4

    def test___getitem__(self, model, pvext):
        elem_pv = pvext.get_element_pv(model[self.elem_uuid], self.pvg_name)
        assert elem_pv["In Stock"] is True
        assert elem_pv["Label"] == "DisplayPort_1"
        assert elem_pv["Plugs per side"] == 1
        assert elem_pv["Price"] == 14.99
        with pytest.raises(KeyError):
            elem_pv["price"]  # pylint: disable=pointless-statement

    def test___setitem___modify(self, model, pvext):
        elem = model[self.elem_uuid]
        elem_pv = pvext.get_element_pv(elem, self.pvg_name)
        pv_cable = pvext.get_element_pv(elem, "Computer.Cables")
        pv_cable["CableType"] = "Trace"
        elem_pv["Price"] = 10
        elem_pv["In Stock"] = False

        assert pv_cable["CableType"] == "Trace"
        assert elem_pv["Price"] == 10.0
        assert elem_pv["In Stock"] is False

        with pytest.raises(KeyError):
            elem_pv["price"] = 10.0

        with pytest.raises(ValueError):
            elem_pv["Price"] = "Not a float"

    def test___delitem_____setitem__(self, model, pvext):
        elem_pv = pvext.get_element_pv(model[self.elem_uuid], self.pvg_name)
        del elem_pv["Price"]
        assert "Price" not in elem_pv

        with pytest.raises(KeyError):
            del elem_pv["Price"]
        with pytest.raises(KeyError):
            del elem_pv["nonexistent_key"]
        with pytest.raises(KeyError):
            elem_pv["price"] = 10.0

        elem_pv["Price"] = 25.0
        assert "Price" in elem_pv
        assert elem_pv["Price"] == 25.0

    def test___contains__(self, model, pvext):
        elem_pv = pvext.get_element_pv(model[self.elem_uuid], self.pvg_name)
        assert "Price" in elem_pv
        assert "In Stock" in elem_pv
        assert "price" not in elem_pv
        assert "InStock" not in elem_pv

    def test_copy(self, model, pvext):
        elem_pv = pvext.get_element_pv(model[self.elem_uuid], self.pvg_name)
        copy = elem_pv.copy()
        expected = {
            "In Stock": True,
            "Label": "DisplayPort_1",
            "Plugs per side": 1,
            "Price": 14.99,
        }
        assert expected == copy
        assert elem_pv is not copy

    def test_get(self, model, pvext):
        elem_pv = pvext.get_element_pv(model[self.elem_uuid], self.pvg_name)
        assert elem_pv.get("Price") == 14.99
        assert elem_pv.get("In Stock") is True

        sentinel = object()
        assert elem_pv.get("price", sentinel) is sentinel


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

    def test_apply(self, model, pvext, monkeypatch):
        call_count = 0

        def mock_generate_uuid(*__, **_):
            nonlocal call_count
            call_count += 1
            return f"00000000-0000-0000-0000-{call_count:012x}"

        monkeypatch.setattr(
            "capellambse.loader.MelodyLoader.generate_uuid",
            mock_generate_uuid,
        )

        elem = model[self.elem_uuid]

        obj_ids = pvext.get_element_pv(
            elem, "External Data.Object IDs", create=True
        )
        # By this point, the group and its child must both already
        # exist, each with their own UUID.
        assert call_count == 2

        obj_ids["Object ID"] = "CABLE-0001"
        self.compare_xml(model, "apply.capella")
