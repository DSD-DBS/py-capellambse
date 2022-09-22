# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

from capellambse import MelodyModel


def test_physical_path_has_ordered_list_of_involved_items(model: MelodyModel):
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


def test_physical_path_has_ordered_list_of_involved_links(model: MelodyModel):
    expected = [
        "42ee9e89-d445-45a2-8280-028d4fb1038d",
        "3078ec08-956a-4c61-87ed-0143d1d66715",
    ]

    path = model.pa.all_physical_paths.by_name("card1 - card2 connection")

    actual = [i.uuid for i in path.involved_links]
    assert actual == expected


def test_physical_path_has_exchanges(model: MelodyModel):
    exchange = model.pa.all_component_exchanges.by_name("C 6")
    path = model.pa.all_physical_paths.by_name("card1 - card2 connection")
    assert path.exchanges == [exchange]


def test_physical_link_has_physical_paths(model: MelodyModel):
    link = model.pa.all_physical_links.by_name("Eth Cable 2")
    path = model.pa.all_physical_paths.by_name("card1 - card2 connection")
    assert link.physical_paths == [path]


def test_physical_link_has_exchanges(model: MelodyModel):
    link = model.pa.all_physical_links.by_name("Eth Cable 2")
    exchange = model.pa.all_component_exchanges.by_name("C 3")
    assert link.exchanges == [exchange]
