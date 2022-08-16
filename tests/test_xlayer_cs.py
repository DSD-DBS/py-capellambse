# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

from capellambse import MelodyModel


def test_physical_path_has_ordered_list_of_involved_items(model: MelodyModel):
    path = model.pa.all_physical_paths.by_name("card1 - card2 connection")
    cmp_0_part = model.search("Part").by_name("Compute Card 1")
    link_1 = model.pa.all_physical_links.by_name("Eth Cable 2")
    assert cmp_0_part == path.involved_items[0]
    assert link_1 == path.involved_items[1]


def test_physical_path_has_ordered_list_of_involved_links(model: MelodyModel):
    path = model.pa.all_physical_paths.by_name("card1 - card2 connection")
    link_0 = model.pa.all_physical_links.by_name("Eth Cable 2")
    link_1 = model.pa.all_physical_links.by_name("Eth Cable 3")
    assert link_0 == path.involved_links[0]
    assert link_1 == path.involved_links[1]


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
