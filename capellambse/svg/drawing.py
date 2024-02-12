# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Custom extensions to the svgwrite ``Drawing`` object."""
from __future__ import annotations

import collections.abc as cabc
import copy
import dataclasses
import logging
import os
import re
import typing as t

from svgwrite import base, container, drawing, shapes
from svgwrite import text as svgtext

from capellambse import diagram
from capellambse import helpers as chelpers
from capellambse.diagram import capstyle

from . import decorations, generate, helpers, style, symbols

LOGGER = logging.getLogger(__name__)
DEBUG = "CAPELLAMBSE_SVG_DEBUG" in os.environ
"""Debug flag to render helping lines."""
LABEL_ICON_PADDING = 2
"""Default padding between a label's icon and text."""
NUMBER = r"-?\d+(\.\d+)?"
RE_ROTATION = re.compile(
    rf"rotate\((?P<angle>{NUMBER}),\s*(?P<x>{NUMBER}),\s*(?P<y>{NUMBER})\) "
    f"(?P<tspan_y>{NUMBER})"
)


LabelDict = t.TypedDict(
    "LabelDict",
    {
        "x": float,
        "y": float,
        "width": float,
        "height": float,
        "text": str,
        "class": str,
    },
    total=False,
)


class Drawing:
    """The main container that stores all svg elements."""

    def __init__(self, metadata: generate.DiagramMetadata):
        superparams = {
            "cursor": "pointer",
            "filename": f"{metadata.name}.svg",
            "font-family": "Open Sans",
            "font-size": "8px",
            "shape-rendering": "geometricPrecision",
            "size": metadata.size,
            "viewBox": metadata.viewbox,
        }
        if metadata.class_:
            superparams["class_"] = re.sub(r"\s+", "", metadata.class_)

        self.__drawing = drawing.Drawing(**superparams)
        self.diagram_class = metadata.class_
        self.deco_cache: set[str] = set()
        self.add_backdrop(pos=metadata.pos, size=metadata.size)

        self.obj_cache: dict[str | None, t.Any] = {}

    @property
    def filename(self) -> str:
        """Return the filename of the SVG."""
        return self.__drawing.filename

    @filename.setter
    def filename(self, name: str) -> None:
        self.__drawing.filename = name

    def save_as(self, filename: str | None = None, **kw: t.Any) -> None:
        """Write the SVG to a file.

        If ``filename`` wasn't given the underlying ``filename`` is
        taken.
        """
        kw["filename"] = filename or self.__drawing.filename
        return self.__drawing.saveas(**kw)

    def to_string(self) -> str:
        """Return a string representation of the SVG."""
        return self.__drawing.tostring()

    def add_backdrop(
        self, pos: tuple[float, float], size: tuple[float, float]
    ) -> None:
        """Add a white background rectangle to the drawing."""
        self.__backdrop = self.__drawing.rect(
            insert=pos,
            size=size,
            fill="#fff",
            stroke="none",
        )
        self.__drawing.add(self.__backdrop)

    def __repr__(self) -> str:
        return self.__drawing._repr_svg_()

    def add_rect(
        self,
        pos: tuple[float, float],
        size: tuple[float, float],
        rectstyle: cabc.Mapping[str, style.Styling],
        *,
        class_: str = "",
        context_: cabc.Sequence[str] = (),
        label: LabelDict | None = None,
        description: str | None = None,
        features: cabc.Sequence[str] = (),
        id_: str | None = None,
        children: bool = False,
    ) -> container.Group:
        """Add a rectangle with auto-aligned text to the group."""
        gcls = "".join(f" context-{i}" for i in context_)
        grp: container.Group = self.__drawing.g(
            class_=f"Box {class_}{gcls}", id_=id_
        )
        text_style = rectstyle["text_style"]
        rect_style = rectstyle["obj_style"]
        transform = chelpers.get_transformation(class_, pos, size)
        rectparams: dict[str, t.Any] = {
            "insert": pos,
            "size": size,
            "class_": class_,
            **transform,
        }

        rect: shapes.Rect = self.__drawing.rect(
            **rectparams, **rect_style._to_dict()
        )
        grp.add(rect)

        if description is not None and label is not None:
            new_label: LabelDict = copy.deepcopy(label)
            new_label["text"] = description
            self._draw_label(
                LabelBuilder(
                    new_label,
                    grp,
                    labelstyle=text_style,
                    class_=class_,
                    text_anchor="middle",
                    y_margin=None,
                    icon=False,
                )
            )

        if features or class_ in decorations.needs_feature_line:
            self._draw_feature_line(rect, grp, rect_style)
            if features:
                self._draw_feature_text(
                    rect, features, class_, grp, text_style
                )

        if label:
            text_anchor = (
                "start" if class_ in decorations.start_aligned else "middle"
            )
            y_margin = None
            if children or class_ in decorations.always_top_label:
                y_margin = 5

            self._draw_label(
                LabelBuilder(
                    label,
                    grp,
                    labelstyle=text_style,
                    class_=class_,
                    text_anchor=text_anchor,
                    y_margin=y_margin,
                )
            )
        elif class_ in decorations.only_icons:
            icon_size = 50
            labelpos = (
                pos[0] + (size[0] - icon_size / 4) / 2,
                pos[1] + (decorations.feature_space - 15) / 2,
            )
            label = {
                "x": labelpos[0],
                "y": labelpos[1],
                "width": 0.0,
                "height": 0.0,
                "text": "",
                "class": "",
            }
            self.add_label_image(
                LabelBuilder(
                    label, grp, text_style, class_=class_, icon_size=icon_size
                ),
                labelpos,
            )

        if DEBUG:
            self._draw_rect_helping_lines(grp, pos, size)

        return grp

    def _draw_feature_line(
        self,
        obj: base.BaseElement,
        group: container.Group | None,
        objstyle: style.Styling | None,
    ) -> shapes.Line | None:
        """Draw a Line on the given object."""
        x, y = obj.attribs["x"], obj.attribs["y"]
        w = obj.attribs["width"]

        line = self.__drawing.line(
            start=(x, y + decorations.feature_space),
            end=(x + w, y + decorations.feature_space),
            stroke=getattr(objstyle, "stroke", None),
        )
        if group is None:
            return line

        return group.add(line)

    def _draw_feature_text(
        self,
        obj: base.BaseElement,
        features: cabc.Sequence[str],
        class_: str,
        group: container.Group,
        labelstyle: style.Styling,
    ) -> None:
        """Draw features text on given object."""
        x, y = obj.attribs["x"], obj.attribs["y"]
        w, h = obj.attribs["width"], obj.attribs["height"]
        label: LabelDict = {
            "x": x + decorations.feature_space / 2,
            "y": y + decorations.feature_space,
            "width": w - decorations.feature_space / 2,
            "height": h - decorations.feature_space,
            "class": "Features",
            "text": "\n".join(
                chelpers.flatten_html_string(feat) for feat in features
            ),
        }
        self._draw_label(
            LabelBuilder(
                label,
                group,
                class_=class_,
                labelstyle=labelstyle,
                y_margin=7,
                icon=False,
                alignment="left",
            )
        )

    def _draw_label(self, builder: LabelBuilder) -> None:
        """Draw label text on given object and return the label's group."""
        assert isinstance(builder.label["x"], (int, float))
        assert isinstance(builder.label["y"], (int, float))
        assert isinstance(builder.label["width"], (int, float))
        assert isinstance(builder.label["height"], (int, float))
        assert isinstance(builder.label.get("text", ""), str)

        text = self._make_text(builder)
        builder.icon &= f"{builder.class_}Symbol" in decorations.deco_factories
        if not text.elements:
            lines = render_hbounded_lines(builder, builder.icon)
            x, y = get_label_position(builder, lines)
            for line in lines.lines:
                params = {
                    "insert": (x, y),
                    "text": line,
                    "xml:space": "preserve",
                }
                text.add(svgtext.TSpan(**params))
                y += lines.line_height

            if builder.icon:
                icon_pos = get_label_icon_position(builder, lines)
                self.add_label_image(builder, icon_pos)
        return builder.group

    def _make_text(self, builder: LabelBuilder) -> svgtext.Text:
        """Return a text element and add it to the builder group."""
        textattrs = {
            "text": "",
            "insert": (builder.label["x"], builder.label["y"]),
            "text_anchor": builder.text_anchor,
            "dominant_baseline": "middle",
        }
        if "class" in builder.label:
            textattrs["class_"] = builder.label["class"]

        if transform := getattr(builder.labelstyle, "transform", None):
            if match := re.search(RE_ROTATION, transform):
                if match.group("angle") != "-90":
                    raise NotImplementedError(
                        "Angles other than -90 are not supported"
                    )

                x = float(match.group("x"))
                y = float(match.group("y"))
                if new_y := match.group("tspan_y"):
                    y = float(new_y)
                    transform = transform.replace(f" {new_y}", "")

            textattrs["transform"] = transform
            delattr(builder.labelstyle, "transform")

        text = self.__drawing.text(
            **textattrs, **builder.labelstyle._to_dict()
        )
        if transform:
            params = {
                "insert": (x, y),
                "text": str(builder.label["text"]),
                "xml:space": "preserve",
            }
            text.add(svgtext.TSpan(**params))
        builder.group.add(text)
        return text

    def add_label_image(
        self, builder: LabelBuilder, pos: tuple[float, float]
    ) -> None:
        """Add label svgobject to given group."""
        if builder.class_ is None:
            builder.class_ = "Error"

        if builder.class_ not in self.deco_cache:
            self._add_decofactory(builder.class_)

        builder.group.add(
            self.__drawing.use(
                href=f"#{builder.class_}Symbol",
                insert=pos,
                size=(builder.icon_size, builder.icon_size),
            )
        )

    def get_port_transformation(
        self,
        pos: tuple[float, float],
        size: tuple[float, float],
        class_: str,
        parent_id: str | None,
    ) -> str:
        """Return rotation transformation for port-object-styling."""
        rect = self.obj_cache[parent_id]
        x, y = pos
        w, h = size
        angle = 0
        par_x, par_y = rect["x"] + 0.5, rect["y"] + 0.5
        if x <= par_x:
            angle = 90
        elif par_x + rect["width"] < x + w:
            angle = -90
        elif y <= par_y:
            angle = -180

        angle += 180 * (class_ in ["FOP", "CP_IN"])
        return f"rotate({angle} {x + w / 2} {y + h / 2})"

    def add_port(
        self,
        pos: tuple[float, float],
        size: tuple[float, float],
        text_style: style.Styling,
        parent_id: str | None,
        *,
        class_: str,
        context_: cabc.Sequence[str] = (),
        obj_style: style.Styling,
        label: LabelDict | None = None,
        id_: str | None = None,
    ) -> container.Group:
        gcls = "".join(f" context-{i}" for i in context_)
        grp = self.__drawing.g(class_=f"Box {class_}{gcls}", id_=id_)
        if class_ in decorations.all_directed_ports:
            port_id = "Error"
            if class_ in decorations.function_ports:
                port_id = "Port"
            elif class_ in decorations.component_ports:
                port_id = "ComponentPort"

            if port_id not in self.deco_cache:
                self._add_decofactory(port_id)

            grp.add(
                self.__drawing.use(
                    href=f"#{port_id}Symbol",
                    insert=pos,
                    size=size,
                    transform=self.get_port_transformation(
                        pos, size, class_, parent_id
                    ),
                    class_=class_,
                    **obj_style._to_dict(),
                )
            )
        else:
            grp.add(
                self.__drawing.rect(
                    insert=pos,
                    size=size,
                    class_=class_,
                    transform=self.get_port_transformation(
                        pos, size, class_, parent_id
                    ),
                    **obj_style._to_dict(),
                )
            )

        if label is not None:
            self._draw_label(
                LabelBuilder(
                    label,
                    grp,
                    class_="Annotation",
                    labelstyle=text_style,
                    text_anchor="middle",
                    y_margin=0,
                    icon=False,
                )
            )

        return grp

    def draw_object(self, obj: cabc.Mapping[str, t.Any]) -> None:
        """Draw an object into this drawing.

        Parameters
        ----------
        obj
            The (decoded) JSON-dict of a single diagram object.
        """
        mobj = copy.deepcopy(obj)
        del obj
        type_mapping: dict[str, tuple[t.Any, str]] = {
            "box": (self._draw_box, "Box"),
            "edge": (self._draw_edge, "Edge"),
            "circle": (self._draw_circle, "Edge"),
            "symbol": (self._draw_symbol, "Box"),
            "box_symbol": (self._draw_box_symbol, "Box"),
        }

        try:
            drawfunc, style_type = type_mapping[mobj["type"]]
        except KeyError:
            raise ValueError(f"Invalid object type: {mobj['type']}") from None

        objparams = {
            f"{k}_": v for k, v in mobj.items() if k not in {"type", "style"}
        }
        if mobj["class"] in decorations.all_ports:
            mobj["type"] = "box"  # type: ignore[index]

        class_: str = style_type + (
            f".{mobj['class']}" if "class" in mobj else ""
        )

        my_styles: dict[str, t.Any] = {
            **capstyle.get_style(self.diagram_class, class_),
            **mobj.get("style", {}),
        }
        obj_style = style.Styling(
            self.diagram_class,
            class_,
            **{k: v for k, v in my_styles.items() if "_" not in k},
        )
        text_style = style.Styling(
            self.diagram_class,
            class_,
            "text",
            **{
                k[5:]: v for k, v in my_styles.items() if k.startswith("text_")
            },
        )

        self.obj_cache[mobj["id"]] = mobj

        drawfunc(**objparams, obj_style=obj_style, text_style=text_style)

        self._deploy_defs(obj_style)
        self._deploy_defs(text_style)

    def _deploy_defs(self, styling: style.Styling) -> None:
        defs_ids = {d.attribs.get("id") for d in self.__drawing.defs.elements}
        for attr in styling:
            val = getattr(styling, attr)
            if isinstance(val, cabc.Iterable) and not isinstance(
                val, (str, diagram.RGB)
            ):
                grad_id = styling._generate_id("CustomGradient", val)
                if grad_id not in defs_ids:
                    gradient = symbols._make_lgradient(
                        id_=grad_id, stop_colors=val
                    )
                    self.__drawing.defs.add(gradient)
                    defs_ids.add(grad_id)

        defaultstyles = diagram.get_style(self.diagram_class, styling._class)

        def getstyleattr(sobj: object, attr: str) -> t.Any:
            return getattr(sobj, attr, None) or defaultstyles.get(
                styling._style_name(attr)
            )

        markers = (
            getstyleattr(super(), "marker-start"),
            getstyleattr(super(), "marker-end"),
        )
        for marker in markers:
            if marker is None:
                continue

            stroke = str(getstyleattr(styling, "stroke"))
            stroke_width = str(getstyleattr(styling, "stroke-width"))
            marker_id = styling._generate_id(marker, [stroke])
            if marker_id not in defs_ids:
                factory = decorations.deco_factories[marker]
                markstyle = style.Styling(
                    self.diagram_class,
                    styling._class,
                    _prefix=styling._prefix,
                    _markers=False,
                    stroke=stroke,
                    stroke_width=stroke_width,
                )._to_dict()
                markstyle.pop("marker-start", None)
                markstyle.pop("marker-end", None)
                self.__drawing.defs.add(
                    factory.function(marker_id, **markstyle)
                )
                defs_ids.add(marker_id)

    def _draw_symbol(
        self,
        *,
        x_: int | float,
        y_: int | float,
        width_: int | float,
        height_: int | float,
        context_: cabc.Sequence[str] = (),
        parent_: str | None = None,
        label_: LabelDict | None = None,
        id_: str | None = None,
        class_: str,
        obj_style: style.Styling,
        text_style: style.Styling,
        **kw: t.Any,
    ):
        del kw  # Dismiss additional info from json
        assert isinstance(label_, (dict, type(None)))
        pos = (x_ + 0.5, y_ + 0.5)
        size = (width_, height_)
        if (
            class_ not in self.deco_cache
            and class_ not in decorations.all_ports
        ):
            self._add_decofactory(class_)

        if class_ in decorations.all_ports:
            grp = self.add_port(
                pos,
                size,
                text_style,
                parent_,
                class_=class_,
                context_=context_,
                obj_style=obj_style,
                label=label_,
                id_=id_,
            )
        else:
            gcls = "".join(f" context-{i}" for i in context_)
            grp = self.__drawing.g(class_=f"Box {class_}{gcls}", id_=id_)
            grp.add(
                self.__drawing.use(
                    href=f"#{class_}Symbol",
                    insert=pos,
                    size=size,
                    class_=class_,
                    **obj_style._to_dict(),
                )
            )

        self.__drawing.add(grp)
        if label_:
            label_["class"] = "Annotation"
            self._draw_label(
                LabelBuilder(
                    label_,
                    grp or self.__drawing.elements[-1],
                    labelstyle=text_style,
                    class_=class_,
                    y_margin=0,
                    text_anchor="middle",
                    icon=False,
                )
            )

    def _draw_box(
        self,
        *,
        x_: int | float,
        y_: int | float,
        width_: int | float,
        height_: int | float,
        context_: cabc.Sequence[str] = (),
        children_: cabc.Sequence[str] = (),
        features_: cabc.Sequence[str] = (),
        label_: str | LabelDict | None = None,
        description_: str | None = None,
        id_: str,
        class_: str,
        obj_style: style.Styling,
        text_style: style.Styling,
        **kw: t.Any,
    ) -> container.Group:
        del kw  # Dismiss additional info from json, for e.g.: ports_
        pos = (x_ + 0.5, y_ + 0.5)
        size = (width_, height_)
        rect_style = {"text_style": text_style, "obj_style": obj_style}
        label: LabelDict | None = None
        if isinstance(label_, str):
            label = {
                "x": x_,
                "y": y_,
                "width": width_,
                "height": height_,
                "text": label_,
                "class": class_ or "Box",
            }
        elif label_ is not None:
            label = label_
            label["class"] = "Annotation"

        grp = self.add_rect(
            pos,
            size,
            rect_style,
            class_=class_,
            context_=context_,
            id_=id_,
            label=label,
            description=description_,
            features=features_,
            children=bool(children_),
        )
        return self.__drawing.add(grp)

    def _draw_box_symbol(
        self,
        *,
        x_: int | float,
        y_: int | float,
        width_: int | float,
        height_: int | float,
        label_: LabelDict,
        id_: str,
        class_: str,
        context_: cabc.Sequence[str] = (),
        obj_style: style.Styling,
        text_style: style.Styling,
        **kw: t.Any,
    ) -> container.Group:
        del kw

        grp = self._draw_box(
            x_=x_,
            y_=y_,
            width_=width_,
            height_=height_,
            id_=id_,
            class_=class_,
            context_=context_,
            obj_style=obj_style,
            text_style=text_style,
        )
        label_["class"] = "Annotation"
        self._draw_label(
            LabelBuilder(
                label_,
                grp or self.__drawing.elements[-1],
                labelstyle=text_style,
                class_=class_,
                y_margin=0,
                text_anchor="middle",
                icon=False,
            )
        )
        return grp

    def _draw_circle(
        self,
        *,
        center_: tuple[float, float],
        radius_: float,
        id_: str | None = None,
        class_: str | None = None,
        context_: cabc.Sequence[str] = (),
        obj_style: style.Styling,
        text_style: style.Styling,
    ) -> container.Group:
        del text_style  # No label for circles
        center_ = (center_[0] + 0.5, center_[1] + 0.5)
        obj_style.fill = obj_style.stroke or diagram.RGB(0, 0, 0)
        del obj_style.stroke
        gcls = "".join(f" context-{i}" for i in context_)
        grp = self.__drawing.g(class_=f"Circle {class_}{gcls}", id_=id_)
        circle = self.__drawing.circle(
            center=center_, r=radius_, **obj_style._to_dict()
        )
        grp.add(circle)
        return self.__drawing.add(grp)

    def _draw_edge(
        self,
        *,
        points_: list[list[int]],
        labels_: t.Sequence[LabelDict] = (),
        id_: str,
        class_: str,
        context_: cabc.Sequence[str] = (),
        obj_style: style.Styling,
        text_style: style.Styling,
        **kw,
    ) -> container.Group:
        del kw
        points: list = [(x + 0.5, y + 0.5) for x, y in points_]
        gcls = "".join(f" context-{i}" for i in context_)
        grp = self.__drawing.g(class_=f"Edge {class_}{gcls}", id_=id_)
        path = self.__drawing.path(
            d=["M"] + points, class_="Edge", **obj_style._to_dict()
        )
        grp.add(path)

        # Received text space doesn't allow for anything else than the text
        for label_ in labels_:
            label_["class"] = "Annotation"
            self._draw_edge_label(
                label_,
                grp,
                labelstyle=text_style,
                text_anchor="middle",
                class_=class_,
                y_margin=0,
            )
        return self.__drawing.add(grp)

    def _draw_edge_label(
        self,
        label: LabelDict,
        group: container.Group,
        *,
        class_: str,
        labelstyle: style.Styling,
        text_anchor: str = "start",
        y_margin: int | float,
    ) -> container.Group:
        if f"{class_}Symbol" in decorations.deco_factories:
            additional_space = (
                decorations.icon_size + 2 * decorations.icon_padding
            )
            label["width"] += additional_space + 2
            label["x"] -= additional_space / 2

        self._draw_label(
            LabelBuilder(
                label,
                group,
                labelstyle=labelstyle,
                class_=class_,
                y_margin=y_margin,
                text_anchor=text_anchor,
            )
        )

        return group

    def _draw_line(
        self,
        data: dict[str, float | int],
        *,
        obj_style: style.Styling,
    ) -> shapes.Line | None:
        """Draw a Line on the given object."""
        x1, y1 = data["x"], data["y"]
        x2 = data.get("x1") or data["x"] + data["width"]
        y2 = data.get("y1") or data["y"]
        line = self.__drawing.line(
            start=(x1, y1), end=(x2, y2), **obj_style._to_dict()
        )
        return line

    def _draw_rect_helping_lines(
        self,
        grp: container.Group,
        pos: tuple[float, float],
        size: tuple[float, float],
    ) -> None:
        linestyle = style.Styling(
            self.diagram_class,
            "Edge",
            stroke="rgb(239, 41, 41)",
            **{"stroke-dasharray": "5"},
        )
        start = (pos[0] + size[0] / 2, pos[1])
        end = (pos[0] + size[0] / 2, pos[1] + size[1])
        ln = self.__drawing.line(start=start, end=end, **linestyle._to_dict())
        grp.add(ln)

        y = pos[1] + size[1] / 2
        start = (pos[0], y)
        end = (pos[0] + size[0], y)
        ln = self.__drawing.line(start=start, end=end, **linestyle._to_dict())
        grp.add(ln)

    def _add_decofactory(self, name: str) -> None:
        factory = decorations.deco_factories[f"{name}Symbol"]
        self.__drawing.defs.add(factory.function())
        for dep in factory.dependencies:
            if dep not in self.deco_cache:
                self._add_decofactory(dep)

        self.deco_cache.add(name)


