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
"""Classes that represent different aspects of a diagram."""
from __future__ import annotations

__all__ = ["Diagram", "DiagramElement", "Box", "Circle", "Edge"]

import collections.abc as cabc
import logging
import math
import os
import typing as t

from capellambse import aird, helpers

LOGGER = logging.getLogger(__name__)

SNAPPING = "AIRD_NOSNAP" not in os.environ

DiagramElement = t.Union["Box", "Edge", "Circle"]


class Box:
    """A Box.  Some may call it rectangle."""

    # The number of pixels that a port hangs over its parent's border
    PORT_OVERHANG = 2
    CHILD_MARGIN = 2

    JSON_TYPE = "box"

    pos = aird.Vec2Property()
    minsize = aird.Vec2Property()
    maxsize = aird.Vec2Property()

    def __init__(
        self,
        pos: aird.Vec2ish,
        size: aird.Vec2ish,
        *,
        label: Box | str | None = None,
        uuid: str | None = None,
        parent: Box | None = None,
        collapsed: bool = False,
        minsize: aird.Vec2ish = aird.Vector2D(0, 0),
        maxsize: aird.Vec2ish = aird.Vector2D(math.inf, math.inf),
        context: cabc.Iterable[str] | None = None,
        port: bool = False,
        features: cabc.Sequence[str] | None = None,
        styleclass: str | None = None,
        styleoverrides: cabc.Mapping[
            str, aird.RGB | str | cabc.Sequence[aird.RGB | str]
        ]
        | None = None,
        hidelabel: bool = False,
        hidden: bool = False,
    ) -> None:
        """Create a new box.

        Parameters
        ----------
        pos
            A Vector2D describing the spatial position.
        size
            A Vector2D describing the box' size.  If one or both of its
            components are 0, it/they will be calculated based on the
            Box' label text and contained children.
        label
            This box' label text.
        uuid
            UUID of the semantic element this box represents.
        parent
            This box' parent box.
        collapsed
            Collapse this box and hide all its children.  Note that
            setting this flag does not change the box' size.
        minsize
            When dynamically calculating Box size, the minimum size it
            should have.  Default: zero.
        maxsize
            When dynamically calculating Box size, the maximum size it
            can have.  Default: inifite.
        context
            A list of UUIDs of objects in this box' context.  This
            includes children and associated edges.
        port
            Flag this box as a port.  Affects how context is added.
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
        self.size = aird.Vector2D(*size)
        self.minsize = minsize
        self.maxsize = maxsize
        self.label: Box | str | None = label
        self.collapsed: bool = collapsed
        self.features: cabc.Sequence[str] | None = features

        self.styleclass: str | None = styleclass
        self.styleoverrides: cabc.Mapping[
            str, aird.RGB | str | cabc.Sequence[aird.RGB | str]
        ] | None = (styleoverrides or {})
        self.hidelabel: bool = hidelabel
        self.hidden = hidden

        self.parent: Box | None = parent
        self.children: cabc.MutableSequence[DiagramElement] = []
        self.context: set[str] = set(context) if context else set()
        self.port: bool = port

        if parent is not None:
            parent.children.append(self)
            self.snap_to_parent()

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

        text_extent = aird.Vector2D(*helpers.get_text_extent(labeltext)) + (
            2 * margin,
            2 * margin,
        )
        text_pos = self.pos
        text_pos += (
            self.size.x + margin if leftside else -text_extent.x - margin,
            (self.size.y - text_extent.y) // 2,
        )
        self.label = type(self)(text_pos, text_extent, label=labeltext)

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
                f"Can only snap to parent Boxes, not {type(self.parent).__name__}"
            )

        if self.port:
            padding = (self.parent.PORT_OVERHANG, self.parent.PORT_OVERHANG)
            # Distances of all corner combinations
            # (our/parent's top-left/bottom-right)
            d_tl_tl = self.pos - self.parent.pos
            d_br_tl = self.pos + self.size - self.parent.pos
            d_tl_br = self.pos - self.parent.pos - self.parent.size
            d_br_br = self.pos + self.size - self.parent.pos - self.parent.size

            # Find closest parent border (left vs. right and top vs. bottom)
            d_tl = aird.Vector2D(
                min(d_tl_tl.x, d_br_tl.x), min(d_tl_tl.y, d_br_tl.y)
            )
            d_br = aird.Vector2D(
                min(d_tl_br.x, d_br_br.x), min(d_tl_br.y, d_br_br.y)
            )
            border = aird.Vector2D(
                -1 if abs(d_tl.x) <= abs(d_br.x) else 1,
                -1 if abs(d_tl.y) <= abs(d_br.y) else 1,
            )

            # Find out if horizontal or vertical border is closer
            horiz = abs(d_tl.x if border.x < 0 else d_br.x) <= abs(
                d_tl.y if border.y < 0 else d_br.y
            )
            border = border @ (horiz, not horiz)

            self.pos = self.pos.boxsnap(
                self.parent.pos - padding,
                self.parent.pos + self.parent.size + padding - self.size,
                border,
            )
        else:
            padding = (self.parent.CHILD_MARGIN, self.parent.CHILD_MARGIN)
            minpos = self.parent.pos + padding
            self.pos = aird.Vector2D(
                max(self.pos.x, minpos.x), max(self.pos.y, minpos.y)
            )
            maxsize = self.parent.pos + self.parent.size - self.pos - padding
            newsize = aird.Vector2D(
                min(self.size.x, maxsize.x), min(self.size.y, maxsize.y)
            )
            if newsize <= (0, 0):
                newsize = aird.Vector2D(0, 0)
                LOGGER.warning(
                    "Box %r (%s) has zero size after snapping",
                    self.label,
                    self.uuid,
                )
            self.size = aird.Vector2D(
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
        self, vector: aird.Vec2ish, direction: aird.Vec2ish
    ) -> aird.Vector2D:
        """Snap the ``vector`` into this Box, preferably into ``direction``."""
        if not isinstance(vector, aird.Vector2D):
            vector = aird.Vector2D(*vector)

        if not SNAPPING:
            return vector
        return vector.boxsnap(self.pos, self.pos + self.size, direction)

    def move(self, offset: aird.Vector2D, *, children: bool = True) -> None:
        """Move the box by the specified offset.

        Parameters
        ----------
        children
            Recursively move children as well.  If False, the positions
            of children need to be adjusted separately.
        """
        self.pos += offset
        if isinstance(self.label, Box):
            self.label.move(offset, children=children)

        if children:
            for child in self.children:
                child.move(offset, children=True)

    @property
    def size(self) -> aird.Vector2D:
        """Return the size of this Box."""
        width, height = self._size
        needwidth = width <= 0
        needheight = height <= 0
        if not needwidth and not needheight:
            return self._size

        if isinstance(self.label, str):
            # pylint: disable=unpacking-non-sequence  # false-positive
            pad_w, pad_h = self.padding * 2  # Pad on all four sides

            # Fill in missing box size fields based on label text extent
            label_extent = helpers.get_text_extent(
                self.label + "\n" + "\n".join(self.features)
                if self.features
                else self.label,
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

        width = max(self.minsize.x, width)
        height = max(self.minsize.y, height)

        # Features divider line
        if (
            self.features
            or self.styleclass == "Class"
            or self.styleclass == "Enumeration"
        ):
            height += 24
        return aird.Vector2D(width, height)

    @size.setter
    def size(self, new_size: aird.Vec2ish) -> None:
        if isinstance(new_size, aird.Vector2D):
            self._size = new_size
        else:
            self._size = aird.Vector2D(*new_size)

    @property
    def bounds(self) -> Box:
        """Calculate the bounding box of this Box."""
        return self

    @property
    def padding(self) -> aird.Vector2D:
        """Return the horizontal and vertical padding of label text."""
        if self.styleclass and self.styleclass.endswith("Annotation"):
            return aird.Vector2D(0, 0)
        return aird.Vector2D(10, 5)

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

    def __contains__(self, item: aird.Vec2ish) -> bool:
        """Check if item is in bounding box vectors"""
        # Fix x and vary y
        if self.is_on_side(*self.pos, *item, *self.size):
            return True

        # Fix y and vary x
        if self.is_on_side(*self.pos[::-1], *item[::-1], *self.size[::-1]):
            return True

        return False

    @staticmethod
    def is_on_side(
        x: aird.vector2d.Vec2Element,
        y: aird.vector2d.Vec2Element,
        tx: aird.vector2d.Vec2Element,
        ty: aird.vector2d.Vec2Element,
        w: aird.vector2d.Vec2Element,
        h: aird.vector2d.Vec2Element,
    ) -> bool:
        """Check if given (tx, ty) is part of left or right side of bounding
        box that is constructed by x, y and w, h.

        Parameters
        ----------
        x
            x position of bounding box
        y
            y position of bounding box
        tx
            x position of arbitrary point
        ty
            y position of arbitrary point
        w
            width of bounding box
        h
            height of bounding box

        Returns
        -------
        is_on_side
            True if arbitrary point is part of left or right side of bounding box
        """
        if (tx == x or tx == x + w) and y <= ty <= y + h:
            return True
        return False

    def __str__(self) -> str:
        if self.label is None:
            label = ""
        elif isinstance(self.label, str):
            label = self.label
        else:
            assert isinstance(self.label.label, str)
            label = self.label.label
        if label:
            label = " " + repr(label)
        return (
            f"{self.styleclass if self.styleclass else 'Box'}{label}"
            f" at {self.pos}, size {self.size}"
            + (f" with {len(self.features)} features" if self.features else "")
        )

    def __repr__(self) -> str:
        return "".join(
            [
                f"{type(self).__name__}({self.pos!r}, {self.size!r}",
                f", label={self.label!r}" if self.label else "",
                f", uuid={self.uuid!r}" if self.uuid is not None else "",
                (
                    f", parent=<UUID={self.parent.uuid}>"
                    if self.parent is not None
                    else ""
                ),
                (
                    f", context={{{', '.join(repr(c) for c in sorted(self.context))}}}"
                    if self.context
                    else ""
                ),
                f", features={self.features!r}" if self.features else "",
                f", styleclass={self.styleclass!r}" if self.styleclass else "",
                ", hidelabel=True" if self.hidelabel else "",
                ", hidden=True" if self.hidden else "",
                ")",
            ]
        )


class Edge(aird.Vec2List):
    """An edge in the diagram.

    An Edge consists of a series of points that are traversed in order.
    Each point is given as Vector2D containing absolute coordinates.  At
    least two points are required.
    """

    JSON_TYPE = "edge"

    collapsed = False
    context: cabc.Set[str] = frozenset()
    port = False

    _hidelabel: bool

    def __init__(
        self,
        points: cabc.Iterable[aird.Vec2ish],
        *,
        label: Box | None = None,
        uuid: str | None = None,
        source: DiagramElement | None = None,
        target: DiagramElement | None = None,
        styleclass: str | None = None,
        styleoverrides: dict[str, t.Any] | None = None,
        hidelabel: bool = False,
        hidden: bool = False,
    ):
        """Construct an Edge.

        Parameters
        ----------
        source
            The source diagram element of this Edge.
        target
            The target diagram element of this Edge.
        label
            A Box describing this Edge's label.
        points
            A list of ``Vector2D``s with the (absolute) points this edge
            follows.
        uuid
            UUID of the semantic element this Edge represents.
        styleclass
            The CSS style class to use.
        styleoverrides
            A dict of CSS properties to override.
        hidelabel
            True to skip drawing this edge's label.
        hidden
            True to skip drawing this edge entirely.
        """
        super().__init__(points)
        if len(self) < 2:
            raise ValueError(
                "".join(
                    (
                        "At least two points are required",
                        f" for edge with uuid {uuid}" if uuid else "",
                    )
                )
            )

        self.source = source
        self.target = target

        self.uuid = uuid
        self.styleclass = styleclass
        self.styleoverrides = styleoverrides or {}

        self._label = label
        self.hidelabel = hidelabel
        self.hidden = hidden

    def add_context(self, uuid: str) -> None:
        """Do nothing."""
        # Edges don't save context

    def vector_snap(
        self, vector: aird.Vec2ish, direction: aird.Vec2ish
    ) -> aird.Vector2D:
        """Snap the ``vector`` onto this Edge.

        Parameters
        ----------
        direction
            Ignored.
        """
        del direction

        if not isinstance(vector, aird.Vector2D):
            vector = aird.Vector2D(*vector)

        if not SNAPPING:
            return vector

        epoint: aird.Vector2D  # Point on this Edge
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

    def move(self, offset: aird.Vector2D, *, children: bool = True) -> None:
        """Move all points of this edge by the specified offset."""
        del children
        for i, _ in enumerate(self):
            self[i] += offset

    @property
    def bounds(self) -> Box:
        """Calculate the bounding Box of this Edge."""
        if self.label is not None and not self.hidelabel:
            minx, miny = self.label.pos
            maxx, maxy = self.label.pos + self.label.size
        else:
            minx = miny = math.inf
            maxx = maxy = -math.inf

        for point in self.points:
            if point.x < minx:
                minx = point.x
            if point.y < miny:
                miny = point.y
            if point.x > maxx:
                maxx = point.x
            if point.y > maxy:
                maxy = point.y

        topleft = aird.Vector2D(minx, miny)
        bottomright = aird.Vector2D(maxx, maxy)
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
    def hidelabel(self) -> bool:
        """Return whether to skip rendering this Edge's label."""
        if self.label is not None:
            return self.label.hidden
        return self._hidelabel

    @hidelabel.setter
    def hidelabel(self, hide: bool) -> None:
        if self.label is not None:
            self.label.hidden = hide
        else:
            self._hidelabel = hide

    @property
    def label(self) -> Box | None:
        """Return this Edge's label."""
        return self._label

    @label.setter
    def label(self, label: Box | None) -> None:
        # Copy over label's hidden-flag
        if label is not None:
            label.hidden = self.hidelabel
        self._label = label

    @property
    def points(self) -> aird.Vec2List:
        """Return an iterable over this edge's points."""
        return self

    @points.setter
    def points(self, newpoints: cabc.Iterable[aird.Vec2ish]) -> None:
        self[:] = newpoints

    def __str__(self) -> str:
        # pylint: disable=consider-using-ternary
        numpoints = len(self.points)
        label = self.label and self.label.label or ""
        return (
            f"{self.styleclass or 'Edge'}"
            f"{f' {label!r}' if label else ''} between"
            f" {self[0]} and {self[-1]}"
            + (
                # pylint: disable=not-an-iterable  # false-positive
                f" via {', '.join(str(p) for p in self[1:-1])}"
                if numpoints > 2
                else ""
            )
        )

    def __repr__(self) -> str:
        return "".join(
            [
                f"{self.__class__.__name__}({list(self)!r}",
                f", label={self.label!r}" if self.label else "",
                f", uuid={self.uuid!r}" if self.uuid else "",
                f", styleclass={self.styleclass!r}" if self.styleclass else "",
                ", hidelabel=True" if self.hidelabel else "",
                ", hidden=True" if self.hidden else "",
                ")",
            ]
        )


