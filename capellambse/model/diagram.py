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
"""Classes that allow access to diagrams in the model."""
from __future__ import annotations

import abc
import base64
import importlib.metadata as imm
import logging
import operator
import traceback
import typing as t
import uuid

import markupsafe

import capellambse.svg

from .. import aird
from . import common as c
from . import modeltypes

DiagramConverter = t.Callable[[aird.Diagram], t.Any]
LOGGER = logging.getLogger(__name__)


class UnknownOutputFormat(ValueError):
    """An unknown output format was requested for the diagram."""


class AbstractDiagram(metaclass=abc.ABCMeta):
    """Abstract superclass of model diagrams."""

    uuid: str
    """Unique ID of this diagram."""
    name: str
    """Human-readable name for this diagram."""
    target: c.GenericElement
    """This diagram's "target".

    The target of a diagram is usually:

    *   The model element which is the direct parent of all visible
        nodes **OR**
    *   The only top-level element in the diagram **OR**
    *   The element which is considered to be the "element of interest".
    """

    _model: capellambse.MelodyModel
    _render: aird.Diagram
    _error: BaseException

    def __init__(self, model: capellambse.MelodyModel) -> None:
        self._model = model

    def __dir__(self) -> list[str]:
        return dir(type(self)) + [
            f"as_{i.name}"
            for i in imm.entry_points()["capellambse.diagram.formats"]
        ]

    def __getattr__(self, attr: str) -> t.Any:
        if attr.startswith("as_"):
            fmt = attr[len("as_") :]
            try:
                return self.render(fmt)
            except UnknownOutputFormat:
                raise
            except Exception as err:  # pylint: disable=broad-except
                if hasattr(self, "_error") and err is self._error:
                    err_img = self._render
                else:
                    err_img = self.__create_error_image("render", err)
                assert err_img is not None
                return _find_format_converter(fmt)(err_img)
        return getattr(super(), attr)

    def __repr__(self) -> str:
        return f"<Diagram {self.name!r}>"

    def __html__(self) -> markupsafe.Markup:
        return (
            markupsafe.Markup("<figure>")
            + markupsafe.Markup(self.render("svg"))
            + markupsafe.Markup("<figcaption>")
            + self.name
            + markupsafe.Markup("</figcaption></figure>")
        )

    def _repr_svg_(self):
        return self.render("svg")

    @property
    def nodes(self) -> c.MixedElementList:
        """Return a list of all nodes visible in this diagram."""
        allids = {e.uuid for e in self.render(None)}
        assert None not in allids
        elems = []
        for elemid in allids:
            assert elemid is not None
            try:
                elem = self._model._loader[elemid]
                elem = next(elem.iterchildren("target"))
                elem = self._model._loader.follow_link(
                    elem, elem.attrib["href"]
                )
            except (KeyError, StopIteration):  # pragma: no cover
                continue
            else:
                # Filter out visual-only elements that live in the
                # .aird / .airdfragment files
                frag = self._model._loader.find_fragment(elem)
                if frag.suffix not in {".aird", ".airdfragment"}:
                    elems.append(elem)

        return c.MixedElementList(self._model, elems, c.GenericElement)

    @t.overload
    def render(self, fmt: None) -> aird.Diagram:
        ...

    @t.overload
    def render(self, fmt: str) -> t.Any:
        ...

    def render(self, fmt: str | None) -> t.Any:
        """Render the diagram in the given format."""
        conv: t.Any
        if fmt is None:
            conv = lambda i: i
        else:
            conv = _find_format_converter(fmt)

        try:
            return self.__load_cache(conv)
        except KeyError:
            pass
        return conv(self.__render_fresh())

    @abc.abstractmethod
    def _create_diagram(self) -> aird.Diagram:
        """Perform the actual rendering of the diagram.

        This method should only be called by the public :meth:`render`
        method, as it handles caching of the results.
        """

    def __create_error_image(
        self,
        stage: str,
        error: Exception,
    ) -> aird.Diagram:
        err_name = (
            "An error occured while rendering diagram\n"
            f"{self.name!r}\n"
            f"(in stage {stage!r})"
        )
        err_msg = (
            "Please report this error to your tools and methods team,"
            " and attach the following information:"
        )
        err_trace = "".join(
            traceback.format_exception(None, error, error.__traceback__)
        )

        diag = aird.Diagram("An error occured! :(")
        err_box = aird.Box(
            (200, 0),
            (350, 0),
            label=err_name,
            uuid="error",
            styleclass="Note",
            styleoverrides={
                "fill": aird.RGB(255, 0, 0),
                "text_fill": aird.RGB(255, 255, 255),
            },
        )
        diag.add_element(err_box, extend_viewport=False)
        info_box = aird.Box(
            (200, err_box.pos.y + err_box.size.y + 10),
            (350, 0),
            label=err_msg,
            uuid="info",
            styleclass="Note",
        )
        diag.add_element(info_box, extend_viewport=False)
        trace_box = aird.Box(
            (0, info_box.pos.y + info_box.size.y + 10),
            (750, 0),
            label=err_trace,
            uuid="trace",
            styleclass="Note",
        )
        diag.add_element(trace_box, extend_viewport=False)
        diag.calculate_viewport()
        return diag

    def __load_cache(self, converter):
        try:
            cache_handler = self._model._diagram_cache
            cachedir = self._model._diagram_cache_subdir
            fromcache = converter.from_cache
            ext = converter.filename_extension
        except AttributeError:
            raise KeyError(self.uuid) from None

        try:
            with cache_handler.open(cachedir / (self.uuid + ext)) as f:
                cache = f.read()
        except FileNotFoundError:
            raise KeyError(self.uuid) from None

        return fromcache(cache)

    def __render_fresh(self):
        # pylint: disable=broad-except
        if not hasattr(self, "_render"):
            try:
                self._render = self._create_diagram()
            except Exception as err:
                self._error = err
                self._render = self.__create_error_image("parse", self._error)

        if hasattr(self, "_error"):
            raise self._error
        return self._render


