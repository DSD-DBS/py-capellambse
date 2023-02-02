# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Factory functions for Edges inside a diagram."""
from __future__ import annotations

import collections.abc as cabc
import dataclasses
import math
import typing as t

from capellambse import diagram, helpers

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


def generic_factory(seb: C.SemanticElementBuilder) -> diagram.Edge:
    """Create an Edge from the diagram XML."""
    bendpoints, sourceport, targetport = extract_bendpoints(seb)

    try:
        ostyle = next(seb.diag_element.iterchildren("ownedStyle"))
    except StopIteration:
        raise ValueError(
            "Cannot find style definition for edge"
            f" {seb.data_element.attrib['element']}"
        ) from None
    routingstyle = ostyle.attrib.get("routingStyle")

    if not bendpoints:
        if routingstyle == "manhattan":
            bendpoints = route_manhattan(sourceport, targetport)
        elif routingstyle == "tree":
            bendpoints = route_tree(sourceport, targetport)
        else:
            bendpoints = route_oblique(sourceport, targetport)

    edge = diagram.Edge(
        bendpoints,
        source=sourceport,
        target=targetport,
        uuid=seb.data_element.attrib["element"],
        styleclass=seb.styleclass,
    )

    _filters.setfilters(seb, edge)
    # <https://github.com/python/mypy/issues/8136#issuecomment-565387901>
    # pylint: disable-next=line-too-long
    edge.styleoverrides = _styling.apply_style_overrides(  # type: ignore[assignment]
        seb.target_diagram.styleclass, f"Edge.{seb.styleclass}", ostyle
    )
    edge.labels.extend(_construct_labels(edge, seb))

    if isinstance(targetport, diagram.Box):
        snaptarget(edge, -1, -2, targetport, not edge.hidden, routingstyle)
    if isinstance(sourceport, diagram.Box):
        snaptarget(edge, 0, 1, sourceport, not edge.hidden, routingstyle)

    sourceport.add_context(seb.data_element.attrib["element"])
    if targetport is not None:
        targetport.add_context(seb.data_element.attrib["element"])

    return edge


def extract_bendpoints(
    seb: C.ElementBuilder,
) -> tuple[
    list[diagram.Vector2D], diagram.DiagramElement, diagram.DiagramElement
]:
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
        if sourceanchor.endswith(" custom"):
            sourceanchor = sourceanchor[: -len(" custom")]
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

        if len(bendpoints) == 1 or all(b == bendpoints[0] for b in bendpoints):
            bendpoints = []
    else:
        raise ValueError(f"Unknown bendpoint type {bendpoint_type}")

    return bendpoints, sourceport, targetport


def get_end_ports(
    seb: C.ElementBuilder,
) -> tuple[diagram.DiagramElement, diagram.DiagramElement]:
    """Retrieve the source and target port of an Edge in the diagram."""

    def get_port_object(portside: str) -> diagram.DiagramElement:
        try:
            port = seb.data_element.attrib[portside]
            try:
                return seb.target_diagram[port]
            except KeyError:
                elem = seb.melodyloader.follow_link(seb.data_element, port)
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
    source: diagram.DiagramElement,
    target: diagram.DiagramElement,
) -> list[diagram.Vector2D]:
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

    source_point = source.vector_snap(
        source.center,
        source=target.center,
        style=diagram.RoutingStyle.MANHATTAN,
    )
    target_point = target.vector_snap(
        target.center,
        source=source.center,
        style=diagram.RoutingStyle.MANHATTAN,
    )

    if abs(source_point.x - target_point.x) > abs(
        source_point.y - target_point.y
    ):
        p1 = diagram.Vector2D(
            (source_point.x + target_point.x) / 2, source_point.y
        )
        p2 = diagram.Vector2D(p1.x, target_point.y)
    else:
        p1 = diagram.Vector2D(
            source_point.x, (source_point.y + target_point.y) / 2
        )
        p2 = diagram.Vector2D(target_point.x, p1.y)

    return [source_point, p1, p2, target_point]


