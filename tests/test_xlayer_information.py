import typing as t

import pytest

from capellambse import MelodyModel
from capellambse.model.crosslayer.information import Class

from . import TEST_MODEL, TEST_ROOT


# TODO: test generalization of unions
# TODO: test generalization of collections
@pytest.mark.parametrize(
    "uuid,super_uuid,expected_type",
    [
        pytest.param(
            "0fef2887-04ce-4406-b1a1-a1b35e1ce0f3",
            "8164ae8b-36d5-4502-a184-5ec064db4ec3",
            "Class",
            id="Class - Same Layer",
        ),
        pytest.param(
            "959b5222-7717-4ee9-bd3a-f8a209899464",
            "bbc296e1-ed4c-40cf-b37d-c8eb8613228a",
            "Class",
            id="Class - Cross Layer",
        ),
    ],
)
def test_generalizations(
    model: MelodyModel, uuid: str, super_uuid: str, expected_type: str
):
    elm = model.by_uuid(uuid)  # type: ignore[assignment]
    super_class = model.by_uuid(super_uuid)

    assert elm.xtype.endswith(expected_type)
    assert hasattr(elm, "super")
    assert elm.super == super_class
    assert elm.super.xtype.endswith(expected_type)


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
            pytest.param("ca79bf38-5e82-4104-8c49-e6e16b3748e9", 3),
            pytest.param("d2b4a93c-73ef-4f01-8b59-f86c074ec521", 2),
            pytest.param("8164ae8b-36d5-4502-a184-5ec064db4ec3", 0),
        ],
    )
    def test_class_has_properties(
        self, model: MelodyModel, uuid: str, num_of_properties: int
    ):
        obj = model.by_uuid(uuid)
        assert len(obj.properties) == num_of_properties
