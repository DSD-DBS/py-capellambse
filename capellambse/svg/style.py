# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Stylesheet generator for SVG diagrams."""
from __future__ import annotations

import collections.abc as cabc
import io
import itertools
import logging
import operator
import re
import textwrap
import typing as t

from lxml import etree
from svgwrite import base, gradients

from capellambse import diagram

if t.TYPE_CHECKING:
    from .drawing import Drawing

logger = logging.getLogger(__name__)
RE_ELMCLASS = re.compile(r"^([A-Z][a-z_]*)(\.[A-Za-z][A-Za-z0-9_]*)?(:.+)?$")
CUSTOM_STYLE_ATTRS = {"marker-fill"}

# TODO refactor to dynamically determine needed decorations
STATIC_DECORATIONS: dict[str, tuple[str, ...]] = {
    "__GLOBAL__": (
        "ErrorSymbol",
        "RequirementSymbol",
    ),
    "Error": (),
    "Class Diagram Blank": ("ClassSymbol",),
    "Functional Chain Description": (
        "AndControlNodeSymbol",
        "IterateControlNodeSymbol",
        "OrControlNodeSymbol",
        "FunctionalExchangeSymbol",
        "FunctionSymbol",
    ),
    "Logical Architecture Blank": (
        "ComponentPortSymbol",
        "LogicalActorSymbol",
        "LogicalComponentSymbol",
        "LogicalFunctionSymbol",
        "LogicalHumanActorSymbol",
        "LogicalHumanComponentSymbol",
        "PortSymbol",
        "StickFigureSymbol",
        "FunctionalExchangeSymbol",
        "ComponentExchangeSymbol",
    ),
    "Logical Data Flow Blank": (
        "LogicalFunctionSymbol",
        "PortSymbol",
        "FunctionalExchangeSymbol",
    ),
    "Missions Capabilities Blank": (
        "CapabilitySymbol",
        "MissionSymbol",
        "SystemActorSymbol",
        "SystemComponentSymbol",
        "SystemHumanActorSymbol",
    ),
    "Mode State Machine": (
        "FinalStateSymbol",
        "InitialPseudoStateSymbol",
        "ModeSymbol",
        "StateSymbol",
        "TerminatePseudoStateSymbol",
    ),
    "Operational Capabilities Blank": (
        "EntitySymbol",
        "OperationalActorBoxSymbol",
        "OperationalCapabilitySymbol",
    ),
    "Operational Entity Blank": (
        "EntitySymbol",
        "OperationalActivitySymbol",
        "OperationalActorBoxSymbol",
        "OperationalExchangeSymbol",
    ),
    "Operational Entity Breakdown": ("OperationalActorSymbol", "EntitySymbol"),
    "Operational Process Description": (
        "AndControlNodeSymbol",
        "IterateControlNodeSymbol",
        "OperationalActivitySymbol",
        "OrControlNodeSymbol",
        "OperationalExchangeSymbol",
    ),
    "Operational Activity Interaction Blank": (
        "OperationalActivitySymbol",
        "OperationalExchangeSymbol",
    ),
    "Physical Architecture Blank": (
        "PhysicalLinkSymbol",
        "ComponentExchangeSymbol",
        "ComponentPortSymbol",
        "PortSymbol",
    ),
    "Physical Data Flow Blank": (
        "FunctionalExchangeSymbol",
        "PhysicalFunctionSymbol",
        "PortSymbol",
    ),
    "System Architecture Blank": (
        "ComponentExchangeSymbol",
        "ComponentPortSymbol",
        "FunctionalExchangeSymbol",
        "PhysicalLinkSymbol",
        "SystemActorSymbol",
        "SystemComponentSymbol",
        "SystemFunctionSymbol",
        "SystemHumanActorSymbol",
        "PortSymbol",
    ),
    "System Data Flow Blank": (
        "FunctionalExchangeSymbol",
        "PortSymbol",
        "SystemFunctionSymbol",
    ),
    "Contextual Capability": (
        "CapabilitySymbol",
        "MissionSymbol",
        "SystemActorSymbol",
        "SystemHumanActorSymbol",
    ),
}
MODIFY_STYLECLASS = {"FunctionalExchange"}