def route_tree(
    source: diagram.DiagramElement,
    target: diagram.DiagramElement,
) -> list[diagram.Vector2D]:
    """Reroute an Edge using the "Tree" routing style.

    Parameters
    ----------
    source
        A Box to originate from
    target
        A Box or Edge to point to
    """
    sourcebounds = source.bounds
    sourcecenter = sourcebounds.pos + sourcebounds.size / 2
    targetbounds = target.bounds
    targetcenter = targetbounds.pos + targetbounds.size / 2

    source_y = sourcebounds.pos.y + sourcebounds.size.y * (
        sourcecenter.y > targetcenter.y
    )
    target_y = targetbounds.pos.y + targetbounds.size.y * (
        targetcenter.y > sourcecenter.y
    )
    centerpoint_y = (source_y + target_y) / 2

    return [
        diagram.Vector2D(sourcecenter.x, source_y),
        diagram.Vector2D(sourcecenter.x, centerpoint_y),
        diagram.Vector2D(targetcenter.x, centerpoint_y),
        diagram.Vector2D(targetcenter.x, target_y),
    ]


def route_oblique(
    source: diagram.DiagramElement,
    target: diagram.DiagramElement,
) -> list[diagram.Vector2D]:
    """Reroute an Edge using the "Oblique" routing style."""
    return [source.center, target.center]


