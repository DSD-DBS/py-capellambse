# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Common constants and helpers used by all parser submodules."""
from __future__ import annotations

import collections.abc as cabc
import dataclasses
import enum
import logging
import math
import operator
import pathlib
import re
import typing as t

from lxml import builder, etree

import capellambse._namespaces as _n
import capellambse.loader
from capellambse import aird, helpers

LOGGER: logging.Logger = logging.getLogger(__name__)

ATT_XMID = f"{{{_n.NAMESPACES['xmi']}}}id"
ATT_XMT = f"{{{_n.NAMESPACES['xmi']}}}type"
ATT_XST = f"{{{_n.NAMESPACES['xsi']}}}type"

# Force ports to always have this size.
PORT_SIZE = aird.Vector2D(10, 10)

RE_COMPOSITE_FILTER = re.compile(r"/@filters\[name='(.*?)'\]$")
RE_STYLECLASS = re.compile(r"/@ownedRepresentations\[name='(.*?)'\]$")
RE_VIEWPOINT = re.compile(r"/@ownedViewpoints\[name='(.*?)'\]$")

XP_ANNOTATION_ENTRIES = etree.XPath(
    "./ownedAnnotationEntries[@source='GMF_DIAGRAMS']"
    "/data[@xmi:type='notation:Diagram']",
    namespaces=_n.NAMESPACES,
)
XP_DESCRIPTORS = etree.XPath(
    "./ownedRepresentationDescriptors"
    "[@xmi:type='viewpoint:DRepresentationDescriptor']",
    namespaces=_n.NAMESPACES,
)
XP_VIEWS = etree.XPath(
    "/xmi:XMI/viewpoint:DAnalysis/ownedViews[viewpoint]",
    namespaces=_n.NAMESPACES,
)
ELEMENT = builder.ElementMaker(nsmap={"xmi": str(_n.NAMESPACES["xmi"])})


@dataclasses.dataclass
class ElementBuilder:
    target_diagram: aird.Diagram
    diagram_tree: etree._Element
    data_element: etree._Element
    melodyloader: capellambse.loader.MelodyLoader
    fragment: pathlib.PurePosixPath


@dataclasses.dataclass
class SemanticElementBuilder(ElementBuilder):
    diag_element: etree._Element
    styleclass: str | None
    melodyobjs: cabc.MutableSequence[etree._Element]