def get_symbol_styleclass(style: str | None, dstyle: str | None) -> str | None:
    if (
        style not in MODIFY_STYLECLASS
        or dstyle not in STATIC_DECORATIONS
        or style in STATIC_DECORATIONS[dstyle]
    ):
        return None

    capitals = (dstyle or "").split(" ", maxsplit=1)
    assert capitals
    layer = capitals[0]
    if style.startswith(layer):
        return None

    scapitals = re.findall(r"[A-Z][^A-Z]*", style)
    symbol = f'{layer}{"".join(scapitals[1:])}'
    if f"{symbol}Symbol" in STATIC_DECORATIONS[dstyle]:
        return symbol
    return None


class Styling:
    """Container for style attributes of svg objects.

    Notes
    -----
    Attributes containing '-' are only referenceable via getattr() or
    subscripting syntax, due to Python identifier naming rules.
    """

    _marker: bool = False

    def __init__(
        self, diagram_class: str | None, class_: str, prefix: str = "", **attr
    ):
        self._diagram_class = diagram_class
        self._class = class_
        self._prefix = prefix

        for key, val in attr.items():
            setattr(self, key, val)

    def __setattr__(self, name: str, value: t.Any) -> None:
        if not name.startswith("_"):
            name = name.replace("_", "-")
        super().__setattr__(name, value)

    def __getattribute__(self, attr: str) -> str:
        if attr in {"marker-start", "marker-end"}:
            defaultstyles = diagram.get_style(self._diagram_class, self._class)
            try:
                value = super().__getattribute__(attr)
            except AttributeError as err:
                try:
                    value = defaultstyles[self._style_name(attr)]
                except KeyError:
                    raise err from None
            try:
                stroke = self.stroke
            except AttributeError:
                stroke = (
                    defaultstyles.get(self._style_name("stroke")) or "#000"
                )
            return f'url("#{value}_{diagram.RGB.fromcss(stroke).tohex()}")'

        return super().__getattribute__(attr)

    def __bool__(self) -> bool:
        try:
            next(iter(self))
        except StopIteration:
            return False
        return True

    def __iter__(self) -> cabc.Iterator[str]:
        defaultstyles = diagram.get_style(self._diagram_class, self._class)
        for attr in ("marker-start", "marker-end"):
            if (
                not self._marker
                and not getattr(super(), attr, None)
                and self._style_name(attr) in defaultstyles
            ):
                yield attr

        yield from itertools.filterfalse(
            operator.methodcaller("startswith", "_"), dir(self)
        )

    def __getitem__(self, attrs: str | cabc.Iterable[str]) -> str | None:
        if isinstance(attrs, str):
            attrs = (attrs,) if attrs else self
        return (
            "; ".join(f"{a}: {self._to_css(getattr(self, a))}" for a in attrs)
            or None
        )

    @classmethod
    def _to_css(
        cls, value: float | int | str | diagram.RGB | cabc.Iterable | None
    ) -> float | int | str:
        if isinstance(value, (str, int, float)):
            return value
        elif value is None:
            return "none"
        elif isinstance(value, diagram.RGB):
            return f"#{value.tohex()}"
        elif isinstance(value, cabc.Iterable):
            return f'url("#{cls._generate_id("CustomGradient", value)}")'
        raise ValueError(f"Invalid styling value: {value!r}")

    @staticmethod
    def _generate_id(
        name: str, value: cabc.Iterable[str | diagram.RGB]
    ) -> str:
        """Return unqiue identifier for given css-value."""
        return "_".join(
            itertools.chain(
                (name,),
                (diagram.RGB.fromcss(v).tohex() for v in value),
            ),
        )

    def __str__(self) -> str:
        return self[""] or ""

    def _style_name(self, attr: str) -> str:
        if not self._prefix:
            return attr

        return "_".join((self._prefix, attr))


class Style(base.BaseElement):
    """An embedded cascading style sheet."""

    elementname = "style"

    def __init__(self, text: str, **extra: dict[str, t.Any]) -> None:
        """Initialize Style class.

        Parameters
        ----------
        text
            The stylesheet
        extra
            Additional attributes as keyword arguments
        """
        super().__init__(**extra)
        self.text = text

    def get_xml(self) -> etree._Element:
        xml = super().get_xml()
        xml.text = self.text
        return xml


