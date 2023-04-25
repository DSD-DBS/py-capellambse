# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
"""Module to populate the diagram cache with native Capella diagrams."""

from __future__ import annotations

import collections
import datetime
import json
import logging
import operator
import pathlib
import re
import shutil
import typing as t

import lxml
from lxml import etree

import capellambse.model.diagram
from capellambse import _native
from capellambse.filehandler import local

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


class _IndexEntry(t.TypedDict):
    uuid: str
    name: str
    success: bool


def export(
    capella: str,
    model: capellambse.MelodyModel,
    *,
    format: str,
    index: bool,
    force: t.Literal["exe", "docker", None],
) -> None:
    if not isinstance(
        getattr(model, "_diagram_cache", None), local.LocalFileHandler
    ):
        raise TypeError(
            "Diagram cache updates are only supported for local paths"
        )

    format = format.lower()
    if format not in VALID_FORMATS:
        supported = ", ".join(sorted(VALID_FORMATS))
        raise ValueError(
            f"Invalid image format {format!r}, supported are {supported}"
        )

    diag_cache_dir = pathlib.Path(model._diagram_cache.path)
    try:
        shutil.rmtree(diag_cache_dir)
    except FileNotFoundError:
        pass
    diag_cache_dir.mkdir(parents=True)

    native_args = _find_executor(model, capella, force)
    with _native.native_capella(model, **native_args) as cli:
        assert cli.project
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
) -> list[_IndexEntry]:
    name_counts = collections.defaultdict[str, int](lambda: -1)
    index: list[_IndexEntry] = []
    files = {i.name: i for i in srcdir.glob("**/*") if i.is_file()}
    copy = (shutil.copyfile, _copy_svg)[extension == "svg"]

    for i in model.diagrams:
        entry: _IndexEntry = {"uuid": i.uuid, "name": i.name, "success": False}
        index.append(entry)

        name_counts[i.name] = c = name_counts[i.name] + 1
        if c == 0:
            name = _sanitize_filename(i.name + f".{extension}")
        else:
            name = _sanitize_filename(i.name + f"_{c}.{extension}")

        if name not in files:
            continue

        try:
            copy(srcdir / files[name], destdir / f"{i.uuid}.{extension}")
        except Exception:
            LOGGER.exception("Cannot copy diagram %s (%s)", i.name, i.uuid)
        else:
            entry["success"] = True

    return index


def _sanitize_filename(fname: str) -> str:
    # pylint: disable=line-too-long
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
    # pylint: enable=line-too-long
    fname = fname.rstrip(" .")
    fname = re.sub(
        '[\x00-\x1f<>:"/\\\\|?*]',
        lambda m: "-"[ord(m.group(0)) < 32 :],
        fname,
    )
    if fname.split(".")[0].upper() in BAD_FILENAMES:
        fname = f"_{fname}"
    return fname


def _copy_svg(src: pathlib.Path, dest: pathlib.Path) -> None:
    tree = etree.parse(src)

    for elm in tree.iter():
        attrib = elm.attrib
        if "font-family" in attrib:
            attrib["font-family"] = "'Open Sans','Segoe UI',Arial,sans-serif"
        if "stroke-miterlimit" in attrib:
            del attrib["stroke-miterlimit"]

    dest.write_bytes(etree.tostring(tree, pretty_print=True))


def _write_index(
    model: capellambse.MelodyModel,
    extension: str,
    dest: pathlib.Path,
    index: list[_IndexEntry],
) -> None:
    now = datetime.datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")
    title = f"Capella diagram cache for {model.name!r}"
    html = E.html(
        E.head(
            E.style(
                "a:active, a:hover, a:link, a:visited {text-decoration: none}"
                " .missing {color: red}"
                " ol {font-family: Courier}"
                " span.small {font-size: 40%}"
                " span.uuid {color: #dddddd; font-size: 40%}"
            )
        ),
        E.body(
            E.h1(title, E.span({"class": "small"}, " created: ", now)),
            ol := E.ol(),
        ),
    )

    for diagram in sorted(index, key=operator.itemgetter("name")):
        uuid = E.span(diagram["uuid"], {"class": "uuid"})
        if diagram["success"]:
            href = f"{diagram['uuid']}.{extension}"
            label = E.a({"href": href}, diagram["name"])
        else:
            label = E.span({"class": "missing"}, diagram["name"])
        ol.append(E.li(label, " ", uuid))

    dest.joinpath("index.json").write_text(json.dumps(index))
    dest.joinpath("index.html").write_bytes(etree.tostring(html))
