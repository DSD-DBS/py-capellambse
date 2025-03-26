# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Tests for creating and deleting model elements."""

import pytest

import capellambse.metamodel as mm
import capellambse.model as m

from .conftest import Models  # type: ignore

XPATH_UUID = "//*[@id={!r}]"


@pytest.fixture
def writemodel():
    return m.MelodyModel(Models.writemodel)


def test_created_elements_can_be_accessed_in_model(
    writemodel: m.MelodyModel,
):
    parent = writemodel.by_uuid("df30d27f-0efb-4896-b6b6-0757145c7ad5")
    assert isinstance(parent, mm.capellacommon.Region)
    assert isinstance(type(parent).states, m.Containment)

    newobj = parent.states.create("State", name="Booting up")

    assert newobj is not None
    assert isinstance(newobj, mm.capellacommon.State)
    assert newobj in parent.states


def test_created_elements_show_up_in_xml_after_adding_them(
    writemodel: m.MelodyModel,
):
    newobj = writemodel.la.root_component.components.create(
        name="TestComponent"
    )

    try:
        writemodel._loader[newobj.uuid]
    except KeyError as err:
        raise AssertionError(
            "Cannot find added element via subscripting"
        ) from err

    assert writemodel._loader.xpath(XPATH_UUID.format(newobj.uuid)), (
        "Cannot find added element via XPath"
    )


@pytest.mark.parametrize(
    "deletion_target",
    [0, slice(None, 1)],
)
def test_deleted_elements_are_removed(
    writemodel: m.MelodyModel, deletion_target
):
    comps = writemodel.la.root_component.components
    assert len(comps) == 2, "Precondition not met: Bad list length"

    olduuid = comps[0].uuid
    del comps[deletion_target]

    assert len(comps) != 2, "List length did not change"

    with pytest.raises(KeyError):
        writemodel._loader[olduuid]

    assert not writemodel._loader.xpath(XPATH_UUID.format(olduuid)), (
        "Element is still present in tree after deleting"
    )


def test_delete_all_deletes_matching_objects(writemodel: m.MelodyModel):
    comps = writemodel.la.root_component.components
    assert len(comps) == 2

    comps.delete_all(name="Delete Me")
    assert len(comps) == 1
    assert comps[0].name == "Keep Me"


def test_create_adds_missing_namespace_to_fragment(
    writemodel: m.MelodyModel,
) -> None:
    assert "Requirements" not in writemodel.project._element.nsmap
    module = writemodel.by_uuid("85a31dd7-7755-486b-b803-1df8915e2cf9")

    module.requirements.create(name="TestReq")
    writemodel._loader.update_namespaces()

    assert "Requirements" in writemodel.project._element.nsmap


def test_adding_a_namespace_preserves_the_capella_version_comment(
    writemodel: m.MelodyModel,
) -> None:
    assert "Requirements" not in writemodel.project._element.nsmap
    prev_elements = list(
        writemodel.project._element.itersiblings(preceding=True)
    )
    assert len(prev_elements) == 1, "No version comment to preserve?"
    module = writemodel.by_uuid("85a31dd7-7755-486b-b803-1df8915e2cf9")

    module.requirements.create(name="TestReq")
    writemodel._loader.update_namespaces()

    assert "Requirements" in writemodel.project._element.nsmap
    prev_elements = list(
        writemodel.project._element.itersiblings(preceding=True)
    )
    assert len(prev_elements) == 1


def test_deleting_an_object_purges_references_from_Association(
    writemodel: m.MelodyModel, caplog
) -> None:
    part = writemodel.by_uuid("1bd59e23-3d45-4e39-88b4-33a11c56d4e3")
    assert isinstance(part, mm.cs.Part)
    acc = type(part).type
    assert isinstance(acc, m.Single)
    assert isinstance(acc.wrapped, m.Association)
    component = writemodel.by_uuid("ea5f09e6-a0ec-46b2-bd3e-b572f9bf99d6")
    parent = component.parent

    parent.components.remove(component)
    parent.components.append(component)

    assert not list(writemodel.find_references(component))
    assert part.type is None
    assert not caplog.records


def test_deleting_an_object_purges_references_from_LinkAccessor(
    model: m.MelodyModel, caplog
) -> None:
    entity = model.by_uuid("e37510b9-3166-4f80-a919-dfaac9b696c7")
    assert isinstance(entity, mm.oa.Entity)
    assert isinstance(type(entity).activities, m.Allocation)
    activity = model.by_uuid("f1cb9586-ce85-4862-849c-2eea257f706b")

    activity.parent.activities.remove(activity)

    assert not list(model.find_references(activity))
    assert activity not in entity.activities
    assert not caplog.records


def test_deleting_an_entire_list_purges_references_to_all_list_members(
    model: m.MelodyModel, caplog
) -> None:
    component = model.by_uuid("ff7b8672-84db-4b93-9fea-22a410907fb1")
    assert isinstance(component, mm.la.LogicalComponent)
    p1 = model.by_uuid("db5681e4-4245-4207-a429-e89979f6ac71")
    p2 = model.by_uuid("7c61d723-3658-47ff-9b0c-7b016ac4cb76")
    current_ports = [i.uuid for i in component.ports]
    assert current_ports == [p1.uuid, p2.uuid], "Unexpected ports"
    assert list(model.find_references(p1)), "Dead port CP 1?"
    assert list(model.find_references(p2)), "Dead port CP 2?"

    del component.ports

    assert not list(model.find_references(p1))
    assert not list(model.find_references(p2))
    assert not caplog.records


def test_deleting_an_object_purges_references_to_children(
    model: m.MelodyModel, caplog
) -> None:
    component = model.by_uuid("a8c46457-a702-41c4-a971-c815c4c5a674")
    port = model.by_uuid("e0dcf8c2-2283-4456-98a2-146e78ba5f26")
    exchange_id = "d8655737-39ab-4482-a934-ee847c7ff6bd"
    current_refs = [
        (getattr(obj, "uuid", None), attr)
        for obj, attr, _ in model.find_references(port)
    ]
    assert port in component.ports
    assert len(current_refs) > 1, "Port has no references before test"
    assert (exchange_id, "target") in current_refs
    pkg = model.la.component_pkg
    assert pkg is not None

    pkg.components.remove(component)

    assert not list(model.find_references(port))
    assert model.by_uuid(exchange_id).target is None
    assert not caplog.records
