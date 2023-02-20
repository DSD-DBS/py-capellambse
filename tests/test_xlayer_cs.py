# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
import pytest

from capellambse import MelodyModel
from capellambse.model.crosslayer import cs

HOGWARTS_UUID = "0d2edb8f-fa34-4e73-89ec-fb9a63001440"


def test_PhysicalPath_has_ordered_list_of_involved_items(model: MelodyModel):
    expected = [
        "544549d6-2aa4-44c2-b2ae-a86302f48e62",
        "42ee9e89-d445-45a2-8280-028d4fb1038d",
        "ea8cd402-3d9a-469a-a2ce-2bc1252c3a01",
        "3078ec08-956a-4c61-87ed-0143d1d66715",
        "baa3047c-9cb4-40a7-9b67-b9b5f76fd2ee",
    ]

    path = model.pa.all_physical_paths.by_name("card1 - card2 connection")

    actual = [i.uuid for i in path.involved_items]
    assert actual == expected


def test_PhysicalPath_has_ordered_list_of_involved_links(model: MelodyModel):
    expected = [
        "42ee9e89-d445-45a2-8280-028d4fb1038d",
        "3078ec08-956a-4c61-87ed-0143d1d66715",
    ]

    path = model.pa.all_physical_paths.by_name("card1 - card2 connection")

    actual = [i.uuid for i in path.involved_links]
    assert actual == expected


def test_PhysicalPath_has_exchanges(model: MelodyModel):
    exchange = model.pa.all_component_exchanges.by_name("C 6")
    path = model.pa.all_physical_paths.by_name("card1 - card2 connection")
    assert path.exchanges == [exchange]


def test_PhysicalLink_has_physical_paths(model: MelodyModel):
    link = model.pa.all_physical_links.by_name("Eth Cable 2")
    path = model.pa.all_physical_paths.by_name("card1 - card2 connection")
    assert link.physical_paths == [path]


def test_PhysicalLink_has_exchanges(model: MelodyModel):
    link = model.pa.all_physical_links.by_name("Eth Cable 2")
    exchange = model.pa.all_component_exchanges.by_name("C 3")
    assert link.exchanges == [exchange]


def test_PhysicalLink_setting_ends(model: MelodyModel):
    link = model.pa.all_physical_links.by_name("Eth Cable 2")
    source_pp = model.by_uuid("76d9c301-c0ad-4615-9f02-b804b018decf")
    target_pp = model.by_uuid("53c9fe29-18e2-4642-906e-b7507bf0ff39")

    link.ends = [source_pp, target_pp]

    assert source_pp == link.ends[0]
    assert source_pp == link.source
    assert target_pp == link.ends[1]
    assert target_pp == link.target


def test_PhysicalLink_setting_source_and_target(model: MelodyModel):
    link = model.pa.all_physical_links.by_name("Eth Cable 2")
    source_pp = model.by_uuid("76d9c301-c0ad-4615-9f02-b804b018decf")
    target_pp = model.by_uuid("53c9fe29-18e2-4642-906e-b7507bf0ff39")

    link.source = source_pp
    link.target = target_pp

    assert source_pp == link.ends[0]
    assert source_pp == link.source
    assert target_pp == link.ends[1]
    assert target_pp == link.target


def test_Components_have_parts(model: MelodyModel):
    comp = model.by_uuid(HOGWARTS_UUID)

    for part in comp.parts:
        assert isinstance(part, cs.Part)


@pytest.mark.parametrize(
    "uuid",
    [
        pytest.param(HOGWARTS_UUID, id="Component"),
        pytest.param(
            "84c0978d-9a32-4f5b-8013-5b0b6adbfd73", id="ComponentPkg"
        ),
    ],
)
def test_component_creation_also_creates_a_part(model: MelodyModel, uuid: str):
    name = "Test"
    logical_parts = model.search("Part", below=model.la).by_name
    assert name not in logical_parts, "Part already exists"
    obj = model.by_uuid(uuid)

    comp = obj.components.create(name=name)

    assert (part := model.search("Part", below=model.la).by_name(name))
    assert isinstance(part, cs.Part)
    assert part in comp.representing_parts
    assert part.type == comp


def test_changed_Component_name_is_copied_to_the_parts(model: MelodyModel):
    name = "Test"

    comp = model.by_uuid(HOGWARTS_UUID)
    assert comp.representing_parts
    comp.name = name
    comp.allocated_functions.append(model.la.root_function)

    assert all(i.name == name for i in comp.representing_parts)