@dataclasses.dataclass
class LabelBuilder:
    """Helper data-class for building labels."""

    label: LabelDict
    group: container.Group
    labelstyle: style.Styling
    class_: str | None = None
    y_margin: int | float | None = None
    text_anchor: str = "start"
    icon: bool = True
    icon_size: float | int = decorations.icon_size
    alignment: helpers.AlignmentLiteral = "center"


class LinesData(t.NamedTuple):
    """Helper data-tuple for rendering text-lines from labels."""

    lines: list[str]
    line_height: float
    text_height: float
    margin: float
    max_line_width: float


def render_hbounded_lines(
    builder: LabelBuilder, render_icon: bool
) -> LinesData:
    """Return Lines data to render a label."""
    (
        lines,
        label_margin,
        max_text_width,
    ) = helpers.check_for_horizontal_overflow(
        str(builder.label["text"]),
        builder.label["width"],
        decorations.icon_padding if render_icon else 0,
        builder.icon_size if render_icon else 0,
        builder.alignment,
    )
    lines_to_render = helpers.check_for_vertical_overflow(
        lines, builder.label["height"], max_text_width
    )
    line_height = max(j for _, j in map(chelpers.extent_func, lines_to_render))
    text_height = line_height * len(lines_to_render)
    max_line_width = max(
        w for w, _ in map(chelpers.extent_func, lines_to_render)
    )
    assert max_text_width >= max_line_width
    return LinesData(
        lines_to_render, line_height, text_height, label_margin, max_line_width
    )


