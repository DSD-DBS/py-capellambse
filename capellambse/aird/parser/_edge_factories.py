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
"""Factory functions for Edges inside a diagram."""
from __future__ import annotations

import collections.abc as cabc
import dataclasses
import typing as t

from capellambse import aird, helpers
from capellambse.aird import diagram

from . import _common as C
from . import _filters, _styling

# Port classes that should not be considered
# when differentiating ``PortAllocation``s.
PORTALLOCATION_CLASS_BLACKLIST = {
    "CP",
    "CP_IN",
    "CP_OUT",
    "CP_INOUT",
    "CP_UNSET",
}
XT_EXITEM = "org.polarsys.capella.core.data.information:ExchangeItem"


def generic_factory(seb: C.SemanticElementBuilder) -> aird.Edge:
    """Create an Edge from the diagram XML."""
    bendpoints, sourceport, targetport = extract_bendpoints(seb)
    if sourceport is ... or targetport is ...:
        C.LOGGER.warning(
            "Source or target of edge %r were deleted, skipping",
            seb.data_element.attrib[C.ATT_XMID],
        )
        raise C.SkipObject()

    try:
        ostyle = next(seb.diag_element.iterchildren("ownedStyle"))
    except StopIteration:
        raise ValueError(
            "Cannot find style definition for edge {}".format(
                seb.data_element.attrib["element"]
            )
        ) from None
    routingstyle = ostyle.attrib.get("routingStyle")

    {"manhattan": route_manhattan, "tree": route_tree,}.get(
        routingstyle, lambda *args: None
    )(bendpoints, sourceport, targetport)

    edge = aird.Edge(
        bendpoints,
        source=sourceport,
        target=targetport,
        uuid=seb.data_element.attrib["element"],
        styleclass=seb.styleclass,
    )

    _filters.setfilters(seb, edge)
    edge.styleoverrides = _styling.apply_style_overrides(
        seb.target_diagram.styleclass, f"Edge.{seb.styleclass}", ostyle
    )
    edge.label = _construct_label(edge, seb)

    if isinstance(targetport, aird.Box):
        snaptarget(edge.points, -1, -2, targetport, movetarget=not edge.hidden)
    if targetport is not None:
        snaptarget(edge.points, -1, -2, targetport)
    if isinstance(sourceport, aird.Box):
        snaptarget(edge.points, 0, 1, sourceport, movetarget=not edge.hidden)
    if sourceport is not None:
        snaptarget(edge.points, 0, 1, sourceport)

    if seb.melodyobj is not None:
        sourceport.add_context(seb.data_element.attrib["element"])
        if targetport is not None:
            targetport.add_context(seb.data_element.attrib["element"])

    return edge


def extract_bendpoints(
    seb: C.ElementBuilder,
) -> tuple[list[aird.Vector2D], aird.DiagramElement, aird.DiagramElement]:
    """Extract the bendpoints from an Edge's XML.

    Parameters
    ----------
    seb
        The element builder instance

    Returns
    -------
    tuple
        A 3-tuple with the list of bendpoints, the source element and
        the target element.
    """
    uid = (
        seb.data_element.attrib.get("element")
        or seb.data_element.attrib[C.ATT_XMID]
    )
    sourceport, targetport = get_end_ports(seb)
    sourcebounds = sourceport.bounds
    targetbounds = targetport.bounds

    try:
        bendpoints_elm = next(seb.data_element.iterchildren("bendpoints"))
    except StopIteration:
        raise ValueError(f"No bendpoints definition for {uid!r}") from None

    bendpoints = []
    bendpoint_type = bendpoints_elm.attrib.get(C.ATT_XMT)

    if bendpoint_type == "notation:RelativeBendpoints":
        # Translate relative to absolute coordinates
        try:
            sourceanchor = next(
                seb.data_element.iterchildren("sourceAnchor")
            ).attrib["id"]
        except (StopIteration, KeyError):
            sourceanchor = "(0.5, 0.5)"
        sourceanchor = helpers.ssvparse(
            sourceanchor, float, parens="()", num=2
        )
        refpos = sourcebounds.pos + sourcebounds.size @ sourceanchor

        bendpoints_attrib = bendpoints_elm.attrib.get(
            "points", "[0, 0, 0, 0]$[0, 0, 0, 0]"
        )
        for point in bendpoints_attrib.split("$"):
            bendpoints.append(
                refpos + helpers.ssvparse(point, int, parens="[]", num=4)[:2]
            )

        if all(b == bendpoints[0] for b in bendpoints):
            # Draw a straight line between source's and target's center
            bendpoints = [
                sourcebounds.pos + (sourcebounds.size / 2),
                targetbounds.pos + (targetbounds.size / 2),
            ]
    else:
        raise ValueError(f"Unknown bendpoint type {bendpoint_type}")

    return bendpoints, sourceport, targetport