def snaptarget(
    points: cabc.MutableSequence[diagram.Vector2D],
    i: int,
    next_i: int,
    target: diagram.DiagramElement,
    movetarget: bool = False,
    routingstyle: str | None = None,
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
    routingstyle
        The routing style of the edge that caused this call
    """
    del movetarget

    if i < 0:
        i += len(points)
    if next_i < 0:
        next_i += len(points)
    assert i >= 0
    assert next_i >= 0

    if not diagram.SNAPPING or target is None:
        return

    if routingstyle == "manhattan":
        snap_manhattan(points, i, next_i, target)
    elif routingstyle == "tree":
        snap_tree(points, i, next_i, target)
    else:
        snap_oblique(points, i, next_i, target)


def snap_oblique(
    points: t.MutableSequence[diagram.Vector2D],
    i: int,
    next_i: int,
    target: diagram.DiagramElement,
) -> None:
    """Snap ``points``' end to ``target`` in a straight line."""
    points[i] = target.vector_snap(
        points[i], source=points[next_i], style=diagram.RoutingStyle.OBLIQUE
    )


def snap_manhattan(
    points: t.MutableSequence[diagram.Vector2D],
    i: int,
    next_i: int,
    target: diagram.DiagramElement,
) -> None:
    """Snap ``points``' end to ``target`` with axis-parallel lines."""
    direction = points[i] - points[next_i]
    axis = direction.closestaxis()
    manhattan = math.isclose(axis.angleto(direction), 0)
    if not manhattan:
        translate = points[next_i] @ (not axis.x, not axis.y)
        end = points[i] @ abs(axis)
        points[i] = end + translate

    endpoint = target.vector_snap(
        points[i], source=points[next_i], style=diagram.RoutingStyle.MANHATTAN
    )

    if axis.x:
        if math.isclose(endpoint.y, points[i].y):
            points[i] = endpoint
        else:
            points[i] = diagram.Vector2D(endpoint.x, points[i].y)
            points.insert(i + (i > next_i), endpoint)
    else:
        if math.isclose(endpoint.x, points[i].x):
            points[i] = endpoint
        else:
            points[i] = diagram.Vector2D(points[i].x, endpoint.y)
            points.insert(i + (i > next_i), endpoint)


def snap_tree(
    points: t.MutableSequence[diagram.Vector2D],
    i: int,
    next_i: int,
    target: diagram.DiagramElement,
) -> None:
    """Snap ``points``' end to ``target`` in tree routing style."""
    endpoint = target.vector_snap(
        points[i], source=points[next_i], style=diagram.RoutingStyle.TREE
    )

    if math.isclose(endpoint.x, points[i].x):
        points[i] = endpoint
    else:
        points[i] = diagram.Vector2D(endpoint.x, points[i].y)
        points.insert(
            i + (i > next_i), diagram.Vector2D(endpoint.x, points[next_i].y)
        )


def _construct_labels(
    edge: diagram.Edge, seb: C.SemanticElementBuilder
) -> list[diagram.Box]:
    """Construct the label box for an edge."""
    refpoints = _find_refpoints(edge)
    layouts = seb.data_element.xpath("./children/layoutConstraint")
    labels: list[diagram.Box] = []
    for (labelanchor, travel_direction), layout, melodyobj in zip(
        refpoints, layouts, seb.melodyobjs
    ):
        labeltext = melodyobj.get("name", "")

        label_pos = diagram.Vector2D(
            int(layout.get("x", "0")),
            int(layout.get("y", "0")),
        )
        label_size = diagram.Vector2D(
            int(layout.attrib.get("width", "0")),
            int(layout.attrib.get("height", "0")),
        )

        # Rotate the position vector into place
        label_pos = label_pos.rotatedby(travel_direction.angleto((1, 0)))

        labels.append(
            C.CenterAnchoredBox(
                labelanchor + label_pos,
                label_size,
                label=labeltext,
                styleclass="EdgeAnnotation",
            )
        )
    return labels


def _find_refpoints(
    points: cabc.Sequence[diagram.Vector2D],
) -> list[tuple[diagram.Vector2D, diagram.Vector2D]]:
    """Calculate the center point of the edge described by `points`."""
    refpoints: list[tuple[diagram.Vector2D, diagram.Vector2D]] = []

    lengths = [
        (points[i] - points[i + 1]).length for i in range(len(points) - 1)
    ]
    total_length = sum(lengths)
    refpoint_lengths = [
        total_length * 0.15,
        total_length * 0.5,
        total_length * 0.85,
    ]
    current_length = 0.0
    current_position = points[0]
    new_length = lengths[0]
    i = 0

    for next_refpoint in refpoint_lengths:
        while new_length < next_refpoint:
            i += 1
            current_length = new_length
            new_length += lengths[i]
            current_position = points[i]

        try:
            dir = (points[i + 1] - points[i]).normalized
        except ZeroDivisionError:  # pragma: no cover
            dir = diagram.Vector2D(1, 0)
        pos = current_position + dir * (next_refpoint - current_length)
        refpoints.append((pos, dir))

    refpoints[0], refpoints[1] = refpoints[1], refpoints[0]
    return refpoints


def labelless_factory(seb: C.SemanticElementBuilder) -> diagram.Edge:
    """Create an edge that should never have a label."""
    edge = generic_factory(seb)
    edge.labels = []
    return edge


def port_allocation_factory(seb: C.SemanticElementBuilder) -> diagram.Edge:
    """Specially handle ``PortAllocation`` type edges.

    Generic PortAllocations need to be differentiated into specific port
    allocation types (e.g. FIPAllocation), based on the types of ports
    they connect with.
    """
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


def state_transition_factory(seb: C.SemanticElementBuilder) -> diagram.Edge:
    """Create a StateTransition.

    StateTransitions (connecting two Modes or two States) do not use the
    transition's name as their label, but rather some transition-
    specific attributes.
    """
    edge = generic_factory(seb)
    if edge.labels:  # pragma: no branch
        triggers = seb.melodyloader.follow_links(
            seb.melodyobjs[0], seb.melodyobjs[0].get("triggers", "")
        )
        label = ", ".join(
            i.get("name", "(unnamed trigger)")
            for i in triggers
            if i is not None
        )

        if guard := _guard_condition(seb, "guard"):
            label = f"{label} [{guard}]"

        effects = seb.melodyloader.follow_links(
            seb.melodyobjs[0], seb.melodyobjs[0].get("effect", "")
        )
        if effects:
            effects_str = ", ".join(
                i.get("name", "") for i in effects if i is not None
            )
            label = f"{label} / {effects_str}"

        edge.labels[0].label = label
    return edge


def sequence_link_factory(seb: C.SemanticElementBuilder) -> diagram.Edge:
    """Create a SequenceLink.

    Sequence links (in Operational Process Diagrams) use the guard
    condition as label, if it is set.  Otherwise the label stays empty.
    """
    edge = generic_factory(seb)
    guard = _guard_condition(seb, "condition")
    if guard and edge.labels:
        edge.labels[0].label = guard
    return edge


def constraint_factory(seb: C.SemanticElementBuilder) -> diagram.Edge:
    """Create the edge for a Constraint.

    As the Box already contains the label, it is not needed on the Edge.

    See Also
    --------
    capellambse.aird._box_factories.constraint_factory :
        The accompanying box factory.
    """
    edge = generic_factory(seb)
    edge.labels = []
    return edge


def fcil_factory(seb: C.SemanticElementBuilder) -> diagram.Edge:
    """Create a FunctionalChainInvolvementLinks."""
    seb.melodyobjs[0] = seb.melodyloader.follow_link(
        seb.melodyobjs[0], seb.melodyobjs[0].get("involved")
    )
    xtype = helpers.xtype_of(seb.melodyobjs[0])
    assert xtype is not None
    seb.styleclass = xtype.split(":")[-1]
    edge = generic_factory(seb)
    edge.labels = edge.labels[:1]
    assert edge.styleclass is not None and edge.target is not None
    if edge.target.styleclass == "OperationalActivity":
        edge.styleclass = "OperationalExchange"
    return edge


def eie_factory(seb: C.SemanticElementBuilder) -> diagram.Edge:
    """Create an exchange item element link."""
    edge = generic_factory(seb)
    edge.labels = edge.labels[:1]
    return edge


def _guard_condition(seb: C.SemanticElementBuilder, attr: str) -> str:
    """Extract the guard condition's text from the XML."""
    try:
        guard = seb.melodyloader.follow_links(
            seb.melodyobjs[0], seb.melodyobjs[0].get(attr, "")
        )[0]
    except IndexError:
        return ""
    else:
        return C.get_spec_text(
            dataclasses.replace(seb, melodyobjs=[guard, *seb.melodyobjs[1:]])
        )


def req_relation_factory(seb: C.SemanticElementBuilder) -> diagram.Edge:
    """Create a Capella Incoming or Outgoing Relation."""
    label = seb.melodyobjs[0].attrib.get("name", "")
    if not label:
        try:
            reltype_id = seb.melodyobjs[0].attrib["relationType"]
            reltype = seb.melodyloader[reltype_id]
            label = reltype.attrib["ReqIFLongName"]
        except KeyError:
            C.LOGGER.warning(
                "Requirement-Relation %r has no RelationType",
                seb.data_element.attrib[C.ATT_XMID],
            )
        finally:
            seb.melodyobjs[0].attrib["name"] = label

    return generic_factory(seb)


def include_extend_factory(seb: C.SemanticElementBuilder) -> diagram.Edge:
    """Create an AbstractCapabilityIncludes or -Extends edge."""
    if seb.melodyobjs[0].get("name") is None:
        seb.melodyobjs[0].attrib["name"] = seb.diag_element.get("name", "")
    return generic_factory(seb)


def association_factory(seb: C.SemanticElementBuilder) -> diagram.Edge:
    """Create an Association."""
    edge = generic_factory(seb)
    for member in seb.melodyobjs[0].iterchildren("ownedMembers"):
        kind = member.get("aggregationKind", "ASSOCIATION").capitalize()
        if kind != "Association":
            edge.styleclass = kind
    return edge
