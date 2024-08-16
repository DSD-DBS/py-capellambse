# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Module to populate the diagram cache with native Capella diagrams."""

from __future__ import annotations

import collections
import contextlib
import datetime
import itertools
import json
import logging
import os
import pathlib
import re
import shutil
import typing as t

import lxml
from lxml import etree

import capellambse
import capellambse.model as m
from capellambse import _native, helpers
from capellambse.filehandler import local

E = lxml.builder.ElementMaker()
BAD_FILENAMES = frozenset(
    {"AUX", "CON", "NUL", "PRN"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)
CROP_MARGIN = 10.0
LOGGER = logging.getLogger(__name__)

SVG_CROP_FLAG_NAME = "CAPELLAMBSE_EXPERIMENTAL_CROP_SVG_DIAGRAM_CACHE_VIEWPORT"
"""Flag environment variable that enables experimental SVG cropping.

If set to 1, the viewBox and width/height of produced SVG images will be
cropped in order to minimize the amount of whitespace around the visible
contents.
"""


VALID_FORMATS = frozenset(
    {
        "bmp",
        "gif",
        "jpg",
        "png",
        "svg",
    }
)
VIEWPOINT_ORDER = (
    "Common",
    "Operational Analysis",
    "System Analysis",
    "Logical Architecture",
    "Physical Architecture",
)


class _NoBoundingBoxFound(Exception):
    pass


class _NoExtentsFound(Exception):
    pass


class ViewBox(t.NamedTuple):
    """Bounding box of an SVG shape."""

    x_min: float
    y_min: float
    width: float
    height: float


class Extents(t.NamedTuple):
    """Extents of an SVG shape."""

    x_min: float
    x_max: float
    y_min: float
    y_max: float


class IndexEntry(t.TypedDict):
    """An entry for the index JSON file."""

    uuid: str
    name: str
    type: m.DiagramType
    viewpoint: str
    success: bool


def export(
    capella: str,
    model: capellambse.MelodyModel,
    *,
    format: str,
    index: bool,
    force: t.Literal["exe", "docker", None],
    background: bool,
    refresh: bool = False,
) -> None:
    if model.diagram_cache is None:
        raise TypeError("No diagram cache configured for the model")
    if not isinstance(model.diagram_cache, local.LocalFileHandler):
        raise TypeError(
            "Diagram cache updates are only supported for local paths"
        )

    format = format.lower()
    if format not in VALID_FORMATS:
        supported = ", ".join(sorted(VALID_FORMATS))
        raise ValueError(
            f"Invalid image format {format!r}, supported are {supported}"
        )

    diag_cache_dir = pathlib.Path(model.diagram_cache.path)
    with contextlib.suppress(FileNotFoundError):
        shutil.rmtree(diag_cache_dir)
    diag_cache_dir.mkdir(parents=True)

    native_args = _find_executor(model, capella, force)
    with _native.native_capella(model, **native_args) as cli:
        if refresh:
            cli(
                *_native.ARGS_CMDLINE,
                "-appid",
                "org.polarsys.capella.refreshRepresentations",
            )

        cli(
            *_native.ARGS_CMDLINE,
            "-appid",
            "org.polarsys.capella.exportRepresentations",
            "-imageFormat",
            format.upper(),
            "-outputfolder",
            "/main_model/output",
            "-forceoutputfoldercreation",
        )

        diagrams = _copy_images(
            model,
            cli.workspace / "main_model" / "output",
            diag_cache_dir,
            format,
            background,
        )
        if index:
            _write_index(model, format, diag_cache_dir, diagrams)


def _find_executor(
    model: capellambse.MelodyModel,
    capella: str,
    force: t.Literal["exe", "docker", None],
) -> dict[str, str]:
    assert model.info.capella_version
    capella = capella.replace("{VERSION}", model.info.capella_version)
    native_args: dict[str, str] = {}
    if force == "docker":
        native_args["docker"] = capella
    elif force == "exe" or pathlib.Path(capella).is_absolute():
        native_args["exe"] = capella
    elif pathlib.Path(capella).parent == pathlib.Path():
        exe = shutil.which(capella)
        if exe:
            native_args["exe"] = exe
        else:
            raise ValueError(f"Not found in PATH: {capella}")
    else:
        native_args["docker"] = capella
    assert "exe" in native_args or "docker" in native_args
    return native_args


def _copy_images(
    model: capellambse.MelodyModel,
    srcdir: pathlib.Path,
    destdir: pathlib.Path,
    extension: str,
    background: bool,
) -> list[IndexEntry]:
    name_counts = collections.defaultdict[str, int](lambda: -1)
    index: list[IndexEntry] = []
    files = {i.name: i for i in srcdir.glob("**/*") if i.is_file()}

    for i in model.diagrams:
        entry: IndexEntry = {
            "uuid": i.uuid,
            "name": i.name,
            "type": i.type,
            "viewpoint": i.viewpoint,
            "success": False,
        }
        index.append(entry)

        name_counts[i.name] = c = name_counts[i.name] + 1
        if c == 0:
            name = _sanitize_filename(i.name + f".{extension}")
        else:
            name = _sanitize_filename(i.name + f"_{c}.{extension}")

        if name not in files:
            continue

        try:
            source = srcdir / files[name]
            destination = destdir / f"{i.uuid}.{extension}"
            if extension == "svg":
                _copy_and_postprocess_svg(source, destination, background)
            else:
                shutil.copyfile(source, destination)

        except Exception:
            LOGGER.exception("Cannot copy diagram %s (%s)", i.name, i.uuid)
        else:
            entry["success"] = True

    return index


def _sanitize_filename(fname: str) -> str:
    r"""Sanitize the filename.

    This function removes all characters that are illegal in file
    names on Windows operating systems, and prefixes reserved names
    with an underscore.

    Note that this also includes the two common directory separators
    (``/`` and ``\``).

    Notes
    -----
    Refer to the `MSDN article about file names`__ for more details.

    __ https://docs.microsoft.com/en-us/windows/win32/fileio/naming-a-file?redirectedfrom=MSDN#naming-conventions
    """
    fname = fname.rstrip(" .")
    fname = re.sub(
        '[\x00-\x1f<>:"/\\\\|?*]',
        lambda m: "-"[ord(m.group(0)) < ord(" ") :],
        fname,
    )
    if fname.split(".")[0].upper() in BAD_FILENAMES:
        fname = f"_{fname}"
    return fname


def _circle_extents(element: etree._Element) -> Extents:
    """Compute extents for a circle."""
    cx = float(element.get("cx", 0))
    cy = float(element.get("cy", 0))
    r = float(element.get("r", 0))
    return Extents(cx - r, cx + r, cy - r, cy + r)


def _ellipse_extents(element: etree._Element) -> Extents:
    """Compute extents for an ellipse."""
    cx = float(element.get("cx", 0))
    cy = float(element.get("cy", 0))
    rx = float(element.get("rx", 0))
    ry = float(element.get("ry", 0))
    return Extents(cx - rx, cx + rx, cy - ry, cy + ry)


def _image_extents(element: etree._Element) -> Extents:
    """Compute extents for an image."""
    x = float(element.get("x", 0))
    y = float(element.get("y", 0))
    width = float(element.get("width", 0))
    height = float(element.get("height", 0))
    return Extents(x, x + width, y, y + height)


def _line_extents(element: etree._Element) -> Extents:
    """Compute extents for a line."""
    x1 = float(element.get("x1", 0))
    y1 = float(element.get("y1", 0))
    x2 = float(element.get("x2", 0))
    y2 = float(element.get("y2", 0))
    return Extents(min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2))


