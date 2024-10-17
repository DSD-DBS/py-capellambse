# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Classes that represent different aspects of a diagram."""

from __future__ import annotations

__all__ = [
    "Diagram",
    "DiagramElement",
    "Box",
    "Circle",
    "Edge",
    "RoutingStyle",
    "SNAPPING",
    "StyleOverrides",
]

import collections.abc as cabc
import contextlib
import enum
import logging
import math
import os
import typing as t

from capellambse import diagram, helpers

LOGGER = logging.getLogger(__name__)

SNAPPING = "AIRD_NOSNAP" not in os.environ

DiagramElement = t.Union["Box", "Edge", "Circle"]
StyleOverrides = t.MutableMapping[
    str,
    str | diagram.RGB | t.MutableSequence[str | diagram.RGB],
]


class RoutingStyle(enum.Enum):
    OBLIQUE = enum.auto()
    MANHATTAN = enum.auto()
    TREE = enum.auto()


class Box:
    """A Box.

    Some may call it rectangle.
    """

    # The number of pixels that a port hangs over its parent's border
    PORT_OVERHANG = 2
    CHILD_MARGIN = 2

    JSON_TYPE = "box"

    pos = diagram.Vec2Property()
    minsize = diagram.Vec2Property()
    maxsize = diagram.Vec2Property()

    context: set[str]

    def __init__(
        self,
        pos: diagram.Vec2ish,
        size: diagram.Vec2ish,
        *,
        label: str = "",
        floating_labels: cabc.MutableSequence[Box] | None = None,
        description: str | None = None,
        uuid: str | None = None,
        parent: Box | None = None,
        collapsed: bool = False,
        minsize: diagram.Vec2ish = diagram.Vector2D(0, 0),
        maxsize: diagram.Vec2ish = diagram.Vector2D(math.inf, math.inf),
        context: cabc.Iterable[str] | None = None,
        port: bool = False,
        features: cabc.MutableSequence[str] | None = None,
        styleclass: str | None = None,
        styleoverrides: StyleOverrides | None = None,
        hidelabel: bool = False,
        hidden: bool = False,
    ) -> None:
        """Create a new box.

        Parameters
        ----------
        pos
            A Vector2D describing the spatial position.
        size
            A Vector2D describing the box' size. If one or both of its
            components are 0, it/they will be calculated based on the
            Box' label text and contained children.
        label
            This box' label text.
        floating_labels
            Additional box labels.
        description
            Optional label text used only by Representation Links.
        uuid
            UUID of the semantic element this box represents.
        parent
            This box' parent box.
        collapsed
            Collapse this box and hide all its children. Note that
            setting this flag does not change the box' size.
        minsize
            When dynamically calculating Box size, the minimum size it
            should have. Default: zero.
        maxsize
            When dynamically calculating Box size, the maximum size it
            can have. Default: infinite.
        context
            A list of UUIDs of objects in this box' context. This
            includes children and associated edges.
        port
            Flag this box as a port. Affects how context is added.
        features
            Certain classes of Box (like ``Class``) have features, which
            is a list of strings that will be displayed inside the Box,
            separated from the label by a horizontal line.
        styleclass
            The CSS style class to use.
        styleoverrides
            A dict of CSS properties to override.
        hidelabel
            Set to True to skip drawing this box' label.
        hidden
            Set to True to skip drawing this entire box.
        """
        self.uuid = uuid
        self.pos = pos
        self.size = diagram.Vector2D(*size)
        self.minsize = minsize
        self.maxsize = maxsize
        self.label = label
        assert isinstance(self.label, str)
        self.floating_labels: cabc.MutableSequence[Box] = floating_labels or []
        self.description: str | None = description
        self.collapsed: bool = collapsed
        self.features: cabc.MutableSequence[str] | None = features

        self.styleclass: str | None = styleclass
        self.styleoverrides: StyleOverrides = styleoverrides or {}
        self.hidelabel: bool = hidelabel
        self.hidden = hidden

        self.children: cabc.MutableSequence[DiagramElement] = []
        self.context: set[str] = set(context) if context else set()
        self.port: bool = port

        self._parent: Box | None = None
        self.parent = parent

    def create_portlabel(
        self, labeltext: str, margin: float | int = 2
    ) -> None:
        """Add a label to a port box.

        The port that this is called for must be snapped to its parent's
        left or right side.

        Parameters
        ----------
        labeltext
            The label text.
        margin
            Space between the label text and the port Box.
        """
        if self.parent is None:
            raise ValueError("Ports must have a parent")
        if (
            self.pos.x > self.parent.pos.x
            and self.pos.x + self.size.x
            < self.parent.pos.x + self.parent.size.x
        ):
            raise ValueError(
                "Ports must be attached to their parents' side to get labels"
            )

        leftside = self.pos.x < self.parent.pos.x

        text_extent = diagram.Vector2D(*helpers.get_text_extent(labeltext)) + (
            2 * margin,
            2 * margin,
        )
        text_pos = self.pos
        text_pos += (
            self.size.x + margin if leftside else -text_extent.x - margin,
            (self.size.y - text_extent.y) // 2,
        )
        self.floating_labels = [
            type(self)(text_pos, text_extent, label=labeltext)
        ]

    def snap_to_parent(self) -> None:
        """Snap this Box into the constraints set by its parent.

        If this Box is a port, ensure it lines up with the parent's
        border, keeping an overhang of 2px.

        Otherwise, ensures that this Box will not overflow out of the
        parent's border, keeping a padding of 2px.
        """
        if not SNAPPING or self.parent is None:
            return

        if not isinstance(self.parent, Box):
            raise TypeError(
                "Can only snap to parent Boxes,"
                f" not {type(self.parent).__name__}"
            )

        if self.port:
            padding = (self.parent.PORT_OVERHANG, self.parent.PORT_OVERHANG)
            midbox_tl = self.parent.pos + self.size / 2 - padding
            midbox_br = (
                self.parent.pos + self.parent.size - self.size / 2 + padding
            )
            midbox = diagram.Box(midbox_tl, midbox_br - midbox_tl)
            mid = self.pos + self.size / 2
            newmid = midbox.vector_snap(mid)
            self.pos += newmid - mid
        else:
            padding = (self.parent.CHILD_MARGIN, self.parent.CHILD_MARGIN)
            minpos = self.parent.pos + padding
            self.pos = diagram.Vector2D(
                max(self.pos.x, minpos.x), max(self.pos.y, minpos.y)
            )
            maxsize = self.parent.pos + self.parent.size - self.pos - padding
            newsize = diagram.Vector2D(
                min(self.size.x, maxsize.x), min(self.size.y, maxsize.y)
            )
            if newsize <= (0, 0):
                newsize = diagram.Vector2D(0, 0)
                LOGGER.warning(
                    "Box %r (%s) has zero size after snapping",
                    self.floating_labels,
                    self.uuid,
                )
            self.size = diagram.Vector2D(
                newsize.x if self._size.x > 0 else 0,
                newsize.y if self._size.y > 0 else 0,
            )

    def add_context(self, uuid: str) -> None:
        """Add a UUID as context for this box.

        The context will bubble to the immediate parent if this box is a
        port.
        """
        self.context.add(uuid)
        if self.port and self.parent is not None:
            self.parent.add_context(uuid)

    def vector_snap(
        self,
        point: diagram.Vec2ish,
        *,
        source: diagram.Vec2ish | None = None,
        style: RoutingStyle = RoutingStyle.OBLIQUE,
    ) -> diagram.Vector2D:
        """Snap the ``point`` into this Box, coming from ``source``."""
        if not isinstance(point, diagram.Vector2D):
            point = diagram.Vector2D(*point)

        if not SNAPPING:
            return point

        if source is None:
            source = point
        elif not isinstance(source, diagram.Vector2D):
            source = diagram.Vector2D(*source)

        if style is RoutingStyle.OBLIQUE:
            if point == source:
                return self.__vector_snap_closest(point)
            return self.__vector_snap_oblique(point, source)
        if style is RoutingStyle.MANHATTAN:
            return self.__vector_snap_manhattan(point, point - source)
        if style is RoutingStyle.TREE:
            return self.__vector_snap_tree(point, point - source)
        raise ValueError(f"Unsupported routing style: {style}")

    def __vector_snap_closest(
        self, source: diagram.Vector2D
    ) -> diagram.Vector2D:
        if source == self.center:
            return self.pos + self.size @ (0, 0.5)

        angle = self.size.angleto(source - self.center)
        alpha = 2 * self.size.angleto((1, 0))
        assert alpha >= 0
        alpha_prime = math.pi - alpha

        if 0 < angle < alpha:
            return diagram.line_intersect(
                (self.center, source),
                (self.pos + self.size @ (1, 0), self.pos + self.size),
            )
        if -alpha_prime < angle <= 0:
            return diagram.line_intersect(
                (self.center, source),
                (self.pos + self.size @ (0, 1), self.pos + self.size),
            )
        if alpha < angle < math.pi:
            return diagram.line_intersect(
                (self.center, source),
                (self.pos, self.pos + self.size @ (1, 0)),
            )
        return diagram.line_intersect(
            (self.center, source),
            (self.pos, self.pos + self.size @ (0, 1)),
        )

    def __vector_snap_oblique(
        self, point: diagram.Vector2D, source: diagram.Vector2D
    ) -> diagram.Vector2D:
        assert point != source
        if not (
            self.pos.x <= point.x <= self.pos.x + self.size.x
            and self.pos.y <= point.y <= self.pos.y + self.size.y
        ):
            point = self.center
        direction = point - source
        edge = (source, point)
        assert direction.x or direction.y, f"{edge} doesn't have a direction"

        edges: set[str] = set()
        if direction.x > 0:
            edges.add("left")
        elif direction.x < 0:
            edges.add("right")

        if direction.y > 0:
            edges.add("top")
        elif direction.y < 0:
            edges.add("bottom")
        assert len(edges) in (1, 2), f"{edge} doesn't have a direction"

        intersections: list[diagram.Vector2D] = []
        if "top" in edges:
            border = (self.pos, self.pos + self.size @ (1, 0))
            with contextlib.suppress(ValueError):
                intersection = diagram.line_intersect(border, edge)
                if border[0].x <= intersection.x <= border[1].x:
                    intersections.append(intersection)
        if "left" in edges:
            border = (self.pos, self.pos + self.size @ (0, 1))
            with contextlib.suppress(ValueError):
                intersection = diagram.line_intersect(border, edge)
                if border[0].y <= intersection.y <= border[1].y:
                    intersections.append(intersection)
        if "right" in edges:
            border = (self.pos + self.size @ (1, 0), self.pos + self.size)
            with contextlib.suppress(ValueError):
                intersection = diagram.line_intersect(border, edge)
                if border[0].y <= intersection.y <= border[1].y:
                    intersections.append(intersection)
        if "bottom" in edges:
            border = (self.pos + self.size @ (0, 1), self.pos + self.size)
            with contextlib.suppress(ValueError):
                intersection = diagram.line_intersect(border, edge)
                if border[0].x <= intersection.x <= border[1].x:
                    intersections.append(intersection)

        assert len(intersections) > 0, f"{edge} doesn't intersect {edges}"
        return intersections[0]

    def __vector_snap_manhattan(
        self, point: diagram.Vector2D, direction: diagram.Vector2D
    ) -> diagram.Vector2D:
        axis = direction.closestaxis()

        if axis.x:
            if point.y < self.pos.y:
                return self.pos + self.size @ (0.5, 0)
            if point.y > self.pos.y + self.size.y:
                return self.pos + self.size @ (0.5, 1)
            if self.port:
                return self.pos + self.size @ (axis.x < 0, 0.5)
            return diagram.Vector2D(
                self.pos.x + self.size.x * (axis.x < 0),
                point.y,
            )

        if axis.y:
            if point.x < self.pos.x:
                return self.pos + self.size @ (0, 0.5)
            if point.x > self.pos.x + self.size.x:
                return self.pos + self.size @ (1, 0.5)
            if self.port:
                return self.pos + self.size @ (0.5, axis.y < 0)
            return diagram.Vector2D(
                point.x,
                self.pos.y + self.size.y * (axis.y < 0),
            )

        raise AssertionError(f"closestaxis({axis!r}) returned (0,0)")

    def __vector_snap_tree(
        self, point: diagram.Vector2D, direction: diagram.Vector2D
    ) -> diagram.Vector2D:
        if direction == diagram.Vector2D(0.0, 0.0):
            if self.center.x < point.x:
                return diagram.Vector2D(point.x - 1, point.y)
            return diagram.Vector2D(point.x + 1, point.y)

        if self.port:
            if (
                direction.y < 0.0
                or math.isclose(direction.y, 0.0)
                and point.y != self.pos.y
            ):
                return self.pos + self.size @ (0.5, 1.0)
            return self.pos + self.size @ (0.5, 0.0)

        if (
            direction.y < 0.0
            or math.isclose(direction.y, 0.0)
            and point.y != self.pos.y
        ):
            return diagram.Vector2D(point.x, self.pos.y + self.size.y)

        return diagram.Vector2D(point.x, self.pos.y)

    def move(self, offset: diagram.Vector2D, *, children: bool = True) -> None:
        """Move the box by the specified offset.

        Parameters
        ----------
        offset
            The offset to move the box by.
        children
            Recursively move children as well. If False, the positions
            of children need to be adjusted separately.
        """
        self.pos += offset
        for label in self.floating_labels:
            label.move(offset, children=children)

        if children:
            for child in self.children:
                child.move(offset, children=True)

    @property
    def size(self) -> diagram.Vector2D:
        """Return the size of this Box."""
        width, height = self._size
        needwidth = width <= 0
        needheight = height <= 0
        if not needwidth and not needheight:
            return self._size

        if self.label:
            pad_w, pad_h = self.padding * 2  # Pad on all four sides

            # Fill in missing box size fields based on label text extent
            label_extent = helpers.get_text_extent(
                (
                    self.label + "\n" + "\n".join(self.features)
                    if self.features
                    else self.label
                ),
                self.maxsize.x if needwidth else width - pad_w,
            )

            if needwidth:
                width = math.ceil(label_extent[0]) + pad_w
            if needheight:
                height = min(
                    self.maxsize.y, math.ceil(label_extent[1]) + pad_h
                )
        for child in self.children:
            if not child.hidden:
                cbound = child.bounds
                if needwidth:
                    width = max(
                        width,
                        cbound.pos.x
                        + cbound.size.x
                        + (-self.PORT_OVERHANG if child.port else 5)
                        - self.pos.x,
                    )
                    width = min(self.maxsize.x, width)
                if needheight:
                    height = max(
                        height,
                        cbound.pos.y
                        + cbound.size.y
                        + (-self.PORT_OVERHANG if child.port else 5)
                        - self.pos.y,
                    )
                    height = min(self.maxsize.y, height)

        # Features divider line
        if self.features or self.styleclass in ("Class", "Enumeration"):
            height += 24

        if needwidth:
            width = max(self.minsize.x, width)
        if needheight:
            height = max(self.minsize.y, height)
        return diagram.Vector2D(width, height)

    @size.setter
    def size(self, new_size: diagram.Vec2ish) -> None:
        if isinstance(new_size, diagram.Vector2D):
            self._size = new_size
        else:
            self._size = diagram.Vector2D(*new_size)

    @property
    def bounds(self) -> Box:
        """Calculate the bounding box of this Box.

        Notes
        -----
        Labels with a `text_transform` in its `styleoverrides` are
        ignored during bounds calculation.
        """
        minx, miny = self.pos
        maxx, maxy = self.pos + self.size
        if self.styleoverrides.get("text_transform") is not None:
            return Box((minx, miny), (maxx - minx, maxy - miny))

        for label in self.floating_labels:
            if isinstance(label, Box) and not self.hidelabel:
                minx = min(minx, label.pos.x)
                miny = min(miny, label.pos.y)
                maxx = max(maxx, label.pos.x + label.size.x)
                maxy = max(maxy, label.pos.y + label.size.y)

        return Box((minx, miny), (maxx - minx, maxy - miny))

    @property
    def padding(self) -> diagram.Vector2D:
        """Return the horizontal and vertical padding of label text."""
        if self.styleclass and self.styleclass.endswith("Annotation"):
            return diagram.Vector2D(0, 0)
        return diagram.Vector2D(10, 5)

    @property
    def hidden(self) -> bool:
        """Return whether to skip this Box during rendering."""
        hidden = self._hidden
        if self.parent is not None:
            hidden |= self.parent.hidden or self.parent.collapsed
        return hidden

    @hidden.setter
    def hidden(self, hide: bool) -> None:
        self._hidden = hide

    @property
    def center(self) -> diagram.Vector2D:
        """Return the center point of this Box."""
        return self.pos + self.size / 2

    @property
    def parent(self) -> Box | None:
        """Return the parent element of this Box."""
        return self._parent

    @parent.setter
    def parent(self, parent: Box | None) -> None:
        self._parent, prev_parent = parent, self._parent
        if prev_parent is not None and self in prev_parent.children:
            prev_parent.children.remove(self)
        if self._parent is not None:
            self._parent.children.append(self)

        self.snap_to_parent()

    def __str__(self) -> str:
        labels = self.label or "\n".join(b.label for b in self.floating_labels)
        if labels:
            labels = " " + repr(labels)
        return (
            f"{self.styleclass or 'Box'}{labels}"
            f" at {self.pos}, size {self.size}"
            + (f" with {len(self.features)} features" if self.features else "")
        )

    def __repr__(self) -> str:
        context = ", ".join(repr(c) for c in sorted(self.context))
        return "".join(
            [
                f"{type(self).__name__}({self.pos!r}, {self.size!r}",
                f", label={self.label!r}",
                (
                    f", labels={self.floating_labels!r}"
                    if self.floating_labels
                    else ""
                ),
                f", uuid={self.uuid!r}" if self.uuid is not None else "",
                (
                    f", parent=<UUID={self.parent.uuid}>"
                    if self.parent is not None
                    else ""
                ),
                f", context={{{context}}}" if context else "",
                f", features={self.features!r}" if self.features else "",
                f", styleclass={self.styleclass!r}" if self.styleclass else "",
                ", hidelabel=True" if self.hidelabel else "",
                ", hidden=True" if self.hidden else "",
                ")",
            ]
        )


