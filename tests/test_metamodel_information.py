# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

import typing as t

import pytest

import capellambse.model as m
from capellambse.metamodel import information

TEMP_PROPERTY_UUID = "2e729284-56e2-4afa-b29e-7fe00d057f80"
CLASS_TYPED_PROP_UUID = "752afd4c-dfa1-4040-baf4-9c5a4ef5b399"
FLOAT_TYPE_UUID = "d65e426c-7df0-43df-aaa4-417ae193176a"


@pytest.mark.parametrize(
    ("name", "super_name", "expected_type"),
    [
        ("SpecialTwist", "Twist", "Class"),
        ("1st Specialization of SuperClass", "SuperClass", "Class"),
        ("SpecialUnion1", "SuperUnion", "Union"),
        ("StatusEnum", "CmdEnum", "Enumeration"),
        ("SpecialCollection1", "SuperCollection", "Collection"),
    ],
)
def test_generalizations(
    model: m.MelodyModel,
    name: str,
    super_name: str,
    expected_type: str,
):
    objects_of_type = model.search(expected_type)
    obj = objects_of_type.by_name(name)
    super_obj = objects_of_type.by_name(super_name)

    assert isinstance(obj.xtype, str)
    assert obj.xtype.endswith(expected_type)
    assert obj.super == super_obj
    assert isinstance(super_obj.xtype, str)
    assert super_obj.xtype.endswith(expected_type)
    sub_objects = super_obj.sub
    assert isinstance(sub_objects, m.ElementList)
    assert obj in sub_objects


@pytest.mark.parametrize(
    ("uuid", "expected_visibility"),
    [
        pytest.param(
            "bbc296e1-ed4c-40cf-b37d-c8eb8613228a", "PUBLIC"
        ),  # class
        pytest.param("959b5222-7717-4ee9-bd3a-f8a209899464", "UNSET"),  # class
        pytest.param(
            "d2b4a93c-73ef-4f01-8b59-f86c074ec521", "PACKAGE"
        ),  # class
        pytest.param(
            "ca79bf38-5e82-4104-8c49-e6e16b3748e9", "PROTECTED"
        ),  # class
        pytest.param(TEMP_PROPERTY_UUID, "PUBLIC"),  # property
        pytest.param(
            "3b4915eb-22fc-421d-bf89-07a14d0a2772", "PRIVATE"
        ),  # property
    ],
)
def test_object_visibility(
    model: m.MelodyModel, uuid: str, expected_visibility
):
    obj = model.by_uuid(uuid)
    assert obj.visibility == expected_visibility


@pytest.mark.parametrize(
    ("typed_object_uuid", "expected_type_uuid"),
    [
        pytest.param(
            "3b4915eb-22fc-421d-bf89-07a14d0a2772",
            "be4e2bfa-2026-4e0b-9a6d-88b5f9c8a3d4",
            id="prop has int type",
        ),
        pytest.param(
            TEMP_PROPERTY_UUID, FLOAT_TYPE_UUID, id="prop has float type"
        ),
        pytest.param(
            CLASS_TYPED_PROP_UUID,
            "d2b4a93c-73ef-4f01-8b59-f86c074ec521",
            id="prop has class type",
        ),
        pytest.param(
            "b6feec5b-3bba-4da9-b9fc-fbd3b72b287d",
            FLOAT_TYPE_UUID,
            id="literal-value has float type",
        ),
    ],
)
def test_object_has_type(
    model: m.MelodyModel, typed_object_uuid: str, expected_type_uuid: str
):
    obj = model.by_uuid(typed_object_uuid)
    expected_type = model.by_uuid(expected_type_uuid)
    assert obj.type == expected_type