def _polyline_extents(element: etree._Element) -> Extents:
    """Compute extents for a polyline or polygon."""
    points = [
        tuple(map(float, p.split(",")))
        for p in element.get("points", "").strip().split()
    ]
    x_coords, y_coords = zip(*points, strict=False)
    return Extents(min(x_coords), max(x_coords), min(y_coords), max(y_coords))


def _rect_extents(element: etree._Element) -> Extents:
    """Compute extents for a rectangle."""
    width_str = element.get("width", "0")
    height_str = element.get("height", "0")
    try:
        width = float(width_str)
        height = float(height_str)
    except ValueError:
        raise _NoExtentsFound() from None
    x = float(element.get("x", 0))
    y = float(element.get("y", 0))
    width = float(element.get("width", 0))
    height = float(element.get("height", 0))
    return Extents(x, x + width, y, y + height)


def _text_extents(element: etree._Element) -> Extents:
    """Compute extents for text."""
    x = float(element.get("x", 0))
    y = float(element.get("y", 0))
    text = element.text or ""
    font_size_str = element.get("font-size", "0").strip().lower()
    if "px" in font_size_str:
        font_size_str = font_size_str[:-2]
    font_size = float(font_size_str) or helpers.DEFAULT_FONT_SIZE
    width = len(text) * font_size * 0.6  # Simplistic width estimation
    return Extents(x, x + width, y - font_size, y)