class Edge(diagram.Vec2List):
    """An edge in the diagram.

    An Edge consists of a series of points that are traversed in order.
    Each point is given as Vector2D containing absolute coordinates. At
    least two points are required.
    """

    JSON_TYPE = "edge"

    collapsed = False
    hidelabel = False
    port = False

    context: set[str]

    def __init__(
        self,
        points: cabc.Iterable[diagram.Vec2ish],
        *,
        labels: cabc.MutableSequence[Box] | None = None,
        uuid: str | None = None,
        source: DiagramElement | None = None,
        target: DiagramElement | None = None,
        styleclass: str | None = None,
        styleoverrides: StyleOverrides | None = None,
        hidden: bool = False,
        context: cabc.Iterable[str] | None = None,
    ):
        r"""Construct an Edge.

        Parameters
        ----------
        source
            The source diagram element of this Edge.
        target
            The target diagram element of this Edge.
        labels
            Labels for this Edge. Each label is a ``Box`` with ``pos``,
            ``size`` and a simple ``str`` label. Other configurations of
            Boxes are not supported. The ``hidden`` flag is honored
            during rendering calculations.
        points
            A list of ``Vector2D``\ s with the (absolute) points this
            edge follows.
        uuid
            UUID of the semantic element this Edge represents.
        styleclass
            The CSS style class to use.
        styleoverrides
            A dict of CSS properties to override.
        hidden
            True to skip drawing this edge entirely.
        context
            A list of UUIDs of objects in this edge's context.
        """
        super().__init__(points)
        if len(self) < 2:
            raise ValueError(
                "At least two points are required"
                + (f" for edge with uuid {uuid}" if uuid else "")
            )

        self.source = source
        self.target = target

        self.uuid = uuid
        self.styleclass = styleclass
        self.styleoverrides = styleoverrides or {}

        self.labels = labels or []
        self.hidden = hidden
        self.context = set(context) if context else set()

    def add_context(self, uuid: str) -> None:
        """Add a UUID as context for this edge."""
        self.context.add(uuid)

    def vector_snap(
        self,
        vector: diagram.Vec2ish,
        *,
        source: diagram.Vec2ish,
        style: RoutingStyle = RoutingStyle.OBLIQUE,
    ) -> diagram.Vector2D:
        """Snap the ``vector`` onto this Edge."""
        del source, style

        if not isinstance(vector, diagram.Vector2D):
            vector = diagram.Vector2D(*vector)

        if not SNAPPING:
            return vector

        epoint: diagram.Vector2D  # Point on this Edge
        edist = math.inf  # Squared distance to that point

        for i in range(len(self.points) - 1):
            segment = self.points[i + 1] - self.points[i]
            seg_norm = segment.normalized
            dist = (vector - self.points[i]) * seg_norm

            # Clamp into the segment
            seglen = segment.length
            if dist > seglen:
                dist = seglen
            elif dist < 0:
                dist = 0

            new_epoint = self.points[i] + seg_norm * dist
            new_edist = (new_epoint - vector).sqlength

            if new_edist < edist:
                epoint = new_epoint
                edist = new_edist

        return epoint

    def move(self, offset: diagram.Vector2D, *, children: bool = True) -> None:
        """Move all points of this edge by the specified offset."""
        del children
        for i, _ in enumerate(self):
            self[i] += offset

    @property
    def bounds(self) -> Box:
        """Calculate the bounding Box of this Edge."""
        labels = [i for i in self.labels if not i.hidden]
        if labels:
            minx = min(i.pos.x for i in labels)
            miny = min(i.pos.y for i in labels)
            maxx = max(i.pos.x + i.size.x for i in labels)
            maxy = max(i.pos.y + i.size.y for i in labels)
        else:
            minx = miny = math.inf
            maxx = maxy = -math.inf

        for point in self.points:
            minx = min(minx, point.x)
            miny = min(miny, point.y)
            maxx = max(maxx, point.x)
            maxy = max(maxy, point.y)

        topleft = diagram.Vector2D(minx, miny)
        bottomright = diagram.Vector2D(maxx, maxy)
        return Box(topleft, bottomright - topleft)

    @property
    def hidden(self) -> bool:
        """Return whether to skip this Edge during rendering."""
        return (
            self._hidden
            or (self.source is not None and self.source.hidden)
            or (self.target is not None and self.target.hidden)
        )

    @hidden.setter
    def hidden(self, hide: bool) -> None:
        self._hidden = hide

    @property
    def points(self) -> diagram.Vec2List:
        """Return an iterable over this edge's points."""
        return self

    @points.setter
    def points(self, newpoints: cabc.Iterable[diagram.Vec2ish]) -> None:
        self[:] = newpoints

    @property
    def length(self) -> float:
        """Return length of this edge."""
        return sum((self[i - 1] - self[i]).length for i in range(1, len(self)))

    @property
    def center(self) -> diagram.Vector2D:
        """Calculate the point in the middle of this edge."""
        half_length = self.length / 2
        distance = 0.0
        point = self[0]
        for i in range(1, len(self)):
            segment = self[i] - self[i - 1]
            if distance + segment.length > half_length:
                point += segment.normalized * (half_length - distance)
                break
            distance += segment.length
            point = self[i]
        return point

    def __str__(self) -> str:
        numpoints = len(self.points)
        if self.labels:
            label = self.labels[0].floating_labels or ""
        else:
            label = ""
        return (
            f"{self.styleclass or 'Edge'}"
            f"{f' {label!r}' if label else ''} between"
            f" {self[0]} and {self[-1]}"
            + (
                f" via {', '.join(str(p) for p in self[1:-1])}"
                if numpoints > 2
                else ""
            )
        )

    def __repr__(self) -> str:
        return "".join(
            [
                f"{self.__class__.__name__}({list(self)!r}",
                f", labels={self.labels!r}" if self.labels else "",
                f", uuid={self.uuid!r}" if self.uuid else "",
                f", styleclass={self.styleclass!r}" if self.styleclass else "",
                ", hidden=True" if self.hidden else "",
                ")",
            ]
        )


