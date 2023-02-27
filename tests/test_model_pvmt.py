# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import capellambse
from capellambse.extensions import pvmt


class TestModelConfiguration:
    @staticmethod
    def test_model_has_pvmt_attribute(model: capellambse.MelodyModel):
        assert hasattr(model, "pvmt")

    @staticmethod
    def test_pvmt_config_contains_domains(model: capellambse.MelodyModel):
        expected = {"DarkMagic"}
        domains = model.pvmt.domains

        names = {i.name for i in domains}

        assert names == expected
        assert all(isinstance(i, pvmt.ManagedDomain) for i in domains)

    @staticmethod
    def test_access_to_model_pvmt_creates_extensions_package_if_necessary(
        model: capellambse.MelodyModel,
    ) -> None:
        model.property_value_packages.delete_all()
        assert "EXTENSIONS" not in model.property_value_packages.by_name

        model.pvmt  # pylint: disable=pointless-statement

        assert "EXTENSIONS" in model.property_value_packages.by_name

        for i in model.search():
            i.applied_property_values.delete_all()
            i.applied_property_value_groups.delete_all()
            i.property_values.delete_all()
            i.property_value_groups.delete_all()
        model.save()


class TestObjectPVMT:
    @staticmethod
    def test_elements_have_pvmt_attribute(model: capellambse.MelodyModel):
        obj = model.search()[0]

        assert hasattr(obj, "pvmt")

    @staticmethod
    def test_element_pvmt_can_be_read_and_written_by_subscripting(model):
        obj = model.by_uuid("08e02248-504d-4ed8-a295-c7682a614f66")

        value = obj.pvmt["DarkMagic.Power.Max"]
        assert value == 1600

        obj.pvmt["DarkMagic.Power.Max"] = 2000

        value = obj.pvmt["DarkMagic.Power.Max"]
        assert value == 2000