def _use_extents(element: etree._Element) -> Extents:
    """Compute extents for use."""
    x = float(element.get("x", 0))
    y = float(element.get("y", 0))
    width = float(element.get("width", 0))
    height = float(element.get("height", 0))
    return Extents(x, x + width, y, y + height)


EXTENT_FUNCTIONS: dict[str, t.Callable[[etree._Element], Extents]] = {
    "circle": _circle_extents,
    "ellipse": _ellipse_extents,
    "image": _image_extents,
    "line": _line_extents,
    # ``polyline`` and ``polygon`` only differ in whether the shape is
    # implicitly closed (the first and the last point are connected).
    # For the purpose of calculating the extents, this is irrelevant, so
    # we can simply use the same algorithm here.
    "polygon": _polyline_extents,
    "polyline": _polyline_extents,
    "rect": _rect_extents,
    "text": _text_extents,
    "use": _use_extents,
}


def _calculate_svg_viewbox(root: etree._Element) -> ViewBox:
    """Compute bounding box of graphical content for SVG file."""
    x_min = y_min = float("inf")
    x_max = y_max = float("-inf")
    for element in root.iter():
        if (
            isinstance(element, etree._Comment)
            or not hasattr(element, "tag")
            or element.get("transform")
        ):
            continue
        tag = etree.QName(element.tag).localname
        func = EXTENT_FUNCTIONS.get(tag)
        if func is None:
            continue
        try:
            shape_x_min, shape_x_max, shape_y_min, shape_y_max = func(element)
        except (_NoExtentsFound, ValueError):
            continue
        x_min = min(x_min, shape_x_min)
        y_min = min(y_min, shape_y_min)
        x_max = max(x_max, shape_x_max)
        y_max = max(y_max, shape_y_max)

    x_min -= CROP_MARGIN
    y_min -= CROP_MARGIN
    x_max += CROP_MARGIN
    y_max += CROP_MARGIN
    if any(abs(i) == float("inf") for i in (x_min, x_max, y_min, y_max)):
        raise _NoBoundingBoxFound() from None
    return ViewBox(x_min, y_min, x_max - x_min, y_max - y_min)


def _crop_svg_viewbox(src: pathlib.Path, root: etree._Element):
    try:
        min_x, min_y, new_width, new_height = _calculate_svg_viewbox(root)
    except _NoBoundingBoxFound:
        LOGGER.warning("Cannot determine bounding box in file: %s", src)
        return

    old_width = float(root.get("width", 0))
    old_height = float(root.get("height", 0))
    if new_width >= old_width and new_height >= old_height:
        LOGGER.debug(
            (
                "Calculated viewbox for %s is larger than original, ignoring:"
                " (w=%.1f, h=%.1f) > (w=%.1f, h=%.1f)"
            ),
            src,
            new_width,
            new_height,
            old_width,
            old_height,
        )
        return

    old_viewbox_width = float(root.get("viewBox", "0 0 0 0").split()[2])
    old_viewbox_height = float(root.get("viewBox", "0 0 0 0").split()[3])
    if new_width < old_viewbox_width and new_height < old_viewbox_height:
        root.set("viewBox", f"{min_x} {min_y} {new_width} {new_height}")
    elif new_width < old_viewbox_width:
        root.set(
            "viewBox", f"{min_x} {min_y} {new_width} {old_viewbox_height}"
        )
    elif new_height < old_viewbox_height:
        root.set(
            "viewBox", f"{min_x} {min_y} {old_viewbox_width} {new_height}"
        )
    if new_width < old_width:
        root.set("width", str(new_width))
    if new_height < old_height:
        root.set("height", str(new_height))


