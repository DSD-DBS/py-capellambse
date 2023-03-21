# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Tests for creating and deleting model elements."""
# pylint: disable=missing-function-docstring, redefined-outer-name
import pathlib

import pytest

import capellambse
import capellambse.model as metamodel
import capellambse.model.common as c

# pylint: disable-next=relative-beyond-top-level, unused-import
from .conftest import model as model50  # type: ignore[import]

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


def test_create_adds_missing_namespace_to_fragment(
    model: capellambse.MelodyModel,
) -> None:
    assert "Requirements" not in model._element.nsmap, "Precondition failed"
    module = model.by_uuid("85a31dd7-7755-486b-b803-1df8915e2cf9")

    module.requirements.create(name="TestReq")

    assert "Requirements" in model._element.nsmap


def test_adding_a_namespace_preserves_the_capella_version_comment(
    model: capellambse.MelodyModel,
) -> None:
    assert "Requirements" not in model._element.nsmap, "Precondition failed"
    prev_elements = list(model._element.itersiblings(preceding=True))
    assert len(prev_elements) == 1, "No version comment to preserve?"

    model._loader.add_namespace(model._element, "Requirements")

    prev_elements = list(model._element.itersiblings(preceding=True))
    assert len(prev_elements) == 1
    assert model.info.capella_version != "UNKNOWN"


def test_deleting_an_object_purges_references_from_AttrProxyAccessor(
    model: capellambse.MelodyModel, caplog
) -> None:
    part = model.by_uuid("1bd59e23-3d45-4e39-88b4-33a11c56d4e3")
    assert isinstance(part, metamodel.cs.Part)
    assert isinstance(type(part).type, c.AttrProxyAccessor)
    component = model.by_uuid("ea5f09e6-a0ec-46b2-bd3e-b572f9bf99d6")

    component.parent.components.remove(component)

    assert not list(model.find_references(component))
    assert part.type is None
    assert not caplog.records


def test_deleting_an_object_purges_references_from_LinkAccessor(
    model50: capellambse.MelodyModel, caplog
) -> None:
    entity = model50.by_uuid("e37510b9-3166-4f80-a919-dfaac9b696c7")
    assert isinstance(entity, metamodel.oa.Entity)
    assert isinstance(type(entity).activities, c.LinkAccessor)
    activity = model50.by_uuid("f1cb9586-ce85-4862-849c-2eea257f706b")

    activity.parent.activities.remove(activity)

    assert not list(model50.find_references(activity))
    assert activity not in entity.activities
    assert not caplog.records


def test_deleting_an_entire_list_purges_references_to_all_list_members(
    model50: capellambse.MelodyModel, caplog
) -> None:
    component = model50.by_uuid("ff7b8672-84db-4b93-9fea-22a410907fb1")
    assert isinstance(component, metamodel.la.LogicalComponent)
    p1 = model50.by_uuid("db5681e4-4245-4207-a429-e89979f6ac71")
    p2 = model50.by_uuid("7c61d723-3658-47ff-9b0c-7b016ac4cb76")
    current_ports = [i.uuid for i in component.ports]
    assert current_ports == [p1.uuid, p2.uuid], "Unexpected ports"
    assert list(model50.find_references(p1)), "Dead port CP 1?"
    assert list(model50.find_references(p2)), "Dead port CP 2?"

    del component.ports

    assert not list(model50.find_references(p1))
    assert not list(model50.find_references(p2))
    assert not caplog.records


def test_deleting_an_object_purges_references_to_children(
    model50: capellambse.MelodyModel, caplog
) -> None:
    component = model50.by_uuid("a8c46457-a702-41c4-a971-c815c4c5a674")
    port = model50.by_uuid("e0dcf8c2-2283-4456-98a2-146e78ba5f26")
    exchange_id = "d8655737-39ab-4482-a934-ee847c7ff6bd"
    current_refs = [
        (getattr(obj, "uuid", None), attr)
        for obj, attr, _ in model50.find_references(port)
    ]
    assert port in component.ports
    assert len(current_refs) > 1, "Port has no references before test"
    assert (exchange_id, "target") in current_refs

    model50.la.component_package.components.remove(component)

    assert not list(model50.find_references(port))
    assert model50.by_uuid(exchange_id).target is None
    assert not caplog.records