class Diagram(AbstractDiagram):
    """Provides access to a single diagram."""

    uuid: str = property(operator.attrgetter("_element.uid"))  # type: ignore[assignment]
    xtype = "viewpoint:DRepresentationDescriptor"
    name: str = property(operator.attrgetter("_element.name"))  # type: ignore[assignment]
    viewpoint: str = property(operator.attrgetter("_element.viewpoint"))  # type: ignore[assignment]
    target_uuid: str = property(lambda self: self.target.uuid)  # type: ignore[assignment]
    """Obsolete."""

    _element: aird.DiagramDescriptor

    @classmethod
    def from_model(
        cls,
        model: capellambse.MelodyModel,
        descriptor: aird.DiagramDescriptor,
    ) -> Diagram:
        """Wrap a diagram already defined in the Capella AIRD."""
        self = cls.__new__(cls)
        self._model = model
        self._element = descriptor
        return self

    def __init__(self, **kw: t.Any) -> None:
        # pylint: disable=super-init-not-called
        # Do I need to explain this suppression?
        raise TypeError("Cannot create a Diagram this way")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._model is other._model and self._element == other._element

    @property
    def description(self) -> str:
        """Return the diagram description."""
        desc = self._model._loader[self.uuid].get("documentation")
        return desc and c.markuptype(desc)

    @property
    def target(self) -> c.GenericElement:  # type: ignore[override]
        return c.GenericElement.from_model(self._model, self._element.target)

    @property
    def type(self) -> modeltypes.DiagramType:
        """Return the type of this diagram."""
        sc = self._element.styleclass
        try:
            return modeltypes.DiagramType(sc)
        except ValueError:  # pragma: no cover
            LOGGER.warning("Unknown diagram type %r", sc)
            return modeltypes.DiagramType.UNKNOWN

    def _create_diagram(self) -> aird.Diagram:
        return aird.parse_diagram(self._model._loader, self._element)


class DiagramAccessor(c.Accessor):
    """Provides access to a list of diagrams below the specified viewpoint."""

    def __init__(
        self,
        viewpoint: str | None = None,
        *,
        cacheattr: str | None = None,
    ) -> None:
        super().__init__()
        self.cacheattr = cacheattr
        self.viewpoint = viewpoint

    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:  # pragma: no cover
            return self

        if self.viewpoint is None:
            descriptors = list(aird.enumerate_diagrams(obj._model._loader))
        else:
            descriptors = [
                d
                for d in aird.enumerate_diagrams(obj._model._loader)
                if d.viewpoint == self.viewpoint
            ]
        return c.CachedElementList(
            obj._model,
            descriptors,
            Diagram,
            cacheattr=self.cacheattr,
        )