def get_label_position(
    builder: LabelBuilder, lines: LinesData
) -> tuple[float, float]:
    """Return the initial label position (x, y)."""
    icon_size = (builder.icon_size + decorations.icon_padding) * builder.icon
    if builder.text_anchor == "start":
        builder.label["x"] += lines.margin + icon_size
    else:
        builder.label["x"] += (builder.label["width"] + icon_size) / 2

    dominant_baseline_adjust = chelpers.extent_func(lines.lines[0])[1] / 2
    if builder.y_margin is None:
        builder.y_margin = (builder.label["height"] - lines.text_height) / 2
    builder.label["y"] += builder.y_margin + dominant_baseline_adjust
    return builder.label["x"], builder.label["y"]


def get_label_icon_position(
    builder: LabelBuilder, lines: LinesData
) -> tuple[float, float]:
    """Calculate the icon's position."""
    icon_y = builder.label["y"] - builder.icon_size / 2
    if lines.text_height > lines.line_height:
        icon_y += lines.text_height / 2 - decorations.icon_padding * 2
        if builder.label["class"] == "Annotation":
            icon_y -= decorations.icon_padding

    icon_x = (
        builder.label["x"] - builder.icon_size - decorations.icon_padding * 2
    )
    if builder.text_anchor == "middle":
        icon_x -= lines.max_line_width / 3
    return (icon_x, icon_y)
