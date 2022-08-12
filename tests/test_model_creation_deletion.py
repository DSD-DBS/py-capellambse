# Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Tests for creating and deleting model elements"""

# pylint: disable=[missing-function-docstring, protected-access, redefined-outer-name]
import operator
import pathlib

import pytest

import capellambse
from capellambse.model import modeltypes

TEST_ROOT = pathlib.Path(__file__).parent / "data" / "writemodel"
TEST_MODEL = "WriteTestModel.aird"

XPATH_UUID = "//*[@id={!r}]"


@pytest.fixture
def model():
    return capellambse.MelodyModel(TEST_ROOT / TEST_MODEL)


def test_created_elements_can_be_accessed_in_model(
    model: capellambse.MelodyModel,
):
    newobj = model.la.root_component.components.create(name="TestComponent")

    assert newobj is not None
    assert isinstance(newobj, capellambse.model.layers.la.LogicalComponent)
    assert newobj in model.la.root_component.components


def test_created_elements_show_up_in_xml_after_adding_them(
    model: capellambse.MelodyModel,
):
    newobj = model.la.root_component.components.create(name="TestComponent")

    try:
        model._loader[newobj.uuid]
    except KeyError as err:
        raise AssertionError(
            "Cannot find added element via subscripting"
        ) from err

    assert model._loader.xpath(
        XPATH_UUID.format(newobj.uuid)
    ), "Cannot find added element via XPath"


@pytest.mark.parametrize("layer", ["sa", "la", "pa"])
@pytest.mark.parametrize(
    "element,rootelement,name",
    [
        ("root_function", "function_package", "Function"),
        ("root_component", "component_package", "Component"),
    ],
)
def test_create_elements_with_rootelem(
    model: capellambse.MelodyModel,
    layer: str,
    element: str,
    rootelement: str,
    name: str,
):
    old_obj = (obj_getter := operator.attrgetter(f"{layer}.{element}"))(model)
    old_obj.delete()
    root = operator.attrgetter(f"{layer}.{rootelement}")(model)
    new_obj = obj_getter(model).create(name=name, root=root)

    assert new_obj.name == name
    assert new_obj.parent == root
    assert old_obj.uuid != new_obj.uuid


def test_create_elements_with_rootelem_and_elmlist(
    model: capellambse.MelodyModel,
):
    root = model.la.function_package
    new_fnc = model.la.all_functions.create(name="Test Function", root=root)

    assert new_fnc.name == "Test Function"
    assert new_fnc.parent == root


def test_create_elements_on_lookup_fails_when_no_root_is_given(
    model: capellambse.MelodyModel,
):
    with pytest.raises(TypeError) as error:
        model.la.all_functions.create(name="Test Function")

    assert error.value.args[0] == "Cannot create object. Pass 'root'."


@pytest.mark.parametrize(
    "deletion_target",
    [0, slice(None, 1)],
)
def test_deleted_elements_are_removed(
    model: capellambse.MelodyModel, deletion_target
):
    comps = model.la.root_component.components
    assert len(comps) == 2, "Precondition not met: Bad list length"

    olduuid = comps[0].uuid
    del comps[deletion_target]

    assert len(comps) != 2, "List length did not change"

    with pytest.raises(KeyError):
        model._loader[olduuid]  # pylint: disable=pointless-statement

    assert not model._loader.xpath(
        XPATH_UUID.format(olduuid)
    ), "Element is still present in tree after deleting"


def test_delete_all_deletes_matching_objects(model: capellambse.MelodyModel):
    comps = model.la.root_component.components
    assert len(comps) == 2

    comps.delete_all(name="Delete Me")
    assert len(comps) == 1
    assert comps[0].name == "Keep Me"


def test_delete_elements_from_lookups(model: capellambse.MelodyModel):
    assert model.la.all_functions[0] == model.la.root_function

    del model.la.all_functions[0]

    assert not model.la.all_functions


def test_create_architecture_layer_from_mapping(
    model: capellambse.MelodyModel,
):
    del model.pa
    model.pa = {
        "name": "New Physical Arch",
        "component_package": {
            "name": "Components",
            "components": [
                {
                    "name": "Root Component",
                    "nature": modeltypes.Nature.NODE,
                }
            ],
            "packages": [
                {
                    "name": "SubComponents",
                    "components": [{"name": "SubComponent"}],
                }
            ],
        },
        "function_package": {
            "name": "PhysicalFunctionPkg",
            "functions": [{"name": "Function"}],
        },
    }

    assert model.pa.name == "New Physical Arch"
    assert model.pa.owner == model
    assert model.pa.root_component.name == "Root Component"
    assert model.pa.root_component.nature == modeltypes.Nature.NODE
    assert model.pa.all_components[1].name == "SubComponent"
    assert model.pa.all_components[1].owner.name == "SubComponents"
    assert model.pa.all_functions[0].name == "Function"
    assert model.pa.function_package.name == "PhysicalFunctionPkg"