class SVGFormat:
    """Convert the diagram to SVG."""

    filename_extension = ".svg"

    def __new__(cls, diagram):
        return cls.convert(diagram)

    @staticmethod
    def convert(diagram: aird.Diagram) -> str:
        return convert_svgdiagram(diagram).to_string()

    @staticmethod
    def from_cache(cache: bytes) -> str:
        return cache.decode("utf-8")


def convert_svgdiagram(
    diagram: aird.Diagram,
) -> capellambse.svg.generate.SVGDiagram:
    """Convert the diagram to a SVGDiagram."""
    jsondata = aird.DiagramJSONEncoder().encode(diagram)
    svg = capellambse.svg.generate.SVGDiagram.from_json(jsondata)
    return svg


class ConfluenceSVGFormat:
    """Convert the diagram to Confluence-style SVG."""

    filename_extension = ".svg"
    prefix = (
        f'<ac:structured-macro ac:macro-id="{uuid.uuid4()!s}" ac:name="html"'
        ' ac:schema-version="1">'
        f"<ac:plain-text-body><![CDATA["
    )
    postfix = "]]></ac:plain-text-body></ac:structured-macro>"

    def __new__(cls, diagram):
        return cls.convert(diagram)

    @classmethod
    def convert(cls, diagram: aird.Diagram) -> str:
        return "".join((cls.prefix, SVGFormat.convert(diagram), cls.postfix))

    @classmethod
    def from_cache(cls, cache: bytes) -> str:
        return "".join((cls.prefix, cache.decode("utf-8"), cls.postfix))


class SVGDataURIFormat:
    filename_extension = ".svg"
    preamble = "data:image/svg+xml;base64,"

    def __new__(cls, diagram):
        return cls.convert(diagram)

    @classmethod
    def convert(cls, diagram: aird.Diagram) -> str:
        """Convert the diagram to a ``data:`` URI containing SVG."""
        payload = SVGFormat.convert(diagram)
        b64 = base64.standard_b64encode(payload.encode("utf-8"))
        return "".join((cls.preamble, b64.decode("ascii")))

    @classmethod
    def from_cache(cls, cache: bytes) -> str:
        b64 = base64.standard_b64encode(cache)
        return "".join((cls.preamble, b64.decode("ascii")))


class SVGInHTMLIMGFormat:
    filename_extension = ".svg"

    def __new__(cls, diagram):
        return cls.convert(diagram)

    @staticmethod
    def convert(diagram: aird.Diagram) -> str:
        """Convert the diagram to an HTML ``<img>``."""
        payload = SVGDataURIFormat.convert(diagram)
        return c.markuptype(f'<img src="{payload}"/>')

    @staticmethod
    def from_cache(cache: bytes) -> str:
        payload = SVGDataURIFormat.from_cache(cache)
        return c.markuptype(f'<img src="{payload}"/>')


class JSONFormat:
    filename_extension = ".json"

    def __new__(cls, diagram):
        return cls.convert(diagram)

    @staticmethod
    def convert(diagram: aird.Diagram) -> str:
        return aird.DiagramJSONEncoder().encode(diagram)

    @staticmethod
    def from_cache(cache: bytes) -> str:
        return cache.decode("utf-8")


class PrettyJSONFormat:
    filename_extension = ".json"

    def __new__(cls, diagram):
        return cls.convert(diagram)

    @staticmethod
    def convert(diagram: aird.Diagram) -> str:
        return aird.DiagramJSONEncoder(indent=4).encode(diagram)

    @staticmethod
    def from_cache(cache: bytes) -> str:
        return cache.decode("utf-8")


def _find_format_converter(fmt: str) -> DiagramConverter:
    try:
        return next(
            i.load()
            for i in imm.entry_points()["capellambse.diagram.formats"]
            if i.name == fmt
        )
    except StopIteration:
        raise UnknownOutputFormat(
            f"Unknown image output format {fmt}"
        ) from None
