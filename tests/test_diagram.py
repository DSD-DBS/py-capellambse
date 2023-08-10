# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
import pytest

import capellambse

HIDDEN_UUID = "957c5799-1d4a-4ac0-b5de-33a65bf1519c"
SVG_IN_DESCR_UUID = "aa9931e3-116c-461e-8215-6b9fdbdd4a1b"
MODEL_ELEMENT_IN_DESCR_UUID = "edbd1ad4-31c0-4d53-b856-3ffa60e0e99b"
BOTH_IN_DESCR_UUID = "f1423c01-dd0f-4189-97e2-33c4332383f9"

HREF_START = '<a href="hlink://'
SVG_START = '<img src="data:image/svg+xml;base64'


def test_diagram_nodes_only_include_visible_elements(
    session_shared_model: capellambse.MelodyModel,
):
    diagram = session_shared_model.diagrams.by_name(
        "[LAB] Hidden Wizzard Education"
    )

    assert HIDDEN_UUID not in diagram.nodes.by_uuid


@pytest.mark.parametrize(
    "uuid,want_href,want_svg",
    (
        pytest.param(SVG_IN_DESCR_UUID, False, True, id="resolved"),
        pytest.param(
            MODEL_ELEMENT_IN_DESCR_UUID, True, False, id="unresolved"
        ),
        pytest.param(BOTH_IN_DESCR_UUID, True, True, id="partially resolved"),
    ),
)
def test_only_diagram_in_descriptions_is_resolved(
    model_6_0: capellambse.MelodyModel,
    uuid: str,
    want_href: bool,
    want_svg: bool,
):
    obj = model_6_0.by_uuid(uuid)

    assert want_href == (HREF_START in obj.description)
    assert want_svg == (SVG_START in obj.description)


def test_set_description_with_image_is_converted_to_diagram_reference(
    model_6_0: capellambse.MelodyModel,
):
    obj = model_6_0.by_uuid(SVG_IN_DESCR_UUID)
    uuid = "_RSWgcHPIEeyW3OIB4qRWZA"

    obj.description = f'<p>A diagram: <img alt="{uuid}"/> Some text</p>'

    assert obj.description.startswith("<p>A diagram")
    assert SVG_START in obj.description
    assert f'alt="{uuid}"' in obj.description
    assert obj.description.endswith("Some text</p>")


@pytest.mark.parametrize(
    "description,expected",
    (
        pytest.param(
            '<img alt="_RSWgcHPIEeyW3OIB4qRWZ1"/> Some text</p>',
            "Tried to reference a diagram which isn't in the model",
            id="unknown diagram reference",
        ),
        pytest.param(
            '<img src="..."/> Some text</p>',
            "Image needs an `alt` attribute on which a valid diagram UID",
            id="missing diagram UID",
        ),
    ),
)
def test_set_description_with_image_fails(
    model_6_0: capellambse.MelodyModel, description: str, expected: str
):
    obj = model_6_0.by_uuid(SVG_IN_DESCR_UUID)

    with pytest.raises(ValueError, match=expected):
        obj.description = description
