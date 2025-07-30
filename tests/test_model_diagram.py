# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

import functools

from lxml import etree

import capellambse
import capellambse.diagram

HIDDEN_UUID = "957c5799-1d4a-4ac0-b5de-33a65bf1519c"

SVG = functools.partial(etree.QName, "http://www.w3.org/2000/svg")


def test_diagram_nodes_only_include_visible_elements(
    session_shared_model: capellambse.MelodyModel,
):
    diagram = session_shared_model.diagrams.by_name(
        "[LAB] Wizard Education (hidden functions)"
    )

    assert HIDDEN_UUID not in diagram.nodes.by_uuid


def test_convert_format_converts_diagram_object_to_svg():
    diag_obj = capellambse.diagram.Diagram(
        name="Test diagram",
        viewport=capellambse.diagram.Box((10, 10), (10, 10)),
    )

    svg = capellambse.model.diagram.convert_format(None, "svg", diag_obj)

    tree = etree.fromstring(svg)
    assert tree.tag == SVG("svg")
    assert len(tree) == 2
    assert tree.get("version") == "1.1"
    assert tree.get("viewBox") == "0 0 30 30"
    assert tree.get("width") == "30"
    assert tree.get("height") == "30"

    defs, bg = tree.iterchildren()

    assert defs.tag == SVG("defs")
    assert len(defs) == 0

    assert bg.tag == SVG("rect")
    assert len(bg) == 0
    assert bg.get("x") == "0"
    assert bg.get("y") == "0"
    assert bg.get("width") == "30"
    assert bg.get("height") == "30"
    assert bg.get("fill") == "#fff"
