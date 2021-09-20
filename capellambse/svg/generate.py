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
from __future__ import annotations

import dataclasses
import json
import typing as t


class SVGDiagram:
    """An SVG diagram that can be drawn on and serialized.

    SVG diagram object that takes the ``metadata`` of a diagram via the
    :class:`DiagramMetadata` and a list of objects that are dictionaries
    describing the components to be drawn on the diagram canvas of type
    :class:`Drawing`.

    Example of expected json-file/string::

        {
            "name": "FA00 - Functional Architecture Example",
            "class": "LogicalArchitectureBlank",
            "x": 10,
            "y": 20,
            "width": 100,
            "height": 200,
            "contents": [
                {
                    "type": "box",
                    "id": "_ZNVPYDHuEeqOg4absf8kjA",
                    "class": "LogicalFunction",
                    "x": 150,
                    "y": 130,
                    "width": 101,
                    "height": 101,
                    "label": "example label"
                }
            ]
        }
    """

    def __init__(
        self,
        metadata: DiagramMetadata,
        objects: t.Sequence[t.Mapping[str, str | int | float]],
    ) -> None:
        self.drawing = Drawing(metadata)
        for obj in objects:
            self.draw_object(obj)

    @classmethod
    def from_json(cls, jsonstring: str) -> SVGDiagram:
        """Create an SVGDiagram from the given JSON string.

        Parameters
        ----------
        jsonstring
            Json/dictionary in ``str`` format

        Returns
        -------
        diagram
            SVG diagram object
        """
        jsondict = json.loads(jsonstring)
        metadata = DiagramMetadata.from_dict(jsondict)
        return cls(metadata, jsondict["contents"])

    @classmethod
    def from_json_path(cls, path: str) -> SVGDiagram:
        """Create an SVGDiagram from the given JSON file.

        Parameters
        ----------
        path
            path to .json file

        Returns
        -------
        diagram
            SVG diagram object
        """
        with open(path, "r") as file:
            conf = file.read()

        return cls.from_json(conf)

    def draw_object(self, obj: t.Mapping[str, str | int | float]) -> None:
        self.drawing.draw_object(obj)

    def save_drawing(self, pretty: bool = False, indent: int = 2) -> None:
        self.drawing.save(pretty=pretty, indent=indent)

    def to_string(self) -> str:
        return self.drawing.tostring()


@dataclasses.dataclass
class DiagramMetadata:
    """Holds metadata about a diagram.

    The metadata of a diagram includes the diagram-name, ``(x, y)``
    position, ``(w, h)`` size, the viewbox string and the diagram class,
    e.g. ``LogicalArchitectureBlank``.
    """

    def __init__(
        self,
        pos: t.Tuple[float, float],
        size: t.Tuple[float, float],
        name: str,
        class_: str,
    ) -> None:
        # Add padding to viewbox to account for drawn borders
        self.pos: t.Tuple[float, float] = tuple(i - 10 for i in pos)
        self.size: t.Tuple[float, float] = tuple(i + 20 for i in size)
        self.viewbox = " ".join(map(str, self.pos + self.size))
        self.class_ = class_
        self.name = name

    @classmethod
    def from_dict(
        cls, data: t.Mapping[str, str | int | float]
    ) -> DiagramMetadata:
        name = data.get("name")
        if not isinstance(name, str):
            raise TypeError("No diagram name defined.")
        if not isinstance(data.get("class"), str):
            raise TypeError(f"No diagram class defined for {name}")
        for attr in ["x", "y", "width", "height"]:
            if not isinstance(data[attr], (int, float)):
                raise TypeError(
                    f"{data[attr]} needs to be either integer or float."
                )
        return cls(
            (data["x"], data["y"]),
            (data["width"], data["height"]),
            name,
            data["class"],
        )


from .drawing import Drawing