class Circle:
    """Represents a circle."""

    JSON_TYPE = "circle"

    collapsed = False
    hidelabel = True
    label = None
    port = False

    center = diagram.Vec2Property()

    context: set[str]

    def __init__(
        self,
        center: diagram.Vec2ish,
        radius: float | int,
        *,
        uuid: str | None = None,
        styleclass: str | None = None,
        styleoverrides: StyleOverrides | None = None,
        hidden: bool = False,
        context: cabc.Iterable[str] | None = None,
    ):
        """Construct a Circle.

        Parameters
        ----------
        center
            The Circle's center point as Vector2D or 2-tuple.
        radius
            The Circle radius in pixels.
        uuid
            The Circle's unique identifier.
        styleclass
            The Circle's CSS class.
        styleoverrides
            Dict of CSS key/value pairs that override the class
            defaults.
        hidden
            True to skip drawing this Circle.
        context
            A list of UUIDs of objects in this circle's context.
        """
        self.uuid = uuid
        self.center = center
        self.radius = radius

        self.styleclass = styleclass
        self.styleoverrides = styleoverrides or {}
        self.hidden = hidden
        self.context = set(context) if context else set()

    def add_context(self, uuid: str) -> None:
        """Add a UUID as context for this circle."""
        self.context.add(uuid)

    @property
    def bounds(self) -> Box:
        """Calculate the bounding box of this Circle."""
        return Box(
            self.center - (self.radius, self.radius),
            (self.radius * 2, self.radius * 2),
        )

    def move(self, offset: diagram.Vec2ish, *, children: bool = True) -> None:
        """Move this Circle on the 2-dimensional plane."""
        del children
        self.center += offset

    def vector_snap(
        self,
        vector: diagram.Vec2ish,
        *,
        source: diagram.Vec2ish,
        style: RoutingStyle = RoutingStyle.OBLIQUE,
    ) -> diagram.Vector2D:
        """Snap the vector onto this Circle, preferably in direction."""
        del style
        # TODO implement different routing styles than OBLIQUE

        if not isinstance(vector, diagram.Vector2D):
            vector = diagram.Vector2D(*vector)
        if not isinstance(source, diagram.Vector2D):
            source = diagram.Vector2D(*source)
        direction = source - vector
        if vector == self.center:
            vector = direction
        assert vector != (0, 0)

        return self.center + vector.normalized * self.radius

    def __str__(self) -> str:
        return (
            f"{f'{self.styleclass}-' if self.styleclass else ''}Circle"
            f"at {self.center} with radius {self.radius}px"
        )

    def __repr__(self) -> str:
        return "".join(
            (
                f"{self.__class__.__name__}({self.center!r}, {self.radius!r}",
                f", uuid={self.uuid!r}" if self.uuid else "",
                f", styleclass={self.styleclass!r}" if self.styleclass else "",
                (
                    f", styleoverrides={self.styleoverrides!r}"
                    if self.styleoverrides
                    else ""
                ),
                ", hidden=True" if self.hidden else "",
                ")",
            )
        )


