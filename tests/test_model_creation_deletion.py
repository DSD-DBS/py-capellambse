# Copyright 2021 DB Netz AG
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for creating and deleting model elements"""
# pylint: disable=missing-function-docstring
# pylint: disable=protected-access
import pathlib

import pytest

import capellambse

TEST_ROOT = pathlib.Path(__file__).parent / "data" / "writemodel"
TEST_MODEL = "WriteTestModel.aird"

XPATH_UUID = "//*[@id={!r}]"


@pytest.fixture
def model():
    return capellambse.MelodyModel(TEST_ROOT / TEST_MODEL)


def test_created_elements_can_be_accessed_in_model(model):
    newobj = model.la.root_component.components.create(name="TestComponent")

    assert newobj is not None
    assert isinstance(newobj, capellambse.model.layers.la.LogicalComponent)
    assert newobj in model.la.root_component.components


def test_created_elements_show_up_in_xml_after_adding_them(model):
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
def test_deleted_elements_are_removed(model, deletion_target):
    comps = model.la.root_component.components
    assert len(comps) == 2, "Precondition not met: Bad list length"

    olduuid = comps[0].uuid
    del comps[deletion_target]

    assert len(comps) != 2, "List length did not change"

    with pytest.raises(KeyError):
        model._loader[olduuid]

    assert not model._loader.xpath(
        XPATH_UUID.format(olduuid)
    ), "Element is still present in tree after deleting"


def test_delete_all_deletes_matching_objects(model):
    comps = model.la.root_component.components
    assert len(comps) == 2

    comps.delete_all(name="Delete Me")
    assert len(comps) == 1
    assert comps[0].name == "Keep Me"