class SVGStylesheet:
    """CSS stylesheet for SVG."""

    def __init__(self, class_: str):
        if not isinstance(class_, str):
            raise TypeError(
                f"Invalid type for class_ '{type(class_).__name__}'. This"
                " needs to be a str."
            )

        self.drawing_class = class_
        self.builder = StyleBuilder(class_)
        self.create()

    @property
    def sheet(self) -> Style:
        """Return Sheet str from builder."""
        return Style(text=self.builder.sheet.getvalue())

    def create(self) -> None:
        """Generate a stylesheet for the given drawing."""
        self.builder.write_styles()
        self.static_deco = STATIC_DECORATIONS[
            "__GLOBAL__"
        ] + STATIC_DECORATIONS.get(self.drawing_class or "", ())

    def yield_gradients(self) -> cabc.Iterator[gradients.LinearGradient]:
        """Yield an svgwrite LinearGradient for all gradients in this sheet."""
        for gradname, stopcolors in self.builder.gradients.items():
            grad = gradients.LinearGradient(
                id_=gradname, start=("0%", "0%"), end=("0%", "100%")
            )
            for offset, color in zip((0, 1), stopcolors):
                grad.add_stop_color(offset=offset, color=color)

            yield grad

    def __str__(self) -> str:
        return self.sheet.text


class StyleBuilder:
    """Helper class that bundles together all needed objects."""

    _base = textwrap.dedent(
        """\
        {cls}* {{ shape-rendering: geometricPrecision; }}
        {cls}text {{ font-family: "Segoe UI"; font-size: 8pt; }}
        {cls}g {{ cursor: pointer; }}
        {cls}g.Edge > path {{ fill: none; stroke: rgb(0, 0, 0); }}
        """
    )
    _highlight_on_hover = {
        "ComponentExchange": diagram.RGB(8, 138, 189),
        "ExchangeItemElement": diagram.RGB(0, 0, 0),
        "FIPAllocation": diagram.RGB(255, 0, 0),
        "FOPAllocation": diagram.RGB(255, 0, 0),
        "FunctionalExchange": diagram.RGB(0, 0, 255),
        "PhysicalLink": diagram.RGB(239, 41, 41),
    }

    sheet: io.StringIO
    styles: dict[str, dict[str, diagram.CSSdef]]

    def __init__(self, class_: str | None):
        self.class_ = class_
        self.sheetclass = re.sub(r"\s+", "", class_ or "")
        self.stylewriters = {
            "Box": self._write_styles_box,
            "Edge": self._write_styles_edge,
        }
        self.gradients: dict[str, str | tuple[str, ...]] = {}
        self.create()

    def write_styles(self) -> None:
        """Write edge and box styles to sheet."""
        for key, styles in self.styles.items():
            if not styles:  # pragma: no cover
                continue
            elmtype_match = RE_ELMCLASS.match(key)
            if elmtype_match is None:  # pragma: no cover
                logger.error("Invalid style key: %s", key)
                continue

            elmtype, elmclass, pseudoclass = elmtype_match.groups()
            if elmtype not in self.stylewriters:
                continue
            write_styles_real = self.stylewriters[elmtype]
            write_styles_real(elmclass or "", pseudoclass or "", styles)

    def create(self) -> None:
        """Create style builder and all needed components.

        Create sheet string buffer from _base string template.  Copy
        global styles from aird.STYLES and update with class-specific
        styles.  Write styles to sheet.
        """
        self.sheet = io.StringIO(
            self._base.format(
                cls=f".{self.sheetclass} " if self.sheetclass else ""
            )
        )
        self.sheet.seek(0, io.SEEK_END)
        self.styles = self._make_styles()

    def _make_styles(self) -> dict[str, dict[str, diagram.CSSdef]]:
        styles = diagram.STYLES["__GLOBAL__"].copy()
        try:
            deep_update_dict(
                styles, diagram.STYLES[self.class_]  # type: ignore[index]
            )
        except KeyError:
            logger.error(
                "No styling defined for diagram class %s", self.class_
            )

        return styles

    def _write_styles_box(
        self,
        elmclass: str,
        pseudo: str,
        styles: dict[str, diagram.CSSdef],
    ) -> None:
        selectors = [
            f"g.Box{elmclass}{pseudo} > {tag}" for tag in ("rect", "use")
        ]
        selector_text = f"g.Box{elmclass}{pseudo} > text"
        if "stroke" in styles:
            self._write_styledict(
                elmclass,
                f"g.Box{elmclass}{pseudo} > line",
                {"stroke": styles["stroke"]},
            )
        self._write_styles_common(elmclass, selectors, selector_text, styles)

    def _write_styles_edge(
        self,
        elmclass: str,
        pseudo: str,
        styles: dict[str, diagram.CSSdef],
    ) -> None:
        selector = f"g.Edge{elmclass}{pseudo} > path"
        selector_text = f"g.Edge{elmclass}{pseudo} > text"
        self._write_styledict(
            elmclass,
            f"g.Edge{elmclass}{pseudo} > rect",
            {"fill": None, "stroke": None},
        )
        self._write_styledict(
            elmclass,
            f"g.Circle{elmclass}{pseudo} > circle",
            {
                "fill": styles.get("stroke", diagram.RGB(0, 0, 0)),
                "stroke": None,
            },
        )

        if not pseudo and elmclass in self._highlight_on_hover:
            self._write_styledict(
                elmclass,
                f"g.Edge{elmclass}:hover > path",
                {
                    "stroke": self._highlight_on_hover[elmclass],
                    "stroke-width": 2,
                },
            )
            self._write_styledict(
                elmclass,
                f"g.Edge{elmclass}:hover > rect",
                {"stroke": self._highlight_on_hover[elmclass]},
            )
        self._write_styles_common(elmclass, selector, selector_text, styles)

    def _write_styles_common(
        self,
        elmclass: str,
        sel_obj: str | list[str],
        sel_text: str,
        allstyles: dict[str, diagram.CSSdef],
    ) -> None:
        for selector, styles in zip(
            [sel_obj, sel_text], _splitstyles(allstyles)
        ):
            if styles:
                self._write_styledict(elmclass, selector, styles)

    def _write_styledict(
        self,
        elmclass: str,
        selector: str | list[str],
        styles: dict[str, diagram.CSSdef],
    ) -> None:
        if isinstance(selector, str):
            selector = f".{self.sheetclass} {selector}"
        else:
            selector = ", ".join(f".{self.sheetclass} {i}" for i in selector)
        self.sheet.write(f"{selector} {{ ")
        self.sheet.write(
            " ".join(
                self._serialize_value(k, v, elmclass)
                for k, v in styles.items()
                if k not in CUSTOM_STYLE_ATTRS
            )
        )
        self.sheet.write(" }\n")

    def _serialize_value(
        self, key: str, value: diagram.CSSdef, class_: str
    ) -> str:
        if key in {"marker-start", "marker-end"}:
            diagram_class = self.class_
            mystyle = diagram.get_style(diagram_class, f"Edge{class_}")
            if "stroke" not in mystyle:
                mystyle["stroke"] = "#f00"

            marker_id = Styling._generate_id(
                str(value),
                [mystyle["stroke"]],
            )
            value = f"url(#{marker_id})"
        elif value is None:
            value = "none"
        elif isinstance(value, diagram.RGB):
            value = str(value)
        elif isinstance(value, cabc.Sequence) and len(value) == 2:
            gradname = f"{class_}{key.capitalize()}Gradient"
            gradcolors = tuple(str(v) for v in value)
            if gradname in self.gradients:
                assert self.gradients[gradname] == gradcolors
            else:
                self.gradients[gradname] = gradcolors
            value = f'url("#{gradname}")'
        elif not isinstance(value, (float, int, str)):
            raise ValueError(f"Invalid stylesheet value: {value}")
        return f"{key}: {value};"


