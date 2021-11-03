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
"""Custom extensions to the svgwrite ``Drawing`` object."""
from __future__ import annotations

import collections.abc as cabc
import logging
import os
import re
import typing as t

from svgwrite import base, container, drawing, shapes
from svgwrite import text as svgtext

from capellambse import helpers as chelpers

from . import decorations, generate, helpers, style

LOGGER = logging.getLogger(__name__)
DEBUG = "CAPELLAMBSE_SVG_DEBUG" in os.environ


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


# FIXME: refactor this, so a Drawing contains an "svg drawing". Always prefer composition over inheritance.
class Drawing(drawing.Drawing):
    """The main container that stores all svg elements."""

    def __init__(self, metadata: generate.DiagramMetadata):
        superparams = {
            "filename": f"{metadata.name}.svg",
            "size": metadata.size,
            "viewBox": metadata.viewbox,
        }
        if metadata.class_:
            superparams["class_"] = re.sub(r"\s+", "", metadata.class_)

        super().__init__(**superparams)
        self.diagram_class = metadata.class_
        self.stylesheet = self.make_stylesheet()
        self.obj_cache: dict[str | None, t.Any] = {}
        self.requires_deco_patch = decorations.needs_patch.get(
            self.diagram_class, {}
        )
        self.add_backdrop(pos=metadata.pos, size=metadata.size)

    def add_backdrop(
        self, pos: tuple[float, float], size: tuple[float, float]
    ) -> None:
        """Add a white background rectangle to the drawing."""
        self.__backdrop = self.rect(
            insert=pos,
            size=size,
            fill="white",
            stroke="none",
        )
        self.add(self.__backdrop)

    def make_stylesheet(self) -> style.SVGStylesheet:
        """Return created stylesheet and add sheet and decorations to defs."""
        stylesheet = style.SVGStylesheet(class_=self.diagram_class)
        self.defs.add(stylesheet.sheet)
        for name in stylesheet.static_deco:
            self.defs.add(decorations.deco_factories[name]())

        for grad in stylesheet.yield_gradients():
            self.defs.add(grad)

        return stylesheet

    def __repr__(self) -> str:
        return super()._repr_svg_()

    def add_rect(
        self,
        pos: tuple[float, float],
        size: tuple[float, float],
        rectstyle: cabc.Mapping[str, style.Styling],
        *,
        class_: str = "",
        label: LabelDict | None = None,
        features: cabc.Sequence[str] = (),
        id_: str | None = None,
        children: bool = False,
    ) -> container.Group:
        """Add a rectangle with auto-aligned text to the group."""
        grp: container.Group = self.g(class_=f"Box {class_}", id_=id_)
        text_style = rectstyle.get("text_style")
        rect_style = rectstyle.get("obj_style")
        transform = chelpers.get_transformation(class_, pos, size)
        rectparams = {
            "insert": pos,
            "size": size,
            "class_": class_,
            **transform,
        }
        if rect_style:
            rectparams["style"] = rect_style[""]

        rect: shapes.Rect = self.rect(**rectparams)
        grp.add(rect)

        if features:
            self._draw_feature_line(rect, grp, rect_style)
            self._draw_feature_text(rect, features, class_, grp, text_style)

        if label:
            text_anchor = (
                "start" if class_ in decorations.start_aligned else "middle"
            )
            y_margin = None
            if children or class_ in decorations.always_top_label:
                y_margin = 5

            self._draw_box_label(
                label,
                grp,
                labelstyle=text_style,
                class_=class_,
                text_anchor=text_anchor,
                y_margin=y_margin,
            )
        elif class_ in decorations.only_icons:
            icon_size = 50
            labelpos = (
                pos[0] + (size[0] - icon_size / 4) / 2,
                pos[1] + (decorations.feature_space - 15) / 2,
            )
            self.add_label_image(grp, class_, labelpos, icon_size)

        if DEBUG:
            helping_lines = self._draw_rect_helping_lines(pos, size)
            for line in helping_lines:
                grp.add(line)

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
        style: str | None = None
        if objstyle is not None:
            style = objstyle["stroke"] if "stroke" in objstyle else None

        line = self.line(
            start=(x, y + decorations.feature_space),
            end=(x + w, y + decorations.feature_space),
            style=style,
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
        labelstyle: style.Styling | None,
    ) -> None:
        """Draw features text on given object."""
        x, y = obj.attribs["x"], obj.attribs["y"]
        w, h = obj.attribs["width"], obj.attribs["height"]
        label: LabelDict = {
            "x": x,
            "y": y + decorations.feature_space,
            "width": w,
            "height": h - decorations.feature_space,
            "class": "Features",
            "text": "\n".join(
                chelpers.flatten_html_string(feat) for feat in features
            ),
        }
        self._draw_box_label(
            label,
            group,
            class_=class_,
            labelstyle=labelstyle,
            y_margin=7,
            icon=False,
        )

    def _draw_box_label(
        self,
        label: LabelDict,
        group: container.Group,
        *,
        class_: str,
        labelstyle: style.Styling | None,
        text_anchor: str = "start",
        y_margin: int | float | None,
        icon: bool = True,
        icon_size: float | int = decorations.icon_size,
    ) -> container.Group:
        """Draw label text on given object and return calculated label position."""
        x, text_height, _, y_margin = self._draw_label(
            label,
            group,
            class_=class_,
            labelstyle=labelstyle,
            text_anchor=text_anchor,
            y_margin=y_margin,
            icon=icon,
            icon_size=icon_size,
        )

        if DEBUG:
            debug_y = int(label["y"]) + y_margin
            debug_y1 = (
                int(label["y"])
                + (int(label["height"]) - decorations.icon_size) / 2
            )
            x = (
                int(label["x"])
                + decorations.icon_size
                + 2 * decorations.icon_padding
            )
            if text_height >= decorations.icon_size:
                debug_height = text_height
            else:
                debug_height = decorations.icon_size

            bbox: LabelDict = {
                "x": x
                if text_anchor == "start"
                else x - int(label["width"]) / 2,
                "y": debug_y if debug_y <= debug_y1 else debug_y1,
                "width": label["width"],
                "height": debug_height,
            }
            labelstyle = style.Styling(
                self.diagram_class,
                "Box",
                stroke="rgb(239, 41, 41)",
                fill="none",
            )
            self._draw_label_bbox(bbox, group, "Box", obj_style=labelstyle)
            self._draw_circle(
                center_=(label["x"], label["y"]),
                radius_=3,
                obj_style=style.Styling(
                    self.diagram_class,
                    "Box",
                    fill="rgb(239, 41, 41)",
                ),
                text_style=None,
            )

        return group

    def _draw_label(
        self,
        label: LabelDict,
        group: container.Group,
        *,
        class_: str,
        labelstyle: style.Styling | None,
        text_anchor: str = "start",
        icon: bool = True,
        icon_size: float | int = decorations.icon_size,
        y_margin: int | float | None,
    ) -> tuple[float, float, float, float | int]:
        assert isinstance(label["x"], (int, float))
        assert isinstance(label["y"], (int, float))
        assert isinstance(label["width"], (int, float))
        assert isinstance(label["height"], (int, float))
        assert "text" not in label or isinstance(label["text"], str)

        text = self.text(
            text="",
            insert=(label["x"], label["y"]),
            class_=label["class"],
            text_anchor=text_anchor,
            dominant_baseline="middle",
            style=labelstyle[""],  # type: ignore[index]  # FIXME: What does this mean?
        )
        group.add(text)
        render_icon = False
        max_text_width = label["width"]
        if f"{class_}Symbol" in decorations.deco_factories and icon:
            render_icon = True

        (
            lines,
            label_margin,
            max_text_width,
        ) = helpers.check_for_horizontal_overflow(
            str(label["text"]),
            label["width"],
            decorations.icon_padding if render_icon else 0,
            icon_size if render_icon else 0,
        )
        lines_to_render = helpers.check_for_vertical_overflow(
            lines, label["height"], max_text_width
        )
        line_height = max(
            j for _, j in map(chelpers.extent_func, lines_to_render)
        )
        text_height = line_height * len(lines_to_render)
        max_line_width = max(
            w for w, _ in map(chelpers.extent_func, lines_to_render)
        )
        assert max_text_width >= max_line_width
        if text_anchor == "start":
            x = (
                label["x"]
                + label_margin
                + (icon_size + decorations.icon_padding) * render_icon
            )
            icon_x = label["x"] + label_margin
        else:
            x = label["x"] + label["width"] / 2
            icon_x = x - max_line_width / 2 - icon_size

        dominant_baseline_adjust = (
            chelpers.extent_func(lines_to_render[0])[1] / 2
        )
        if y_margin is None:
            y_margin = (label["height"] - text_height) / 2

        y = label["y"] + y_margin + dominant_baseline_adjust
        for line in lines_to_render:
            text.add(
                svgtext.TSpan(
                    insert=(x, y), text=line, **{"xml:space": "preserve"}
                )
            )
            y += line_height

        if render_icon:
            icon_y = label["y"] + y_margin + (text_height - icon_size) / 2
            if icon_x < label["x"] - 2 and label["class"] != "Annotation":
                icon_x = label["x"] - 2

            self.add_label_image(group, class_, (icon_x, icon_y), icon_size)

        return x, text_height, max_line_width, y_margin

    def add_label_image(
        self,
        group: container.Group,
        class_: str | None,
        pos: tuple[float, float],
        icon_size: float | int = decorations.icon_size,
    ) -> None:
        """Add label svgobject to given group."""
        if class_ is None:
            class_ = "Error"

        group.add(
            self.use(
                href=f"#{class_}Symbol",
                insert=pos,
                size=(icon_size, icon_size),
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

        return "rotate({} {} {})".format(angle, x + w / 2, y + h / 2)

    def add_port(
        self,
        pos: tuple[float, float],
        size: tuple[float, float],
        text_style: style.Styling,
        parent_id: str | None,
        *,
        class_: str,
        label: LabelDict | None = None,
        id_: str | None = None,
    ) -> container.Group:
        grp = self.g(class_=f"Box {class_}", id_=id_)
        if class_ in decorations.all_directed_ports:
            port_id = "#ErrorSymbol"
            if class_ in decorations.function_ports:
                port_id = "#PortSymbol"
            elif class_ in decorations.component_ports:
                port_id = "#ComponentPortSymbol"

            grp.add(
                self.use(
                    href=port_id,
                    insert=pos,
                    size=size,
                    transform=self.get_port_transformation(
                        pos, size, class_, parent_id
                    ),
                    class_=class_,
                )
            )
        else:
            grp.add(
                self.rect(
                    insert=pos,
                    size=size,
                    class_=class_,
                    transform=self.get_port_transformation(
                        pos, size, class_, parent_id
                    ),
                )
            )

        if label is not None:
            self._draw_label(
                label,
                grp,
                class_="Annotation",
                labelstyle=text_style,
                text_anchor="middle",
                y_margin=0,
                icon=False,
            )

        return grp

    def draw_object(self, obj: cabc.Mapping[str, t.Any]) -> None:
        """Draw an object into this drawing.

        Parameters
        ----------
        obj
            The (decoded) JSON-dict of a single diagram object.
        """
        try:
            drawfunc: t.Any = getattr(self, f'_draw_{obj["type"]}')
        except AttributeError:
            raise ValueError(f'Invalid object type: {obj["type"]}') from None

        objparams = {
            f"{k}_": v for k, v in obj.items() if k not in {"type", "style"}
        }
        if obj["class"] in decorations.all_ports:
            obj["type"] = "box"  # type: ignore[index]  # FIXME: *HACK* should actually copy the object before modifying

        class_: str = obj["type"].capitalize() + (
            f".{obj['class']}" if "class" in obj else ""
        )
        obj_style = style.Styling(
            self.diagram_class,
            class_,
            **{k: v for k, v in obj.get("style", {}).items() if "_" not in k},
        )
        text_style = style.Styling(
            self.diagram_class,
            class_,
            "text",
            **{
                k[len("text_") :]: v
                for k, v in obj.get("style", {}).items()
                if k.startswith("text_")
            },
        )

        self.obj_cache[obj["id"]] = obj

        drawfunc(**objparams, obj_style=obj_style, text_style=text_style)

        obj_style._deploy_defs(self)
        text_style._deploy_defs(self)

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
        del obj_style, context_  # FIXME Add context to SVG
        del kw  # Dismiss additional info from json
        assert isinstance(label_, (dict, type(None)))
        pos = (x_ + 0.5, y_ + 0.5)
        size = (width_, height_)

        if class_ in decorations.all_ports:
            grp = self.add_port(
                pos, size, text_style, parent_, class_=class_, label=label_
            )
        else:
            grp = self.g(class_=f"Box {class_}", id_=id_)
            grp.add(
                self.use(
                    href=f"#{class_}Symbol",
                    insert=pos,
                    size=size,
                    class_=class_,
                )
            )

        self.add(grp)

        if label_:
            self._draw_annotation(
                grp=grp, label_=label_, class_=class_, text_style=text_style
            )

    def _draw_annotation(
        self,
        *,
        grp: container.Group = None,
        label_: LabelDict,
        class_: str,
        text_style: style.Styling,
    ) -> None:
        label_["class"] = "Annotation"
        self._draw_label(
            label_,
            grp or self.elements[-1],
            class_=class_,
            labelstyle=text_style,
            text_anchor="middle",
            y_margin=0,
            icon=False,
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
        id_: str,
        class_: str,
        obj_style: style.Styling,
        text_style: style.Styling,
        **kw: t.Any,
    ) -> None:
        del context_  # FIXME Add context to SVG
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
            id_=id_,
            label=label,
            features=features_,
            children=bool(children_),
        )
        self.add(grp)

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
        obj_style: style.Styling,
        text_style: style.Styling,
        **kw: t.Any,
    ) -> None:
        del kw

        self._draw_box(
            x_=x_,
            y_=y_,
            width_=width_,
            height_=height_,
            id_=id_,
            class_=class_,
            obj_style=obj_style,
            text_style=text_style,
        )
        self._draw_annotation(
            label_=label_, class_=class_, text_style=text_style
        )

    def _draw_circle(
        self, *, center_, radius_, id_=None, class_=None, obj_style, text_style
    ):
        del text_style  # No label for circles
        center_ = tuple(i + 0.5 for i in center_)

        grp = self.g(class_=f"Circle {class_}", id_=id_)
        grp.add(self.circle(center=center_, r=radius_, style=obj_style[""]))
        self.add(grp)

    def _draw_edge(
        self,
        *,
        points_: list[list[int]],
        label_: LabelDict | None = None,
        id_: str,
        class_: str,
        obj_style: style.Styling,
        text_style: style.Styling,
        **kw,
    ):
        del kw  # Dismiss additional info from json
        points: list = [(x + 0.5, y + 0.5) for x, y in points_]
        grp = self.g(class_=f"Edge {class_}", id_=id_)
        grp.add(
            self.path(d=["M"] + points, class_="Edge", style=obj_style[""])
        )

        # Received text space doesn't allow for anything else than the text
        if label_ is not None:
            label_["class"] = "Annotation"

            self._draw_label_bbox(label_, grp, "AnnotationBB")
            self._draw_edge_label(
                label_,
                grp,
                labelstyle=text_style,
                text_anchor="middle",
                class_=class_,
                y_margin=0,
            )

        self.add(grp)

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
        if class_ in self.requires_deco_patch:
            class_ = self.requires_deco_patch[class_]

        if f"{class_}Symbol" in decorations.deco_factories:
            additional_space = (
                decorations.icon_size + 2 * decorations.icon_padding
            )
            label["width"] += additional_space + 2
            label["x"] -= additional_space / 2

        self._draw_label(
            label,
            group,
            class_=class_,
            labelstyle=labelstyle,
            text_anchor=text_anchor,
            y_margin=y_margin,
        )

        return group

    def _draw_label_bbox(
        self,
        label: LabelDict,
        group: container.Group | None = None,
        class_: str | None = None,
        obj_style: style.Styling | None = None,
    ) -> None:
        """Draw a bounding box for given label."""
        if DEBUG:
            if obj_style is not None:
                setattr(obj_style, "stroke", "rgb(239, 41, 41);")
            else:
                obj_style = style.Styling(
                    self.diagram_class,
                    "AnnotationBB",
                    stroke="rgb(239, 41, 41);",
                )

        bbox = self.rect(
            insert=(label["x"], label["y"]),
            size=(label["width"], label["height"]),
            class_=class_,
            style=obj_style,
        )
        if group is None:
            return bbox

        return group.add(bbox)

    def _draw_line(
        self,
        data: dict[str, float | int],
        group: container.Group | None = None,
        obj_style: style.Styling | None = None,
    ) -> shapes.Line | None:
        """Draw a Line on the given object."""
        x1, y1 = data["x"], data["y"]
        x2 = data.get("x1") or data["x"] + data["width"]
        y2 = data.get("y1") or data["y"]
        line = self.line(start=(x1, y1), end=(x2, y2), style=obj_style)
        if group is None:
            return line

        return group.add(line)

    def _draw_rect_helping_lines(
        self,
        rect_pos: tuple[float, float],
        rect_size: tuple[float, float],
    ):
        linestyle = style.Styling(
            self.diagram_class,
            "Edge",
            **{
                "stroke": "rgb(239, 41, 41)",
                "stroke-dasharray": "5",
            },
        )
        lines = []
        lines.append(
            self._draw_line(
                {
                    "x": rect_pos[0] + rect_size[0] / 2,
                    "y": rect_pos[1],
                    "x1": rect_pos[0] + rect_size[0] / 2,
                    "y1": rect_pos[1] + rect_size[1],
                },
                obj_style=linestyle,
            )
        )
        lines.append(
            self._draw_line(
                {
                    "x": rect_pos[0],
                    "y": rect_pos[1] + rect_size[1] / 2,
                    "width": rect_size[0],
                },
                obj_style=linestyle,
            )
        )
        return lines