def get_end_ports(
    seb: C.ElementBuilder,
) -> tuple[aird.DiagramElement, aird.DiagramElement]:
    """Retrieve the source and target port of an Edge in the diagram."""

    def get_port_object(portside: str) -> aird.DiagramElement:
        try:
            port = seb.data_element.attrib[portside]
            try:
                return seb.target_diagram[port]
            except KeyError:
                elem = seb.melodyloader[
                    helpers.fragment_link(seb.fragment, port)
                ]
                return seb.target_diagram[elem.attrib["element"]]
        except KeyError:
            uid = (
                seb.data_element.attrib.get("element")
                or seb.data_element.attrib[C.ATT_XMID]
            )
            C.LOGGER.warning(
                "Cannot draw edge %r: %s missing from diagram", uid, portside
            )
            raise C.SkipObject() from None

    return (get_port_object("source"), get_port_object("target"))


def route_manhattan(
    points: cabc.MutableSequence[aird.Vector2D],
    source: aird.DiagramElement,
    target: aird.DiagramElement,
) -> None:
    """Reroute an Edge using the "Manhattan" routing style.

    Parameters
    ----------
    points
        The list of points
    source
        A Box to originate from
    target
        A Box or Edge to point to
    """
    # TODO Implement full rerouting
    #      Currently all this function does is slightly straighten the line,
    #      with very narrow angle constraints.  This works okay for many cases,
    #      but — especially when no points were given at all — this simple
    #      approach sometimes fails to provide usable results.
    del source, target

    # Add synthetic bendpoints in the center, so line straightening will work
    if len(points) == 2:
        direction = points[1] - points[0]
        axis = direction.closestaxis()
        angle = abs(axis.angleto(direction))
        # XXX Rough estimates for threshold - adjust if needed
        if 0.017453292519943295 < angle < 0.4363323129985824:  # 1° .. 25°
            center = points[0] + direction / 2
            points = [points[0], center, center, points[1]]

    if len(points) > 2:
        # Snap the second and second-to-last bendpoint to make perfect
        # straight lines if their angle deviation is below a threshold
        for i, next_i in [(1, 0), (-2, -1)]:
            direction = points[next_i] - points[i]
            axis = direction.closestaxis()
            if abs(axis.angleto(direction)) < 0.4363323129985824:  # 25°
                points[i] = aird.Vector2D(
                    points[i].x if axis.x != 0 else points[next_i].x,
                    points[i].y if axis.y != 0 else points[next_i].y,
                )


def route_tree(
    points: cabc.MutableSequence[aird.Vector2D],
    source: aird.DiagramElement,
    target: aird.DiagramElement,
) -> None:
    """Reroute an Edge using the "Tree" routing style.

    Parameters
    ----------
    points
        The list of points
    source
        A Box to originate from
    target
        A Box or Edge to point to
    """
    assert len(points) >= 2
    sourcebounds = source.bounds
    sourcecenter = sourcebounds.pos + sourcebounds.size / 2
    targetbounds = target.bounds
    targetcenter = targetbounds.pos + targetbounds.size / 2

    source_y = (
        points[0]
        .boxsnap(
            sourcebounds.pos,
            sourcebounds.pos + sourcebounds.size,
            (0, targetcenter.y - sourcecenter.y),
        )
        .y
    )
    target_y = (
        points[-1]
        .boxsnap(
            targetbounds.pos,
            targetbounds.pos + targetbounds.size,
            (0, sourcecenter.y - targetcenter.y),
        )
        .y
    )
    sourcepoint = aird.Vector2D(sourcecenter.x, source_y)
    targetpoint = aird.Vector2D(targetcenter.x, target_y)

    if len(points) == 4:
        centerpoint_y = (points[1].y + points[2].y) / 2
    else:
        centerpoint_y = (source_y + target_y) / 2

    points[:] = [
        sourcepoint,
        aird.Vector2D(sourcepoint.x, centerpoint_y),
        aird.Vector2D(targetpoint.x, centerpoint_y),
        targetpoint,
    ]