class TestClasses:
    def test_class_owns_stm(self, model: m.MelodyModel):
        elm = model.by_uuid("959b5222-7717-4ee9-bd3a-f8a209899464")
        assert isinstance(elm, information.Class)

        assert elm.xtype.endswith("Class")
        assert hasattr(elm, "state_machines")
        assert len(elm.state_machines) == 1

    @pytest.mark.parametrize(
        ("uuid", "attr_name", "expected_value"),
        [
            pytest.param(
                "bbc296e1-ed4c-40cf-b37d-c8eb8613228a", "is_abstract", True
            ),
            pytest.param(
                "959b5222-7717-4ee9-bd3a-f8a209899464", "is_abstract", False
            ),
            pytest.param(
                "ca79bf38-5e82-4104-8c49-e6e16b3748e9", "is_final", True
            ),
            pytest.param(
                "959b5222-7717-4ee9-bd3a-f8a209899464", "is_final", False
            ),
            pytest.param(
                "d2b4a93c-73ef-4f01-8b59-f86c074ec521", "is_primitive", True
            ),
            pytest.param(
                "bbc296e1-ed4c-40cf-b37d-c8eb8613228a", "is_primitive", False
            ),
        ],
    )
    def test_class_has_bool_attributes(
        self,
        model: m.MelodyModel,
        uuid: str,
        attr_name: str,
        expected_value: bool,
    ):
        obj = model.by_uuid(uuid)
        value = getattr(obj, attr_name)
        assert value == expected_value

    @pytest.mark.parametrize(
        ("uuid", "expected"),
        [
            ("bbc296e1-ed4c-40cf-b37d-c8eb8613228a", "PUBLIC"),
            ("ca79bf38-5e82-4104-8c49-e6e16b3748e9", "PROTECTED"),
            ("3b4915eb-22fc-421d-bf89-07a14d0a2772", "PRIVATE"),
            ("d2b4a93c-73ef-4f01-8b59-f86c074ec521", "PACKAGE"),
            ("c371cebb-8021-4a38-8706-4525734de76d", "UNSET"),
        ],
    )
    def test_class_has_visibility(
        self, model: m.MelodyModel, uuid: str, expected: str
    ) -> None:
        obj = model.by_uuid(uuid)
        assert obj.visibility == expected
        assert not isinstance(obj.visibility, str)

    @pytest.mark.parametrize(
        ("uuid", "num_of_properties"),
        [
            pytest.param("bbc296e1-ed4c-40cf-b37d-c8eb8613228a", 2),
            pytest.param("ca79bf38-5e82-4104-8c49-e6e16b3748e9", 5),
            pytest.param("d2b4a93c-73ef-4f01-8b59-f86c074ec521", 2),
            pytest.param("8164ae8b-36d5-4502-a184-5ec064db4ec3", 0),
        ],
    )
    def test_class_has_properties(
        self, model: m.MelodyModel, uuid: str, num_of_properties: int
    ):
        obj = model.by_uuid(uuid)
        assert len(obj.properties) == num_of_properties


class TestClassProperty:
    @pytest.mark.parametrize(
        "attr_name",
        [
            pytest.param("is_ordered"),
            pytest.param("is_unique"),
            pytest.param("is_abstract"),
            pytest.param("is_static"),
            pytest.param("is_part_of_key"),
            pytest.param("is_derived"),
            pytest.param("is_read_only"),
        ],
    )
    def test_property_has_bool_attributes(
        self, model: m.MelodyModel, attr_name
    ):
        prop_all_false = model.by_uuid(TEMP_PROPERTY_UUID)  # temperature prop
        prop_all_true = model.by_uuid(
            "3b4915eb-22fc-421d-bf89-07a14d0a2772"
        )  # num_of_things prop
        assert hasattr(prop_all_false, attr_name)
        assert getattr(prop_all_false, attr_name) is False
        assert hasattr(prop_all_true, attr_name)
        assert getattr(prop_all_true, attr_name) is True

    @pytest.mark.parametrize(
        ("value_attr", "expected_val_uuid"),
        [
            pytest.param(
                "default_value", "b6feec5b-3bba-4da9-b9fc-fbd3b72b287d"
            ),
            pytest.param("min_value", "e615cba9-acc4-4a23-ab0c-777c8cabb8f3"),
            pytest.param("max_value", "d543018f-5f44-4c03-8e2e-875457c8967e"),
            pytest.param("null_value", "9fbdec5d-12c5-4194-b58f-35bff3ee2c9a"),
            pytest.param("min_card", "5546324b-81e8-46db-acee-2f8c1c50afc0"),
            pytest.param("max_card", "581587dd-8301-4bc1-bab4-4f54224d3f6d"),
        ],
    )
    def test_property_has_role_tag_value(
        self, model: m.MelodyModel, value_attr: str, expected_val_uuid: str
    ):
        obj = model.by_uuid(TEMP_PROPERTY_UUID)
        expected_val = model.by_uuid(expected_val_uuid)
        assert hasattr(obj, value_attr)
        assert getattr(obj, value_attr) == expected_val

    def test_property_has_no_value(self, model: m.MelodyModel):
        obj = model.by_uuid(CLASS_TYPED_PROP_UUID)
        assert obj.min_value is None


def test_complex_value(model: m.MelodyModel):
    cv = model.by_uuid("3a467d68-f53c-4d66-9d32-fe032a8cb2c5")
    value_parts = {
        i.referenced_property.name: i.value.value for i in cv.value_parts
    }
    assert value_parts == {
        "owner": "Harry Potter",
        "core": "Pheonix Feather",
        "wood": "Holly",
    }


@pytest.mark.parametrize(
    ("uuid", "expected_value", "expected_cls"),
    [
        pytest.param(
            "1d24c16d-61ad-40b9-9ce0-80e72320e74f",
            "3",
            "LiteralNumericValue",
        ),
        pytest.param(
            "3c6d9df2-1229-4642-aede-a7ac129035c9",
            "Unknown object",
            "LiteralStringValue",
        ),
    ],
)
def test_literal_value_has_value(
    model: m.MelodyModel, uuid: str, expected_value: t.Any, expected_cls
):
    obj = model.by_uuid(uuid)
    assert obj.value == expected_value
    assert str(obj.xtype).endswith(expected_cls)


def test_literal_value_has_unit(model: m.MelodyModel):
    obj = model.by_uuid("d543018f-5f44-4c03-8e2e-875457c8967e")
    expected_unit = model.by_uuid("695386d5-6364-4e85-a1c3-a2c489bf0eb2")
    assert obj.unit == expected_unit