def _copy_and_postprocess_svg(
    src: pathlib.Path, dest: pathlib.Path, background: bool
) -> None:
    """Copy ``src`` to ``dest`` and post process SVG diagram.

    Post-processing stops propagation of default ``fill`` and ``stroke``
    styling into elements that don't have these stylings. Fixates
    ``font-family`` to ``'Open Sans','Segoe UI',Arial,sans-serif`` and
    deletes ``stroke- miterlimit``.
    """
    tree = etree.parse(src)
    root = tree.getroot()
    if os.getenv(SVG_CROP_FLAG_NAME) == "1":
        _crop_svg_viewbox(src, root)
    if background:
        viewbox = root.get("viewBox", "0 0 0 0").split()
        background_elem = etree.Element(
            "rect",
            x=viewbox[0],
            y=viewbox[1],
            width=viewbox[2],
            height=viewbox[3],
            fill="white",
        )
        root.insert(0, background_elem)
    for elm in tree.iter():
        attrib = elm.attrib
        if "font-family" in attrib:
            attrib["font-family"] = "'Open Sans','Segoe UI',Arial,sans-serif"
        if "stroke-miterlimit" in attrib:
            del attrib["stroke-miterlimit"]
        if elm.tag == "{http://www.w3.org/2000/svg}clipPath":
            attrib.update({"fill": "transparent", "stroke": "transparent"})

    svg = etree.tostring(tree, pretty_print=True)
    dest.write_bytes(svg)


def _write_index(
    model: capellambse.MelodyModel,
    extension: str,
    dest: pathlib.Path,
    index: list[IndexEntry],
) -> None:
    nowtime = datetime.datetime.now(tz=None)
    now = nowtime.strftime("%A, %Y-%m-%d %H:%M:%S")
    title = f"Capella diagram cache for {model.name!r}"
    html = E.html(
        E.head(
            E.style(
                "a:active, a:hover, a:link, a:visited {text-decoration: none}"
                " .missing {color: red}"
                " .helptext {text-decoration: dashed underline; cursor: help}"
                " .small {font-size: 60%}"
                " .uuid {color: #AAA; font-size: 60%}"
            )
        ),
        body := E.body(E.h1(title), E.p({"class": "small"}, "Created: ", now)),
    )

    def sortkey(entry: IndexEntry):
        try:
            vp_index = VIEWPOINT_ORDER.index(entry["viewpoint"])
        except ValueError:
            vp_index = len(VIEWPOINT_ORDER)
        return (vp_index, entry["viewpoint"], entry["name"])

    diagrams = sorted(index, key=sortkey)
    for vp, diags in itertools.groupby(diagrams, key=lambda i: i["viewpoint"]):
        body.append(E.h2(vp))
        body.append(ol := E.ol())
        for diagram in diags:
            uuid = E.span(diagram["uuid"], {"class": "uuid"})
            tlabel = E.span(
                {"title": diagram["type"].value, "class": "helptext"},
                f"[{diagram['type'].name}]",
            )
            if diagram["success"]:
                href = f"{diagram['uuid']}.{extension}"
                label = E.a({"href": href}, diagram["name"])
            else:
                label = E.span({"class": "missing"}, diagram["name"])
            ol.append(E.li(tlabel, " ", label, " ", uuid))

    dest.joinpath("index.json").write_text(json.dumps(index, cls=IndexEncoder))
    dest.joinpath("index.html").write_bytes(etree.tostring(html))


class IndexEncoder(json.JSONEncoder):
    """A JSON encoder for the index file."""

    def default(self, o):
        if isinstance(o, m.DiagramType):
            return o.name
        return super().default(o)
