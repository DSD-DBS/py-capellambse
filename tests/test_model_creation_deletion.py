# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Tests for creating and deleting model elements."""
# pylint: disable=missing-function-docstring, redefined-outer-name
import pathlib

import pytest

import capellambse

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