def _splitstyles(
    styles: dict[str, diagram.CSSdef]
) -> tuple[dict[str, diagram.CSSdef], dict[str, diagram.CSSdef]]:
    objstyles: dict[str, diagram.CSSdef] = {}
    textstyles: dict[str, diagram.CSSdef] = {}
    for key, value in styles.items():
        if key.startswith("text_"):
            textstyles[key[len("text_") :]] = value
        else:
            objstyles[key] = value
    return objstyles, textstyles


def deep_update_dict(
    target: cabc.MutableMapping, updates: cabc.Mapping
) -> cabc.MutableMapping:
    """Apply the ``updates`` to the nested ``target`` dict recursively.

    Parameters
    ----------
    target
        The target dict, which will be modified in place.
    updates
        A dict containing the updates to apply.  If one of the values is
        the special object ``deep_update_dict.delete``, the
        corresponding key will be deleted from the target.

    Returns
    -------
    dict
        The target dict, after modifying it in place.
    """
    for key, value in list(updates.items()):
        if value is deep_update_dict.delete:  # type: ignore
            del target[key]
        elif isinstance(value, cabc.Mapping):
            target[key] = deep_update_dict(target.get(key, {}), value)
        else:
            target[key] = value
    return target


deep_update_dict.delete = object()  # type: ignore