@t.overload
def snaptarget(
    points: cabc.MutableSequence[aird.Vector2D],
    i: int,
    next_i: int,
    target: aird.Box,
    movetarget: bool = False,
) -> None:
    ...


@t.overload
def snaptarget(
    points: cabc.MutableSequence[aird.Vector2D],
    i: int,
    next_i: int,
    target: aird.DiagramElement,
    movetarget: t.Literal[False] = ...,
) -> None:
    ...


def snaptarget(
    points: cabc.MutableSequence[aird.Vector2D],
    i: int,
    next_i: int,
    target: aird.DiagramElement,
    movetarget: bool = False,
) -> None:
    """Snap an Edge's end and (optionally) its target into place.

    Parameters
    ----------
    points
        A list of points describing the entire edge
    i
        The end point index in ``points``
    next_i
        The next point's index in ``points``
    target
        The Edge target (either a Box or another Edge)
    movetarget
        Allow to move the target under certain conditions
    """
    if not diagram.SNAPPING or target is None:
        return

    direction = points[next_i] - points[i]
    axis = direction.closestaxis()
    angle = abs(axis.angleto(direction))
    tbounds = target.bounds

    if angle <= 0.08726646259971647:  # 5°
        if len(points) > 2:
            # Prefer to move the Edge's next point instead of the target
            naxis = aird.Vector2D(axis.y, axis.x)
            snapped = (
                tbounds.pos + tbounds.size / 2
                if target.port
                else target.vector_snap(points[next_i], direction)
            )
            points[next_i] = points[next_i] @ abs(axis) + snapped @ abs(naxis)
        elif movetarget and target.port and not target.context:
            # The target port doesn't have other context yet,
            # so it's safe to move it around.
            assert isinstance(target, aird.Box)
            target.pos = aird.Vector2D(
                target.pos.x
                if axis.x != 0
                else points[next_i].x - target.size.x / 2,
                target.pos.y
                if axis.y != 0
                else points[next_i].y - target.size.y / 2,
            )
            target.snap_to_parent()

    # Snap the Edge into the target
    if target.port:
        # Use the port's center instead of the calculated position
        assert isinstance(target, aird.Box)
        points[i] = target.pos + target.size / 2

    points[i] = target.vector_snap(points[i], direction)


def _construct_label(
    edge: aird.Edge, seb: C.SemanticElementBuilder
) -> aird.Box:
    """Construct the label box for an edge."""
    # Use exchanged items as label text if possible
    if seb.melodyobj is None:
        labeltext = seb.diag_element.attrib.get("name", "")
    else:
        labeltext = seb.melodyobj.attrib.get("name", "")

    # Position the label
    labelanchor, travel_direction = _find_center(edge)
    label_layout = helpers.xpath_fetch_unique(
        './children[@type="6001"]/layoutConstraint',
        seb.data_element,
        "Label layoutConstraints",
        edge.uuid,
    )
    label_pos = aird.Vector2D(
        int(label_layout.get("x", "0")),
        int(label_layout.get("y", "0")),
    )
    label_size = aird.Vector2D(
        int(label_layout.attrib.get("width", "0")),
        int(label_layout.attrib.get("height", "0")),
    )

    # Rotate the position vector into place
    label_pos = label_pos.rotatedby(
        aird.Vector2D(1, 0).angleto(travel_direction)
    )

    label = C.CenterAnchoredBox(
        labelanchor + label_pos,
        label_size,
        label=labeltext,
        styleclass="EdgeAnnotation",
    )
    return label


def _find_center(
    points: cabc.Sequence[aird.Vector2D],
) -> tuple[aird.Vector2D, aird.Vector2D]:
    """Calculate the center point of the edge described by `points`."""
    # Calculate the length of each part
    lengths = [
        (points[i] - points[i + 1]).length for i in range(len(points) - 1)
    ]
    total_length = sum(lengths)
    center_length = total_length / 2
    current_length = 0.0
    current_position = points[0]

    for i in range(len(points) - 1):
        next_length = lengths[i]
        new_length = current_length + next_length
        if new_length > center_length:
            break  # Would overshoot
        current_length = new_length
        current_position = points[i + 1]

    try:
        # Complete the jump from the last point towards the actual edge center
        direction = (points[i + 1] - points[i]).normalized
    except ZeroDivisionError:
        direction = aird.Vector2D(1, 0)

    return (
        current_position + direction * (center_length - current_length),
        direction,
    )