class Circle:
    """Represents a circle."""

    JSON_TYPE = "circle"

    collapsed = False
    context: cabc.Set[str] = frozenset()
    hidelabel = True
    label = None
    port = False

    center = aird.Vec2Property()

    def __init__(
        self,
        center: aird.Vec2ish,
        radius: float | int,
        *,
        uuid: str | None = None,
        styleclass: str | None = None,
        styleoverrides: dict[str, t.Any] | None = None,
        hidden: bool = False,
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
        """
        self.uuid = uuid
        self.center = center
        self.radius = radius

        self.styleclass = styleclass
        self.styleoverrides = styleoverrides or {}
        self.hidden = hidden

    def add_context(self, uuid: str) -> None:
        """Do nothing."""
        # Circles don't save context

    @property
    def bounds(self) -> Box:
        """Calculate the bounding box of this Circle."""
        return Box(
            self.center - (self.radius, self.radius),
            (self.radius * 2, self.radius * 2),
        )

    def move(self, offset: aird.Vec2ish, *, children: bool = True) -> None:
        """Move this Circle on the 2-dimensional plane."""
        del children
        self.center += offset

    def vector_snap(
        self, vector: aird.Vec2ish, direction: aird.Vec2ish
    ) -> aird.Vector2D:
        """Snap the ``vector`` onto this Circle, preferably in `direction`."""
        if vector == self.center:
            vector = direction
        assert vector != (0, 0)
        if not isinstance(vector, aird.Vector2D):
            vector = aird.Vector2D(*vector)

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
    ):
        """Construct a new diagram.

        Parameters
        ----------
        name
            The diagram's name.
        uuid
            The unique ID of this diagram.
        viewport
            A Box describing this diagram's viewport.
        elements
            A :class:`list` containing the diagram's initial elements.
        """
        self.name = name
        self.uuid = uuid
        self.styleclass = styleclass

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
        """
        if element.uuid is not None:
            if element.uuid in self:
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
                    raise ValueError(
                        f"Duplicate element UUID {element.uuid!r}"
                    )

        if extend_viewport:
            self.__extend_viewport(element.bounds)
        self.__elements.append(element)

    def calculate_viewport(self, include_hidden: bool = False) -> None:
        """Recalculate the viewport so that all elements are contained.

        Parameters
        ----------
        include_hidden
            True to also include hidden elements when calculating the
            viewport.
        """
        minx = miny = math.inf
        maxx = maxy = -math.inf

        for elm in self:
            if elm.hidden and not include_hidden:
                continue

            bounds = elm.bounds
            minx = min(minx, bounds.pos.x)
            miny = min(miny, bounds.pos.y)
            maxx = max(maxx, bounds.pos.x + bounds.size.x)
            maxy = max(maxy, bounds.pos.y + bounds.size.y)

            if isinstance(elm.label, Box) and (
                not elm.hidelabel or include_hidden
            ):
                minx = min(minx, elm.label.pos.x)
                miny = min(miny, elm.label.pos.y)
                maxx = max(maxx, elm.label.pos.x + elm.label.size.x)
                maxy = max(maxy, elm.label.pos.y + elm.label.size.y)

        top_left = aird.Vector2D(minx, miny)
        bottom_right = aird.Vector2D(maxx, maxy)
        self.viewport = Box(
            top_left, bottom_right - top_left, styleclass="Viewport"
        )

    def normalize_viewport(
        self,
        offset: float | int | aird.Vec2ish = 0,
    ) -> None:
        """Normalize the viewport.

        This function moves all elements contained within this diagram
        so that the top left corner of the viewport is at (0, 0) (or the
        specified offset, if given).

        If a single value is given as offset, it is applied to both X
        and Y coordinates.
        """
        if isinstance(offset, aird.Vector2D):
            offsetvec = offset
        elif isinstance(offset, (list, tuple)):
            offsetvec = aird.Vector2D(*offset)
        else:
            offsetvec = aird.Vector2D(offset, offset)
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
        if isinstance(element.label, Box) and not element.hidelabel:
            lb = element.label
            b_tl = aird.Vector2D(
                min(bounds.pos.x, element.label.pos.x),
                min(bounds.pos.y, element.label.pos.y),
            )
            b_br = aird.Vector2D(
                max(bounds.pos.x + bounds.size.x, lb.pos.x + lb.size.x),
                max(bounds.pos.y + bounds.size.y, lb.pos.y + lb.size.y),
            )
            bounds = Box(b_tl, b_br - b_tl)

        if self.viewport is None:
            self.viewport = Box(bounds.pos, bounds.size, styleclass="Viewport")
        else:
            top_left = aird.Vector2D(
                min(self.viewport.pos.x, bounds.pos.x),
                min(self.viewport.pos[1], bounds.pos[1]),
            )
            bottom_right = aird.Vector2D(
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
                "\n".join(f"\t- {elm}" for elm in self)
                if self
                else "\t(empty)",
            ]
        )

    def __repr__(self) -> str:
        return "".join(
            [
                f"{self.__class__.__name__}("
                f"{self.name!r}, {self.viewport!r}, {self.__elements!r}",
                f", uuid={self.uuid!r}" if self.uuid else "",
                f", styleclass={self.styleclass!r}" if self.styleclass else "",
                ")",
            ]
        )

    def __iadd__(self, element: DiagramElement) -> "Diagram":
        self.add_element(element)
        return self
