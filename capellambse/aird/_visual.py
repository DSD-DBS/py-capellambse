# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Parser entry point for visual elements.

Visual elements, contrary to semantic ones, do not exist in the melody
files at all.  They are used for things such as Notes and inter-diagram
hyperlinks.
"""
from __future__ import annotations

import collections.abc as cabc
import logging

from capellambse import diagram

from . import _common as c
from . import _edge_factories, _styling

LOGGER = logging.getLogger(__name__)


def from_xml(ebd: c.ElementBuilder) -> diagram.DiagramElement:
    """Deserialize a visual element."""
    el_type = ebd.data_element.attrib[c.ATT_XMT].split(":")[-1]
    if el_type not in VISUAL_TYPES:
        LOGGER.error("Unknown visual element type, skipping: %r", el_type)
        raise c.SkipObject()
    factory = VISUAL_TYPES[el_type]
    if factory is None:
        raise c.SkipObject()
    return factory(ebd)


def connector_factory(ebd: c.ElementBuilder) -> diagram.Edge:
    """Create a Connector.

    A Connector is an edge that connects Notes to arbitrary elements.
    """
    styleclass = "Connector"
    bendpoints, source, target = _edge_factories.extract_bendpoints(ebd)
    styleoverrides = _styling.apply_style_overrides(
        ebd.target_diagram.styleclass, styleclass, ebd.data_element
    )
    edge = diagram.Edge(
        bendpoints,
        uuid=ebd.data_element.attrib[c.ATT_XMID],
        styleclass=styleclass,
        # <https://github.com/python/mypy/issues/8136#issuecomment-565387901>
        styleoverrides=styleoverrides,  # type: ignore[arg-type]
    )
    assert edge.uuid is not None

    if isinstance(target, diagram.Box):
        _edge_factories.snaptarget(edge.points, -1, -2, target)
        target.add_context(edge.uuid)
    if isinstance(source, diagram.Box):
        _edge_factories.snaptarget(edge.points, 0, 1, source)
        source.add_context(edge.uuid)

    return edge


def shape_factory(ebd: c.ElementBuilder) -> diagram.Box:
    """Create a Shape."""
    assert ebd.target_diagram.styleclass is not None

    uid = ebd.data_element.attrib[c.ATT_XMID]
    label = ebd.data_element.get("description", "")
    parent = ebd.data_element.getparent()
    while parent.tag == "children":
        parent_uid = parent.attrib.get("element") or parent.attrib.get(
            c.ATT_XMID
        )
        try:
            parent = ebd.target_diagram[parent_uid]
        except KeyError:
            parent = parent.getparent()
        else:
            refpos = parent.pos
            break
    else:
        parent = None
        refpos = diagram.Vector2D(0, 0)

    try:
        layout = next(ebd.data_element.iterchildren("layoutConstraint"))
    except StopIteration:
        raise ValueError(
            "No layoutConstraint found for element {uid}"
        ) from None

    pos = refpos + (
        int(layout.attrib.get("x", "0")),
        int(layout.attrib.get("y", "0")),
    )
    size = diagram.Vector2D(
        int(layout.attrib.get("width", "0")),
        int(layout.attrib.get("height", "0")),
    )
    styleclass = ebd.data_element.attrib["type"]
    styleoverrides = _styling.apply_visualelement_styles(
        ebd.target_diagram.styleclass, f"Box.{styleclass}", ebd.data_element
    )
    return diagram.Box(
        pos,
        size,
        label=label,
        uuid=uid,
        parent=parent,
        styleclass=styleclass,
        # <https://github.com/python/mypy/issues/8136#issuecomment-565387901>
        styleoverrides=styleoverrides,  # type: ignore[arg-type]
    )


VISUAL_TYPES: dict[
    str, cabc.Callable[[c.ElementBuilder], diagram.DiagramElement]
] = {
    "BasicDecorationNode": c.SkipObject.raise_,
    "Connector": connector_factory,
    # Nodes are actually semantic elements.  If one got through to here,
    # it's an internal node, not an element root.
    "Node": c.SkipObject.raise_,
    "Shape": shape_factory,
}