def labelless_factory(seb: C.SemanticElementBuilder) -> aird.Edge:
    """Create an edge that should never have a label."""
    edge = generic_factory(seb)
    edge.label = None
    return edge


def port_allocation_factory(seb: C.SemanticElementBuilder) -> aird.Edge:
    """Specially handle ``PortAllocation`` type edges.

    Generic PortAllocations need to be differentiated into specific port
    allocation types (e.g. FIPAllocation), based on the types of ports
    they connect with.
    """
    if seb.melodyobj is not None:
        portclasses = set()

        for port in get_end_ports(seb):
            if (
                port.styleclass
                and port.styleclass not in PORTALLOCATION_CLASS_BLACKLIST
            ):
                portclasses.add(port.styleclass)

        if portclasses:
            seb.styleclass = f"{'_'.join(sorted(portclasses))}Allocation"
    return generic_factory(seb)


def state_transition_factory(seb: C.SemanticElementBuilder) -> aird.Edge:
    """Create a StateTransition.

    StateTransitions (connecting two Modes or two States) do not use the
    transition's name as their label, but rather some transition-
    specific attributes.
    """
    edge = generic_factory(seb)
    if edge.label is not None:  # pragma: no branch
        label = ", ".join(
            i.get("name", "(unnamed trigger)")
            for i in seb.melodyloader.follow_links(
                seb.melodyobj, seb.melodyobj.get("triggers", "")
            )
            if i is not None
        )

        if guard := _guard_condition(seb, "guard"):
            label = f"{label} [{guard}]"

        effects = seb.melodyloader.follow_links(
            seb.melodyobj, seb.melodyobj.get("effect", "")
        )
        if effects:
            effects_str = ", ".join(
                i.get("name", "") for i in effects if i is not None
            )
            label = f"{label} / {effects_str}"

        edge.label.label = label
    return edge


def sequence_link_factory(seb: C.SemanticElementBuilder) -> aird.Edge:
    """Create a SequenceLink.

    Sequence links (in Operational Process Diagrams) use the guard
    condition as label, if it is set.  Otherwise the label stays empty.
    """
    edge = generic_factory(seb)
    guard = _guard_condition(seb, "condition")
    if guard and edge.label is not None:
        edge.label.label = guard
    return edge


def constraint_factory(seb: C.SemanticElementBuilder) -> aird.Edge:
    """Create the edge for a Constraint.

    As the Box already contains the label, it is not needed on the Edge.

    See Also
    --------
    capellambse.aird.parser._box_factories.constraint_factory :
        The accompanying box factory.
    """
    edge = generic_factory(seb)
    edge.label = None
    return edge


def fcil_factory(seb: C.SemanticElementBuilder) -> aird.Edge:
    """Create a FunctionalChainInvolvementLinks."""
    seb.melodyobj = seb.melodyloader.follow_link(
        seb.melodyobj, seb.melodyobj.get("involved")
    )
    xtype = helpers.xtype_of(seb.melodyobj)
    assert xtype is not None
    seb.styleclass = xtype.split(":")[-1]
    return generic_factory(seb)


def _guard_condition(seb: C.SemanticElementBuilder, attr: str) -> str:
    """Extract the guard condition's text from the XML."""
    try:
        guard = seb.melodyloader.follow_links(
            seb.melodyobj, seb.melodyobj.get(attr, "")
        )[0]
    except IndexError:
        return ""
    else:
        return C.get_spec_text(dataclasses.replace(seb, melodyobj=guard))


def req_relation_factory(seb: C.SemanticElementBuilder) -> aird.Edge:
    """Factory for Capella[Incoming/Outgoing]Relation"""
    label = seb.melodyobj.attrib.get("name", "")
    if not label:
        try:
            reltype = seb.melodyloader[seb.melodyobj.attrib["relationType"]]
            label = reltype.attrib["ReqIFLongName"]
        except KeyError:
            C.LOGGER.warning(
                "Requirement-Relation %r has no RelationType",
                seb.data_element.attrib[C.ATT_XMID],
            )
        finally:
            seb.melodyobj.attrib["name"] = label

    return generic_factory(seb)


def include_extend_factory(seb: C.SemanticElementBuilder) -> aird.Edge:
    """Factory for AbstractCapability[Includes/Extends]"""
    if seb.melodyobj.attrib.get("name") is None:
        seb.melodyobj.attrib["name"] = seb.diag_element.attrib.get("name", "")
    return generic_factory(seb)
