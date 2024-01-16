# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import pathlib

import pytest
from lxml import etree

import capellambse
import capellambse.diagram
from capellambse.svg import SVGDiagram, decorations, generate, helpers, symbols

TEST_LAB = "[LAB] Wizzard Education"
TEST_DIAGS = [
    TEST_LAB,
    "[OAB] Operational Context",
    "[OCB] Operational Capabilities",
    "[OPD] Obtain food via hunting",
    "[MSM] States of Functional Human Being",
    "[SAB] System",
    "[OEBD] Operational Context",
    "[PAB] Physical System",
    "[LDFB] Test flow",
    "[CC] Capability",
    "[PAB] A sample vehicle arch",
]
FREE_SYMBOLS = {
    "OperationalCapabilitySymbol",
    "AndControlNodeSymbol",
    "ItControlNodeSymbol",
    "OrControlNodeSymbol",
    "FinalStateSymbol",
    "InitialPseudoStateSymbol",
    "TerminatePseudoStateSymbol",
    "StickFigureSymbol",
}


@pytest.fixture(name="tmp_json")
def tmp_json_fixture(
    model: capellambse.MelodyModel, tmp_path: pathlib.Path
) -> pathlib.Path:
    """Return tmp path of diagram json file."""
    dest = tmp_path / (TEST_LAB + ".json")
    diagram = model.diagrams.by_name(TEST_LAB).render(None)
    diagram_json = capellambse.diagram.DiagramJSONEncoder().encode(diagram)
    dest.write_text(diagram_json)
    return dest


class TestSVG:
    def test_diagram_meta_data_attributes(
        self, tmp_json: pathlib.Path
    ) -> None:
        diag_meta = generate.DiagramMetadata.from_dict(
            json.loads(tmp_json.read_text())
        )
        assert diag_meta.name == TEST_LAB
        assert diag_meta.pos == (15, 15)
        assert diag_meta.size == (1162, 611)
        assert diag_meta.viewbox == "15 15 1162 611"
        assert diag_meta.class_ == "Logical Architecture Blank"

    def test_diagram_from_json_path_componentports(
        self, tmp_json: pathlib.Path
    ) -> None:
        tree = etree.fromstring(
            SVGDiagram.from_json_path(tmp_json).to_string()
        )

        cp_in_exists: bool = False
        cp_inout_exists: bool = False
        cp_out_exists: bool = False
        cp_unset_exists: bool = False
        cp_reference_exists: bool = False

        for item in tree.iter():
            # The class CP should not exist anymore as it has been replaced
            # with CP_IN, CP_OUT, CP_UNSET or CP_INOUT
            assert item.get("class") != "Box CP"

            # Check that the classes CP_IN, CP_OUT, CP_UNSET and CP_INOUT exist
            if item.get("class") == "Box CP_IN":
                cp_in_exists = True
            elif item.get("class") == "Box CP_OUT":
                cp_out_exists = True
            elif item.get("class") == "Box CP_INOUT":
                cp_inout_exists = True
            elif item.get("class") == "Box CP_UNSET":
                cp_unset_exists = True

            # Check that reference symbol for CP exists
            if (
                item.tag == "{http://www.w3.org/2000/svg}symbol"
                and item.get("id") == "ComponentPortSymbol"
            ):
                cp_reference_exists = True

        assert cp_in_exists
        assert cp_out_exists
        assert cp_inout_exists
        assert cp_unset_exists
        assert cp_reference_exists

    @pytest.fixture
    def tmp_svg(self, tmp_path: pathlib.Path) -> SVGDiagram:
        name = "Test svg"
        meta = generate.DiagramMetadata(
            pos=(0, 0), size=(1, 1), name=name, class_="TEST"
        )
        svg = SVGDiagram(meta, [])
        svg.drawing.filename = str(tmp_path / name)
        return svg

    def test_diagram_saves(self, tmp_svg: SVGDiagram) -> None:
        tmp_svg.save()
        assert pathlib.Path(tmp_svg.drawing.filename).is_file()

    def test_base_css_styles(self, tmp_json: pathlib.Path) -> None:
        tree = etree.fromstring(
            SVGDiagram.from_json_path(tmp_json).to_string()
        )
        style_ = tree.get("style")
        assert style_

    @pytest.mark.parametrize("diagram_name", TEST_DIAGS)
    def test_diagram_decorations(
        self, model: capellambse.MelodyModel, diagram_name: str
    ):
        """Test diagrams get rendered successfully."""
        diag = model.diagrams.by_name(diagram_name)
        diag.render("svg")


class TestDecoFactory:
    @pytest.mark.parametrize(
        "class_",
        ["LogicalComponentSymbol", "LogicalHumanActorSymbol", "EntitySymbol"],
    )
    def test_deco_factory_contains_styling_for_given_styleclass(
        self, class_: str
    ):
        assert class_ in decorations.deco_factories

    def test_deco_factory_returns_symbol_factory_for_given_styleclass(self):
        deco_factory = decorations.DecoFactory(symbols.port_symbol, ())

        assert decorations.deco_factories["PortSymbol"] == deco_factory

    @pytest.mark.parametrize(
        "class_", ["ImaginaryClassSymbol", "NothingSymbol"]
    )
    def test_deco_factory_logs_error_when_not_containing_given_styleclass(
        self, caplog, class_: str
    ):
        assert class_ not in decorations.deco_factories
        assert (
            decorations.deco_factories[class_]
            is decorations.deco_factories["ErrorSymbol"]
        )
        with caplog.at_level(0, logger="decorations"):
            assert (
                caplog.messages[-1] == f"{class_} wasn't found in factories."
            )

    @pytest.mark.parametrize("attr", ["start", "translate", "offsets"])
    def test_making_linear_gradient_faulty_cases_raise_ValueError(
        self, attr: str
    ):
        params = {
            "id_": "test",
            attr: (0, 0, 0),
        }
        with pytest.raises(ValueError):
            symbols._make_lgradient(**params)

    def test_making_linear_gradient_with_translate(self):
        gradient = symbols._make_lgradient("test", translate=(0, 0))
        assert gradient.attribs.get("gradientTransform") == "translate(0 0)"


class TestSVGHelpers:
    def test_check_for_horizontal_overflow_recognizes_tabs_and_breaks(
        self,
    ) -> None:
        lines, margin, max_text_width = helpers.check_for_horizontal_overflow(
            "             • item 1\n             • item 2", 100, 0, 0
        )
        assert lines == ["             • item 1", "             • item 2"]
        assert 10 <= margin < 13
        for line in lines:
            assert capellambse.helpers.extent_func(line)[0] <= max_text_width
