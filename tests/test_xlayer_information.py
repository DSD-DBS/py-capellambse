import typing as t

import pytest

import capellambse.model.common as c
from capellambse import MelodyModel
from capellambse.model.crosslayer.information import Class

from . import TEST_MODEL, TEST_ROOT

TEMP_PROPERTY_UUID = "2e729284-56e2-4afa-b29e-7fe00d057f80"


@pytest.mark.parametrize(
    "name,super_name,expected_type",
    [
        pytest.param(
            "SpecialTwist",
            "Twist",
            "Class",
        ),
        pytest.param(
            "1st Specialization of SuperClass",
            "SuperClass",
            "Class",
        ),
        pytest.param(
            "SpecialUnion1",
            "SuperUnion",
            "Union",
        ),
        pytest.param(
            "StatusEnum",
            "CmdEnum",
            "Enumeration",
        ),
        pytest.param(
            "SpecialCollection1",
            "SuperCollection",
            "Collection",
        ),
    ],
)
def test_generalizations(
    model: MelodyModel, name: str, super_name: str, expected_type: str
):
    objects_of_type = model.search(expected_type)
    obj = objects_of_type.by_name(name)  # type: ignore[assignment]
    super_obj = objects_of_type.by_name(super_name)

    obj_type: str = obj.xtype  # type: ignore[assignment]
    assert obj_type.endswith(expected_type)
    assert obj.super == super_obj
    super_xtype: str = super_obj.xtype  # type: ignore[assignment]
    assert super_xtype.endswith(expected_type)
    sub_objects: c.ElementList = super_obj.sub  # type: ignore[assignment]
    assert obj in sub_objects


@pytest.mark.parametrize(
    "uuid,expected_visibility",
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
def test_class_visibility(model: MelodyModel, uuid: str, expected_visibility):
    obj = model.by_uuid(uuid)
    assert obj.visibility == expected_visibility


class TestClasses:
    def test_class_owns_stm(self, model: MelodyModel):
        elm: Class = model.by_uuid("959b5222-7717-4ee9-bd3a-f8a209899464")  # type: ignore[assignment]

        assert elm.xtype.endswith("Class")
        assert hasattr(elm, "state_machines")
        assert len(elm.state_machines) == 1

    @pytest.mark.parametrize(
        "uuid,attr_name,expected_value",
        [
            pytest.param(
                "bbc296e1-ed4c-40cf-b37d-c8eb8613228a", "is_abstract", True
            ),
            pytest.param(
                "bbc296e1-ed4c-40cf-b37d-c8eb8613228a", "is_primitive", False
            ),
            pytest.param(
                "d2b4a93c-73ef-4f01-8b59-f86c074ec521", "is_primitive", True
            ),
            pytest.param(
                "959b5222-7717-4ee9-bd3a-f8a209899464", "is_abstract", False
            ),
            pytest.param(
                "959b5222-7717-4ee9-bd3a-f8a209899464", "is_final", False
            ),
            pytest.param(
                "ca79bf38-5e82-4104-8c49-e6e16b3748e9", "is_final", True
            ),
        ],
    )
    def test_class_has_bool_attributes(
        self,
        model: MelodyModel,
        uuid: str,
        attr_name: str,
        expected_value: bool,
    ):
        obj = model.by_uuid(uuid)
        value = getattr(obj, attr_name)
        assert value == expected_value

    @pytest.mark.parametrize(
        "uuid,num_of_properties",
        [
            pytest.param("bbc296e1-ed4c-40cf-b37d-c8eb8613228a", 2),
            pytest.param("ca79bf38-5e82-4104-8c49-e6e16b3748e9", 4),
            pytest.param("d2b4a93c-73ef-4f01-8b59-f86c074ec521", 2),
            pytest.param("8164ae8b-36d5-4502-a184-5ec064db4ec3", 0),
        ],
    )
    def test_class_has_properties(
        self, model: MelodyModel, uuid: str, num_of_properties: int
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
    def test_property_has_bool_attributes(self, model: MelodyModel, attr_name):
        prop_all_false = model.by_uuid(TEMP_PROPERTY_UUID)  # temperature prop
        prop_all_true = model.by_uuid(
            "3b4915eb-22fc-421d-bf89-07a14d0a2772"
        )  # num_of_things prop
        assert hasattr(prop_all_false, attr_name)
        assert getattr(prop_all_false, attr_name) == False
        assert hasattr(prop_all_true, attr_name)
        assert getattr(prop_all_true, attr_name) == True