class StackingBox(aird.Box):
    """A Box with special child-stacking behavior."""

    CHILD_MARGIN = 0

    children: StackingBox._StackingChildren  # type: ignore[name-defined]
    __features: cabc.MutableSequence[str] | None

    def __init__(
        self,
        pos: aird.Vector2D,
        size: aird.Vector2D | None = None,
        *,
        stacking_mode: StackingBox._StackingChildren.StackingMode,
        minsize: aird.Vec2ish = (0, 0),
        maxsize: aird.Vec2ish = (math.inf, math.inf),
        **kw: t.Any,
    ) -> None:
        del size

        super().__init__(
            pos,
            aird.Vector2D(0, 0),
            minsize=minsize,
            maxsize=maxsize,
            **kw,
        )
        self.children = self._StackingChildren(self)
        self.stacking_mode = stacking_mode

    def _topsection_size(self) -> aird.Vector2D:
        """Calculate the size of the top section (this Box' own label).

        Parameters
        ----------
        width
            The maximum width for wrapping label text
        """
        try:
            width = max(map(operator.attrgetter("size.x"), self.children))
        except ValueError:
            width = 0
        # pylint: disable=unpacking-non-sequence  # false-positive
        pad_x, pad_y = self.padding * 2
        if isinstance(self.label, str):
            label_extent = helpers.get_text_extent(
                self.label, width - pad_x if width else math.inf
            )
        else:
            label_extent = (0, 0)
        width = width or label_extent[0] + pad_x
        if self.features:
            features_height = helpers.get_text_extent(
                "\n".join(self.features), width
            )[1]
            features_height += 24  # Divider line
        else:
            features_height = 0
        height = label_extent[1] + features_height + pad_y
        return aird.Vector2D(width, height)

    @property
    def size(self) -> aird.Vector2D:
        pwidth, pheight = self._topsection_size()
        child_bounds = [i.bounds for i in self.children if not i.hidden]
        try:
            width = max(i.size.x for i in child_bounds)
        except ValueError:
            width = pwidth
        cheight = sum(i.size.y for i in child_bounds)
        return aird.Vector2D(width, cheight + pheight)

    @size.setter
    def size(self, new_size: aird.Vec2ish) -> None:
        if any(i != 0 for i in new_size):
            raise TypeError("The size of this Box cannot be changed directly")

    @property
    def stacking_mode(self) -> StackingBox._StackingChildren.StackingMode:
        """Return the current stacking mode."""
        return self.children.stacking_mode

    @stacking_mode.setter
    def stacking_mode(self, new_mode: str) -> None:
        try:
            self.children.stacking_mode = self._StackingChildren.StackingMode(
                new_mode
            )
        except ValueError:
            try:
                self.children.stacking_mode = (
                    self._StackingChildren.StackingMode[new_mode]
                )
            except KeyError:
                raise ValueError(
                    f"Invalid stacking mode: {new_mode!r}"
                ) from None

    @property  # type: ignore[override]
    def features(self) -> cabc.Sequence[str] | None:
        """Return the list of Box' features."""
        return self.__features

    @features.setter
    def features(
        self,
        new_features: cabc.Sequence[str] | None,
    ) -> None:
        if new_features is None:
            self.__features = None
        else:
            self.__features = self._SBFeatures(self, new_features)
            try:
                children = self.children
            except AttributeError:
                pass
            else:
                children._restack()

    def snap_to_parent(self, *_: t.Any) -> None:
        pass  # FIXME

    class _SBFeatures(t.MutableSequence[str]):
        def __init__(
            self, parent: StackingBox, *args: t.Any, **kw: t.Any
        ) -> None:
            super().__init__()
            self.__list: list[str] = list(*args, **kw)
            self.__parent = parent

        def __iter__(self) -> cabc.Iterator[str]:
            return iter(self.__list)

        @t.overload
        def __getitem__(self, index: int) -> str:
            ...

        @t.overload
        def __getitem__(self, index: slice) -> list[str]:
            ...

        def __getitem__(self, index: int | slice) -> str | list[str]:
            return self.__list[index]

        @t.overload
        def __setitem__(self, index: int, value: str) -> None:
            ...

        @t.overload
        def __setitem__(self, index: slice, value: cabc.Iterable[str]) -> None:
            ...

        def __setitem__(
            self,
            index: int | slice,
            value: str | cabc.Iterable[str],
        ) -> None:
            self.__list[index] = value  # type: ignore[index,assignment]
            self.__parent.children._restack()

        def __delitem__(self, index: int | slice) -> None:
            del self.__list[index]
            self.__parent.children._restack()

        def __len__(self) -> int:
            return len(self.__list)

        def insert(self, index: int, value: str) -> None:
            self.__list.insert(index, value)
            self.__parent.children._restack()

        def __repr__(self) -> str:
            return repr(self.__list)

    class _StackingChildren(t.MutableSequence[aird.DiagramElement]):
        class StackingMode(enum.Enum):
            """The possible modes for stacking child boxes."""

            VERTICAL = "VerticalStack"
            HORIZONTAL = "HorizontalStack"

        def __init__(
            self,
            parent: StackingBox,
            stacking_mode: StackingMode = StackingMode.VERTICAL,
        ):
            self.__list: list[aird.DiagramElement] = []
            self.__parent = parent
            self.stacking_mode = stacking_mode

        def __iter__(self) -> cabc.Iterator[aird.DiagramElement]:
            return iter(self.__list)

        @t.overload
        def __getitem__(self, index: int) -> aird.DiagramElement:
            ...

        @t.overload
        def __getitem__(self, index: slice) -> list[aird.DiagramElement]:
            ...

        def __getitem__(
            self, index: int | slice
        ) -> aird.DiagramElement | list[aird.DiagramElement]:
            return self.__list[index]

        @t.overload
        def __setitem__(self, index: int, value: aird.DiagramElement) -> None:
            ...

        @t.overload
        def __setitem__(
            self, index: slice, value: cabc.Iterable[aird.DiagramElement]
        ) -> None:
            ...

        def __setitem__(
            self,
            index: int | slice,
            value: aird.DiagramElement | cabc.Iterable[aird.DiagramElement],
        ) -> None:
            self.__list[index] = value  # type: ignore[index, assignment]
            self._restack()

        def __delitem__(self, index: int | slice) -> None:
            del self.__list[index]
            self._restack()

        def __len__(self) -> int:
            return len(self.__list)

        def insert(self, index: int, value: aird.DiagramElement) -> None:
            self.__list.insert(index, value)
            self._restack()

        def _restack(self) -> None:
            if (
                self.stacking_mode
                is StackingBox._StackingChildren.StackingMode.VERTICAL
            ):
                xpos, ypos = self.__parent.pos
                ypos += self.__parent._topsection_size()[1]
                for obj in self.__list:
                    obj_bounds = obj.bounds
                    offset = aird.Vector2D(xpos, ypos) - obj_bounds.pos
                    obj.move(offset)
                    ypos += obj_bounds.size.y
            elif (
                self.stacking_mode
                is StackingBox._StackingChildren.StackingMode.HORIZONTAL
            ):
                raise NotImplementedError()
            else:
                raise RuntimeError(
                    f"Invalid stacking_mode: {self.stacking_mode!r}"
                )


class CenterAnchoredBox(aird.Box):
    """A special Box subclass that uses its center as reference point."""

    center: aird.Vec2Property = aird.Vec2Property()  # type: ignore[assignment]

    def __init__(
        self, center: aird.Vec2ish, size: aird.Vec2ish, **kwargs: t.Any
    ) -> None:
        """Create a CenterAnchoredBox.

        This class supports the same keyword arguments that the parent
        :class:`Box` class supports.

        Parameters
        ----------
        center
            The point at which to place this Box' center
        size
            The width and height of this Box
        """
        super().__init__((math.inf, math.inf), size, **kwargs)
        self.center = center

    @property  # type: ignore[override]
    def pos(self) -> aird.Vector2D:
        """Return the top left corner position of this Box."""
        return self.center - self.size / 2

    @pos.setter
    def pos(self, new_pos: aird.Vec2ish) -> None:
        if new_pos == aird.Vector2D(math.inf, math.inf):
            return
        self.center = aird.Vector2D(*new_pos) + self.size / 2

    def __repr__(self) -> str:
        return super().__repr__().replace(repr(self.pos), repr(self.center), 1)


class SkipObject(Exception):
    """Raised to stop parsing this object."""

    @classmethod
    def raise_(cls, *args: t.Any, **kw: t.Any) -> t.NoReturn:
        """Raise this exception, ignoring the arguments."""
        del args, kw
        raise cls()


def get_spec_text(seb: SemanticElementBuilder) -> str:
    """Get the ``ownedSpecification`` text for display."""
    try:
        spec = next(seb.melodyobjs[0].iterchildren("ownedSpecification"))
        spec = next(spec.iterchildren("bodies"))
    except StopIteration:
        return ""
    text = helpers.unescape_linked_text(seb.melodyloader, spec.text)
    return text.striptags()
