# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Custom extensions to the svgwrite ``Drawing`` object."""

from __future__ import annotations

import collections.abc as cabc
import copy
import dataclasses
import logging
import math
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

    def __init__(
        self,
        metadata: generate.DiagramMetadata,
        *,
        font_family: str = "'Open Sans','Segoe UI',Arial,sans-serif",
        font_size: int = chelpers.DEFAULT_FONT_SIZE,
        transparent_background: bool = False,
    ):
        superparams = {
            "filename": f"{metadata.name}.svg",
            "font-family": font_family,
            "font-size": f"{font_size}px",
            "shape-rendering": "geometricPrecision",
            "size": metadata.size,
            "viewBox": metadata.viewbox,
        }
        if metadata.class_:
            superparams["class_"] = re.sub(r"\s+", "", metadata.class_)

        self.__drawing = drawing.Drawing(**superparams)
        self.diagram_class = metadata.class_
        self.deco_cache: set[str] = set()
        if not transparent_background:
            self._add_backdrop(pos=metadata.pos, size=metadata.size)

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

    def _add_backdrop(
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

    def _add_rect(
        self,
        pos: tuple[float, float],
        size: tuple[float, float],
        rectstyle: cabc.Mapping[str, style.Styling],
        *,
        class_: str = "",
        context_: cabc.Sequence[str] = (),
        labels: list[LabelDict] | None = None,
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

        if description is not None and labels:
            labels = labels[0:]
            labels[0]["text"] = description
            self._draw_label(
                LabelBuilder(
                    *size,
                    labels,
                    grp,
                    labelstyle=text_style,
                    class_=class_,
                    text_anchor="middle",
                    y_margin=0,
                    icon=False,
                )
            )

        lines = None
        if labels:
            y_margin = 1
            if class_ not in decorations.needs_feature_line and (
                children or class_ in decorations.always_top_label
            ):
                y_margin = 3

            lines = self._draw_label(
                LabelBuilder(
                    *size,
                    labels,
                    grp,
                    labelstyle=text_style,
                    class_=class_,
                    text_anchor="middle",
                    y_margin=y_margin,
                )
            )
        elif class_ in decorations.only_icons:
            icon_size = 50
            labelpos = (
                pos[0] + (size[0] - icon_size / 4) / 2,
                pos[1] + (decorations.feature_space - 15) / 2,
            )
            labels = [
                {
                    "x": labelpos[0],
                    "y": labelpos[1],
                    "width": 0.0,
                    "height": 0.0,
                    "text": "",
                    "class": "",
                }
            ]
            self._add_label_image(
                LabelBuilder(
                    *size,
                    labels,
                    grp,
                    text_style,
                    class_=class_,
                    icon_size=icon_size,
                ),
                labelpos,
            )

        if features or class_ in decorations.needs_feature_line:
            feature_y = self._draw_feature_line(rect, grp, rect_style, lines)
            if features:
                self._draw_feature_text(
                    rect, features, class_, grp, text_style, feature_y
                )

        if DEBUG:
            self._draw_rect_helping_lines(grp, pos, size)

        return grp

    def _draw_feature_line(
        self,
        obj: base.BaseElement,
        group: container.Group | None,
        objstyle: style.Styling | None,
        lines_data: LinesData | None = None,
    ) -> shapes.Line | None:
        """Draw a Line on the given object."""
        x, y = obj.attribs["x"], obj.attribs["y"]
        w = obj.attribs["width"]

        if lines_data is None:
            height_level: float | int = decorations.feature_space
        else:
            height_level = lines_data.text_height + 10.0

        line = self.__drawing.line(
            start=(x, y + height_level),
            end=(x + w, y + height_level),
            stroke=getattr(objstyle, "stroke", None),
        )
        if group is not None:
            group.add(line)
        return y + height_level

    def _draw_feature_text(
        self,
        obj: base.BaseElement,
        features: cabc.Sequence[str],
        class_: str,
        group: container.Group,
        labelstyle: style.Styling,
        y: int | float | None = None,
    ) -> None:
        """Draw features text on given object."""
        x = obj.attribs["x"]
        y = y or obj.attribs["y"] + decorations.feature_space
        w, h = obj.attribs["width"], obj.attribs["height"]
        for feat in features:
            label: LabelDict = {
                "x": x + decorations.feature_space / 2,
                "y": y,
                "width": w - decorations.feature_space / 2,
                "height": h - decorations.feature_space,
                "class": "Features",
                "text": chelpers.flatten_html_string(feat),
            }
            lines = self._draw_label(
                LabelBuilder(
                    w,
                    h,
                    [label],
                    group,
                    class_=f"{class_}Feature",
                    labelstyle=labelstyle,
                    y_margin=5,
                    icon=True,
                    alignment="left",
                )
            )
            if lines:
                y += lines.text_height

    def _draw_label(self, builder: LabelBuilder) -> LinesData | None:
        """Draw label text on given object and return the label's group."""
        if not builder.labels:
            return None
        builder.icon &= diagram.has_icon(builder.class_ or "")
        text = self._make_text(builder)
        lines = None
        if not text.elements:
            lines = render_hbounded_lines(builder, builder.icon)
            x, y = get_label_position(builder, lines)
            lines.min_x = x
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
                self._add_label_image(builder, icon_pos)
        return lines

    def _make_text(self, builder: LabelBuilder) -> svgtext.Text:
        """Return a text element and add it to the builder group."""
        first_label = builder.labels[0]
        assert isinstance(first_label["x"], int | float)
        assert isinstance(first_label["y"], int | float)
        assert isinstance(first_label["width"], int | float)
        assert isinstance(first_label["height"], int | float)
        assert isinstance(first_label["text"], str)
        textattrs = {
            "text": "",
            "insert": (first_label["x"], first_label["y"]),
            "text_anchor": builder.text_anchor,
            "dominant_baseline": "middle",
        }
        if "class" in first_label:
            textattrs["class_"] = first_label["class"]

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

        params = {"xml:space": "preserve"}
        text = self.__drawing.text(
            **textattrs, **builder.labelstyle._to_dict()
        )
        builder.group.add(text)
        if transform:
            text.add(
                svgtext.TSpan(
                    insert=(x, y), text=first_label["text"], **params
                )
            )
        return text

    def _add_label_image(
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

    def _get_port_transformation(
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

    def _add_port(
        self,
        pos: tuple[float, float],
        size: tuple[float, float],
        text_style: style.Styling,
        parent_id: str | None,
        *,
        class_: str,
        context_: cabc.Sequence[str] = (),
        obj_style: style.Styling,
        labels: list[LabelDict] | None = None,
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
                    transform=self._get_port_transformation(
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
                    transform=self._get_port_transformation(
                        pos, size, class_, parent_id
                    ),
                    **obj_style._to_dict(),
                )
            )

        if labels:
            self._draw_label(
                LabelBuilder(
                    decorations.max_label_width,
                    math.inf,
                    labels,
                    grp,
                    class_="Annotation",
                    labelstyle=text_style,
                    text_anchor="middle",
                    y_margin=0,
                    icon=False,
                )
            )

        return grp

    def _deploy_defs(self, styling: style.Styling) -> None:
        defs_ids = {d.attribs.get("id") for d in self.__drawing.defs.elements}
        for attr in styling:
            val = getattr(styling, attr)
            if isinstance(val, cabc.Iterable) and not isinstance(
                val, str | diagram.RGB
            ):
                grad_id = styling._generate_id("CustomGradient", val)
                if grad_id not in defs_ids:
                    gradient = symbols._make_lgradient(
                        grad_id, stop_colors=val
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
                factory = decorations.marker_factories[marker]
                assert isinstance(factory, decorations.MarkerFactory)
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
                markstyle.pop("stroke-dasharray", None)
                markstyle.pop("fill", None)
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
        label_: str = "",
        floating_labels_: list[LabelDict] | None = None,
        id_: str | None = None,
        class_: str,
        obj_style: style.Styling,
        text_style: style.Styling,
    ):
        del label_  # Symbol labels always in floating_labels!
        assert isinstance(floating_labels_, list | dict | type(None))
        pos = (x_ + 0.5, y_ + 0.5)
        size = (width_, height_)
        if (
            class_ not in self.deco_cache
            and class_ not in decorations.all_ports
        ):
            self._add_decofactory(class_)

        if class_ in decorations.all_ports:
            grp = self._add_port(
                pos,
                size,
                text_style,
                parent_,
                class_=class_,
                context_=context_,
                obj_style=obj_style,
                labels=floating_labels_,
                id_=id_,
            )
            self.__drawing.add(grp)
            return

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
        if floating_labels_:
            label_width: int | float = decorations.min_symbol_width
            label_height = 35.0
            for label in floating_labels_:
                label["class"] = "Annotation"
                label_width = max(label_width, label["width"])
                label_height = max(label_height, label["height"])

            self._draw_label(
                LabelBuilder(
                    label_width,
                    label_height,
                    floating_labels_,
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
        label_: str = "",
        floating_labels_: list[LabelDict] | None = None,
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
        labels: list[LabelDict] = []
        if label_:
            max_text_width = (
                width_ - decorations.icon_size - decorations.icon_padding
            )
            if not children_ and class_ not in decorations.always_top_label:
                label_extent = chelpers.get_text_extent(label_, max_text_width)
                y_ += (height_ - label_extent[1]) / 2
            labels.append(
                {
                    "x": x_,
                    "y": y_,
                    "width": width_,
                    "height": height_,
                    "text": label_,
                    "class": class_ or "Box",
                }
            )

        for label in floating_labels_ or []:
            label["class"] = class_ or "Box"
            labels.append(label)

        grp = self._add_rect(
            pos,
            size,
            rect_style,
            class_=class_,
            context_=context_,
            id_=id_,
            labels=labels,
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
        label_: str,
        floating_labels_: list[LabelDict],
        id_: str,
        class_: str,
        context_: cabc.Sequence[str] = (),
        obj_style: style.Styling,
        text_style: style.Styling,
    ) -> container.Group:
        grp = self._draw_box(
            x_=x_,
            y_=y_,
            width_=width_,
            height_=height_,
            label_=label_,
            id_=id_,
            class_=class_,
            context_=context_,
            obj_style=obj_style,
            text_style=text_style,
        )
        for label in floating_labels_:
            label["class"] = "Annotation"

        self._draw_label(
            LabelBuilder(
                width_,
                height_,
                floating_labels_,
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
        labels_: cabc.Sequence[LabelDict] = (),
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
            d=["M", *points], class_="Edge", **obj_style._to_dict()
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
                y_margin=3,
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
        if diagram.has_icon(class_):
            additional_space = decorations.icon_size + decorations.icon_padding
            label["width"] += additional_space + 2
            label["x"] -= additional_space / 2

        self._draw_label(
            LabelBuilder(
                label["width"],
                label["height"],
                [label],
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
        return self.__drawing.line(
            start=(x1, y1), end=(x2, y2), **obj_style._to_dict()
        )

    def _draw_rect_helping_lines(
        self,
        grp: container.Group,
        pos: tuple[float, float],
        size: tuple[float, float],
    ) -> None:
        linestyle = style.Styling(
            self.diagram_class,
            "Edge.Debug",
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
        try:
            symbol, dependencies = diagram.get_svg_symbol(name)
        except ValueError:
            symbol, dependencies = diagram.get_svg_symbol("Error")
        self.__drawing.defs.add(symbol)
        for dep in dependencies:
            if dep not in self.deco_cache:
                self._add_decofactory(dep)

        self.deco_cache.add(name)

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


@dataclasses.dataclass
class LabelBuilder:
    """Helper data-class for building labels."""

    rect_width: int | float
    rect_height: int | float
    labels: list[LabelDict]
    group: container.Group
    labelstyle: style.Styling
    class_: str | None = None
    y_margin: int | float = 0
    text_anchor: str = "start"
    icon: bool = True
    icon_size: float | int = decorations.icon_size
    alignment: helpers.AlignmentLiteral = "center"


@dataclasses.dataclass
class LinesData:
    """Helper data-tuple for rendering text-lines from labels."""

    lines: list[str]
    line_height: float
    text_height: float
    margin: float
    max_line_width: float
    min_x: float | None = None

    def __len__(self) -> int:
        return len(self.lines)

    def __iter__(self) -> cabc.Iterator[str]:
        return iter(self.lines)

    @t.overload
    def __getitem__(self, index: int) -> str: ...
    @t.overload
    def __getitem__(self, index: slice) -> list[str]: ...
    def __getitem__(self, index: int | slice) -> str | list[str]:
        return self.lines[index]

    def __bool__(self) -> bool:
        return bool(self.lines)


def render_hbounded_lines(
    builder: LabelBuilder, render_icon: bool
) -> LinesData:
    """Return Lines data to render a label."""
    lines_to_render: list[str] = []
    max_text_width = 0.0
    for label in builder.labels:
        (
            lines,
            label_margin,
            line_width,
        ) = helpers.check_for_horizontal_overflow(
            label["text"],
            builder.rect_width,
            decorations.icon_padding if render_icon else 0,
            builder.icon_size if render_icon else 0,
            builder.alignment,
        )
        lines_to_render += helpers.check_for_vertical_overflow(
            lines, builder.rect_height, line_width
        )
        max_text_width = max(max_text_width, line_width)

    line_height = max(j for _, j in map(chelpers.extent_func, lines_to_render))
    text_height = line_height * len(lines_to_render)
    return LinesData(
        lines_to_render, line_height, text_height, label_margin, max_text_width
    )


def get_label_position(
    builder: LabelBuilder, lines: LinesData
) -> diagram.Vector2D:
    """Calculate the label positions."""
    icon_size = (builder.icon_size + decorations.icon_padding) * builder.icon
    assert builder.labels
    assert lines

    for label in builder.labels:
        label_height = chelpers.extent_func(label["text"])[1]
        dominant_baseline_adjust = label_height / 2
        if builder.text_anchor == "start":
            label["x"] += lines.margin + icon_size / 2
        else:
            label["x"] += (label["width"] + icon_size) / 2

        label["y"] += dominant_baseline_adjust + builder.y_margin

    if DEBUG:
        builder.group.add(
            shapes.Circle(
                center=(builder.labels[0]["x"], builder.labels[0]["y"]),
                r=3,
                fill="red",
            ),
        )
    min_x = min(label["x"] for label in builder.labels)
    return diagram.Vector2D(min_x, builder.labels[0]["y"])


def get_label_icon_position(
    builder: LabelBuilder, lines: LinesData
) -> diagram.Vector2D:
    """Calculate the icon's position."""
    label = builder.labels[0]
    icon_y = label["y"] - builder.icon_size / 2
    if lines.text_height > lines.line_height:
        offset = lines.text_height if len(lines) > 2 else lines.line_height
        icon_y += offset / 2.75
        if label["class"] == "Annotation":
            icon_y -= decorations.icon_padding

    assert lines.min_x is not None
    icon_x = lines.min_x - builder.icon_size - decorations.icon_padding
    if builder.text_anchor == "middle":
        icon_x -= (
            lines.max_line_width / chelpers.LABEL_WIDTH_PADDING_FACTOR
        ) / 2 - 2

    if label["class"] == "Annotation":
        icon_x -= decorations.icon_padding

    if DEBUG:
        builder.group.add(
            shapes.Circle(
                center=(icon_x, icon_y),
                r=3,
                fill="blue",
            ),
        )
    return diagram.Vector2D(icon_x, icon_y)
