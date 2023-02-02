# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Module that handles converting diagrams to the intermediary JSON format."""
from __future__ import annotations

__all__ = ["DiagramJSONEncoder"]

import collections.abc as cabc
import json
import typing as t

from capellambse import diagram

_CSSStyle = t.Union[diagram.RGB, t.Iterable[t.Union[diagram.RGB, str]], str]


class DiagramJSONEncoder(json.JSONEncoder):
    """JSON encoder that knows how to handle AIRD diagrams."""

    def default(self, o: object) -> object:
        if isinstance(o, diagram.Diagram):
            return self.__encode_diagram(o)
        if isinstance(o, diagram.Box):
            return self.__encode_box(o)
        if isinstance(o, diagram.Edge):
            return self.__encode_edge(o)
        if isinstance(o, diagram.Circle):
            return self.__encode_circle(o)
        if isinstance(o, diagram.RGB):
            return str(o)
        if isinstance(o, cabc.Sequence):
            return list(o)
        return super().default(o)

    @staticmethod
    def __encode_diagram(o: diagram.Diagram) -> object:
        return {
            "name": o.name,
            "uuid": o.uuid,
            "class": o.styleclass,
            "x": _intround(o.viewport.pos.x) if o.viewport is not None else 0,
            "y": _intround(o.viewport.pos.y) if o.viewport is not None else 0,
            "width": (
                _intround(o.viewport.size.x) if o.viewport is not None else 0
            ),
            "height": (
                _intround(o.viewport.size.y) if o.viewport is not None else 0
            ),
            "contents": [e for e in o if not e.hidden],
        }

    @staticmethod
    def __encode_box(o: diagram.Box) -> object:
        children = [
            c.uuid
            for c in o.children
            if isinstance(c, diagram.Box) and not c.port
        ]
        ports = [p.uuid for p in o.children if p.port]
        jsonobj: dict[str, object] = {
            "type": o.JSON_TYPE,
            "id": o.uuid,
            "class": o.styleclass,
            "x": _intround(o.pos.x),
            "y": _intround(o.pos.y),
            "width": _intround(o.size.x),
            "height": _intround(o.size.y),
            "context": sorted(o.context),
        }
        if o.label is not None and not o.hidelabel:
            jsonobj["label"] = _encode_label(o.label)
        if o.styleoverrides:
            jsonobj["style"] = _encode_styleoverrides(o.styleoverrides)
        if o.features:
            jsonobj["features"] = o.features
        if o.parent:
            jsonobj["parent"] = o.parent.uuid
        if children:
            jsonobj["children"] = children
        if ports:
            jsonobj["ports"] = ports

        return jsonobj

    @staticmethod
    def __encode_edge(o: diagram.Edge) -> object:
        jsonobj: dict[str, object] = {
            "type": o.JSON_TYPE,
            "id": o.uuid,
            "class": o.styleclass,
            "points": [[_intround(x), _intround(y)] for x, y in o.points],
            "labels": [_encode_label(i) for i in o.labels if not i.hidden],
        }

        if o.styleoverrides:
            jsonobj["style"] = _encode_styleoverrides(o.styleoverrides)
        return jsonobj

    @staticmethod
    def __encode_circle(o: diagram.Circle) -> object:
        jsonobj: dict[str, object] = {
            "type": o.JSON_TYPE,
            "id": o.uuid,
            "class": o.styleclass,
            "center": [_intround(p) for p in o.center],
            "radius": _intround(o.radius),
        }
        if o.styleoverrides:
            jsonobj["style"] = _encode_styleoverrides(o.styleoverrides)
        return jsonobj


def _encode_label(o: diagram.Box | str) -> object:
    if isinstance(o, str):
        return o
    return {
        "x": _intround(o.pos.x),
        "y": _intround(o.pos.y),
        "width": _intround(o.size.x),
        "height": _intround(o.size.y),
        "text": o.label,
    }


def _intround(val: float | int) -> int:
    return int(val + 0.5)


def _encode_styleoverrides(
    overrides: cabc.Mapping[str, _CSSStyle]
) -> dict[str, object]:
    return {k: _encode_style(v) for k, v in overrides.items()}


def _encode_style(style: _CSSStyle) -> object:
    if isinstance(style, diagram.RGB):
        return str(style)
    if isinstance(style, (list, tuple)):
        return [_encode_style(i) for i in style]
    return style