class Diagram:
    """A complete diagram, including all elements required by it."""

    def __init__(
        self,
        name: str = "Untitled Diagram",
        viewport: Box | None = None,
        elements: cabc.Sequence[DiagramElement] | None = None,
        *,
        uuid: str | None = None,
        styleclass: str | None = None,
        params: dict[str, t.Any] | None = None,
    ):
        """Construct a new diagram.

        Parameters
        ----------
        name
            The diagram's name.
        viewport
            A Box describing this diagram's viewport.
        elements
            A :class:`list` containing the diagram's initial elements.
        uuid
            The unique ID of this diagram.
        styleclass
            The diagram class.
        params
            Additional parameters.
        """
        self.name = name
        self.uuid = uuid
        self.styleclass = styleclass
        self.params = params or {}

        self.viewport = None
        self.__elements: list[DiagramElement] = []

        if elements is not None:
            for element in elements:
                self.add_element(element)
        if viewport is not None:
            self.viewport = Box(
                viewport.pos, viewport.size, styleclass="Viewport"
            )

    def add_element(
        self,
        element: DiagramElement,
        extend_viewport: bool = True,
        *,
        force: bool = False,
    ) -> None:
        """Add an element to this diagram.

        Parameters
        ----------
        element
            The element to add.
        extend_viewport
            True to automatically extend the diagram viewport so that
            the added element is fully visible.
        force
            Normally an exception will be raised if another element with
            the same UUID as the new one already exists in the diagram.
            If this is set to True, the old element will be overwritten
            instead.
        """
        if element.uuid is not None and element.uuid in self:
            if force:
                old_hidden = self[element.uuid].hidden
                new_hidden = element.hidden
                if new_hidden:
                    LOGGER.warning("Skipping hidden duplicate %s", element)
                    return
                if not old_hidden:
                    LOGGER.warning("Skipping duplicate %s", element)
                    return
                LOGGER.warning(
                    "Overwriting hidden duplicate %r with %r",
                    str(self[element.uuid]),
                    str(element),
                )
                self.__elements.remove(self[element.uuid])
            else:
                raise ValueError(f"Duplicate element UUID {element.uuid!r}")

        if extend_viewport:
            self.__extend_viewport(element.bounds)
        self.__elements.append(element)

    def calculate_viewport(self) -> None:
        """Recalculate the viewport so that all elements are contained."""
        minx = miny = math.inf
        maxx = maxy = -math.inf

        for elm in self:
            if elm.hidden:
                continue

            bounds = elm.bounds
            minx = min(minx, bounds.pos.x)
            miny = min(miny, bounds.pos.y)
            maxx = max(maxx, bounds.pos.x + bounds.size.x)
            maxy = max(maxy, bounds.pos.y + bounds.size.y)

        top_left = diagram.Vector2D(minx, miny)
        bottom_right = diagram.Vector2D(maxx, maxy)
        self.viewport = Box(
            top_left, bottom_right - top_left, styleclass="Viewport"
        )

    def normalize_viewport(
        self,
        offset: float | int | diagram.Vec2ish = 0,
    ) -> None:
        """Normalize the viewport.

        This function moves all elements contained within this diagram
        so that the top left corner of the viewport is at (0, 0) (or the
        specified offset, if given).

        If a single value is given as offset, it is applied to both X
        and Y coordinates.
        """
        if isinstance(offset, diagram.Vector2D):
            offsetvec = offset
        elif isinstance(offset, cabc.Sequence):
            offsetvec = diagram.Vector2D(*offset)
        else:
            offsetvec = diagram.Vector2D(offset, offset)
        del offset

        if self.viewport is None:
            self.calculate_viewport()
        assert self.viewport is not None

        offsetvec -= self.viewport.pos

        for element in [self.viewport, *self.__elements]:
            element.move(offsetvec, children=False)

    def __extend_viewport(self, element: DiagramElement) -> None:
        """Extend the viewport so the given element fits in.

        If the element's bounding box already lies completely within the
        current viewport, this function does nothing.
        """
        bounds = element.bounds

        if self.viewport is None:
            self.viewport = Box(bounds.pos, bounds.size, styleclass="Viewport")
        else:
            top_left = diagram.Vector2D(
                min(self.viewport.pos.x, bounds.pos.x),
                min(self.viewport.pos[1], bounds.pos[1]),
            )
            bottom_right = diagram.Vector2D(
                max(
                    self.viewport.pos.x + self.viewport.size.x,
                    bounds.pos.x + bounds.size.x,
                ),
                max(
                    self.viewport.pos.y + self.viewport.size.y,
                    bounds.pos.y + bounds.size.y,
                ),
            )
            pos = top_left
            size = bottom_right - top_left
            self.viewport = Box(pos, size, styleclass="Viewport")

    def __len__(self) -> int:
        return len(self.__elements)

    def __getitem__(self, key: int | str) -> DiagramElement:
        if isinstance(key, int):  # sequence protocol
            return self.__elements[key]

        if isinstance(key, str):  # lookup by uuid
            for elm in self.__elements:
                if elm.uuid == key:
                    return elm
            raise KeyError(f"No element with uuid {key!r} in this diagram")

        raise TypeError(f"Cannot look up elements by {type(key).__name__!s}")

    def __iter__(self) -> cabc.Iterator[DiagramElement]:
        return iter(self.__elements)

    def __contains__(self, obj: str | DiagramElement) -> bool:
        if isinstance(obj, str):
            try:
                self[obj]
            except KeyError:
                return False
            else:
                return True
        else:
            return obj in self.__elements

    def __str__(self) -> str:
        return "".join(
            [
                self.styleclass or self.__class__.__name__,
                f" {self.name!r}",
                f" ({self.uuid!r})" if self.uuid else "",
                f" [{self.viewport!s}]\n",
                (
                    "\n".join(f"\t- {elm}" for elm in self)
                    if self
                    else "\t(empty)"
                ),
            ]
        )

    def __repr__(self) -> str:
        return "".join(
            [
                f"{self.__class__.__name__}(",
                f"{self.name!r}, {self.viewport!r}, {self.__elements!r}",
                f", uuid={self.uuid!r}" if self.uuid else "",
                f", styleclass={self.styleclass!r}" if self.styleclass else "",
                ")",
            ]
        )

    def __iadd__(self, element: DiagramElement) -> Diagram:
        self.add_element(element)
        return self
