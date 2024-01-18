# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Module to populate the diagram cache with native Capella diagrams."""

from __future__ import annotations

import collections
import datetime
import itertools
import json
import logging
import pathlib
import re
import shutil
import typing as t

import lxml
from lxml import etree

import capellambse.model.diagram
from capellambse import _native
from capellambse.filehandler import local
from capellambse.model import modeltypes

E = lxml.builder.ElementMaker()
BAD_FILENAMES = frozenset(
    {"AUX", "CON", "NUL", "PRN"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)
LOGGER = logging.getLogger(__name__)
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


class IndexEntry(t.TypedDict):
    """An entry for the index JSON file."""

    uuid: str
    name: str
    type: modeltypes.DiagramType
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
    try:
        shutil.rmtree(diag_cache_dir)
    except FileNotFoundError:
        pass
    diag_cache_dir.mkdir(parents=True)

    native_args = _find_executor(model, capella, force)
    with _native.native_capella(model, **native_args) as cli:
        assert cli.project

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
            cli.project / "main_model" / "output",
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
    elif force == "exe":
        native_args["exe"] = capella
    else:
        if pathlib.Path(capella).is_absolute():
            native_args["exe"] = capella
        elif pathlib.Path(capella).parent == pathlib.Path("."):
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
                _copy_and_sanitize_svg(source, destination, background)
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
        lambda m: "-"[ord(m.group(0)) < 32 :],
        fname,
    )
    if fname.split(".")[0].upper() in BAD_FILENAMES:
        fname = f"_{fname}"
    return fname


def _copy_and_sanitize_svg(
    src: pathlib.Path, dest: pathlib.Path, background: bool
) -> None:
    """Copy ``src`` to ``dest`` and post process SVG diagram.

    Post-processing stops propagation of default ``fill`` and ``stroke``
    styling into elements that don't have these stylings. Fixates
    ``font-family`` to ``'Open Sans','Segoe UI',Arial,sans-serif`` and
    deletes ``stroke- miterlimit``.
    """
    tree = etree.parse(src)
    if background:
        root = tree.getroot()
        background_elem = etree.Element(
            "rect", x="0", y="0", width="100%", height="100%", fill="white"
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
    now = datetime.datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")
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
        if isinstance(o, modeltypes.DiagramType):
            return o.name
        return super().default(o)
