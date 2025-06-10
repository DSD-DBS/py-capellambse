# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Miscellaneous utility functions used throughout the modules."""

from __future__ import annotations

import array
import collections.abc as cabc
import contextlib
import errno
import functools
import html
import importlib.resources as imr
import itertools
import logging
import math
import mimetypes
import operator
import os
import pathlib
import random
import re
import sys
import time
import typing as t
import urllib.parse
import uuid

import datauri
import lxml.html
import markupsafe
import typing_extensions as te
from lxml import etree
from markupsafe import escape as e
from PIL import ImageFont

import capellambse
import capellambse._namespaces as _n
import capellambse.filehandler as fh

if sys.platform.startswith("win"):
    import msvcrt
else:
    import fcntl
    import termios

LOGGER = logging.getLogger(__name__)

TAG_XMI = etree.QName(_n.NAMESPACES["xmi"], "XMI")
ATT_XT = f"{{{_n.NAMESPACES['xsi']}}}type"
ATT_XMT = f"{{{_n.NAMESPACES['xmi']}}}type"

FALLBACK_FONT = "OpenSans-Regular.ttf"
RE_VALID_UUID = re.compile(r"[A-Za-z0-9_-]+")
LINEBREAK_AFTER = frozenset({"br", "p", "ul", "li"})
TABS_BEFORE = frozenset({"li"})
DEFAULT_FONT_SIZE = 10
LABEL_WIDTH_PADDING_FACTOR = 1.15
LABEL_HEIGHT_PADDING_FACTOR = 10 / 7

CROSS_FRAGMENT_LINK = re.compile(
    r"""
    ^
    (?:
        (?:
            (?:(?P<xtype>[^ #]+)\ )?
            (?P<fragment>[^ #]+)
        )?
        \#
    )?
    (?P<uuid>[A-Za-z0-9_-]+)
    $
    """,
    re.VERBOSE,
)

_UUID_GENERATOR = random.Random(os.getenv("CAPELLAMBSE_UUID_SEED") or None)

UUIDString = t.NewType("UUIDString", str)
"""A string that represents a unique ID within the model."""
_T = t.TypeVar("_T")


def flatten_html_string(text: str) -> str:
    """Convert an HTML-string to plain text."""
    frags = lxml.html.fragments_fromstring(text)
    if not frags:
        return ""

    text_container: list[str] = []
    if isinstance(frags[0], str):
        text_container.append(frags[0])
        frags.pop(0)

    for frag in frags:
        assert isinstance(frag, lxml.html.HtmlElement)
        text_container.extend(_flatten_subtree(frag))

    return "".join(text_container).rstrip()


def _flatten_subtree(element: etree._Element) -> cabc.Iterator[str]:
    def remove_whitespace(text: str):
        return re.sub("[\n\t]", "", text).lstrip()

    if element.tag in TABS_BEFORE:
        yield "             • "

    if element.text:
        yield remove_whitespace(element.text)

    for child in element:
        yield from _flatten_subtree(child)

    if element.tag in LINEBREAK_AFTER:
        yield "\n"

    if element.tail:
        yield remove_whitespace(element.tail)


def is_uuid_string(string: t.Any) -> te.TypeGuard[UUIDString]:
    """Validate that ``string`` is a valid UUID."""
    return isinstance(string, str) and bool(RE_VALID_UUID.fullmatch(string))


def generate_id() -> str:
    """Generate a new, random ID to be used in the model."""
    return str(uuid.UUID(bytes=_UUID_GENERATOR.randbytes(16), version=4))


@contextlib.contextmanager
def deterministic_ids(*, seed: t.Any = None) -> cabc.Iterator[None]:
    """Enter a context during which generated IDs are deterministic.

    This function is primarily intended for testing.

    It can be used as a context manager, where deterministic IDs will be
    generated until the context ends:

    >>> with deterministic_ids():
    ...     print(generate_id())
    ...     print(generate_id())
    ...
    cd072cd8-be6f-4f62-ac4c-09c28206e7e3
    5594aa6b-342f-4d0a-ba5e-4842fab428f7
    >>> with deterministic_ids():
    ...     print(generate_id())
    ...     print(generate_id())
    ...
    cd072cd8-be6f-4f62-ac4c-09c28206e7e3
    5594aa6b-342f-4d0a-ba5e-4842fab428f7

    It can also be used to annotate a function, in which case
    deterministic IDs will be generated while that function is being
    called:

    >>> @deterministic_ids()
    ... def print_the_same_ids():
    ...     print(generate_id())
    ...     print(generate_id())
    ...
    >>> print_the_same_ids()
    cd072cd8-be6f-4f62-ac4c-09c28206e7e3
    5594aa6b-342f-4d0a-ba5e-4842fab428f7
    >>> print_the_same_ids()
    cd072cd8-be6f-4f62-ac4c-09c28206e7e3
    5594aa6b-342f-4d0a-ba5e-4842fab428f7

    A seed for the PRNG may be passed using the *seed* keyword argument:

    >>> with deterministic_ids(seed=1234):
    ...     print(generate_id())
    ...     print(generate_id())
    ...
    b97f69f7-5edf-45c7-9fda-d37066eae91d
    14f6ea01-456b-4417-b0b8-35e942f549f1
    >>> @deterministic_ids(seed=1234)
    ... def print_the_same_ids():
    ...     print(generate_id())
    ...     print(generate_id())
    ...
    >>> print_the_same_ids()
    b97f69f7-5edf-45c7-9fda-d37066eae91d
    14f6ea01-456b-4417-b0b8-35e942f549f1
    """
    global _UUID_GENERATOR

    if seed is None:
        seed = 0
    orig_generator = _UUID_GENERATOR
    _UUID_GENERATOR = random.Random(seed)
    try:
        yield
    finally:
        _UUID_GENERATOR = orig_generator


# File name and path manipulation
def normalize_pure_path(
    path: str | pathlib.PurePosixPath,
    *,
    base: str | pathlib.PurePosixPath = "/",
) -> pathlib.PurePosixPath:
    """Make a PurePosixPath relative to *base* and collapse ``..`` components.

    Parameters
    ----------
    path
        The input path to normalize.
    base
        The base directory to which relative paths should be
        interpreted. Ignored if the input path is not relative.

    Returns
    -------
    pathlib.PurePosixPath
        The normalized path.
    """
    path = pathlib.PurePosixPath("/", base, path)

    parts: list[str] = []
    for i in path.parts[1:]:
        if i == "..":
            with contextlib.suppress(IndexError):
                parts.pop()
        else:
            parts.append(i)

    return pathlib.PurePosixPath(*parts)


def relpath_pure(
    path: pathlib.PurePosixPath, start: pathlib.PurePosixPath
) -> pathlib.PurePosixPath:
    """Calculate the relative path between two pure paths.

    Unlike :meth:`pathlib.PurePath.relative_to`, this method can cope
    with ``path`` not being a subpath of ``start``. And unlike the
    :func:`os.path.relpath` function, it does not involve any filesystem
    access.
    """
    parts = list(reversed(path.parts))
    prefix = True
    for part in start.parts:
        if prefix:
            if parts and parts[-1] == part:
                parts.pop()
            else:
                prefix = False
        else:
            parts.append("..")
    return pathlib.PurePosixPath(*reversed(parts))


if sys.platform.startswith("win"):

    @contextlib.contextmanager
    def flock(file: pathlib.Path) -> t.Iterator[None]:
        file = file.resolve()
        logged = False
        with file.open("wb") as lock:
            while True:
                try:
                    msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
                except OSError as err:
                    if err.errno == errno.EDEADLOCK:
                        if not logged:
                            LOGGER.debug("Waiting for lock file %s", file)
                            logged = True
                        time.sleep(1)
                    else:
                        raise
                else:
                    break

            try:
                yield
            finally:
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)

else:

    @contextlib.contextmanager
    def flock(file: pathlib.Path) -> t.Iterator[None]:
        file = file.resolve()
        with file.open("wb") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                LOGGER.debug("Waiting for lock file %s", file)
                fcntl.flock(lock, fcntl.LOCK_EX)

            yield


# Text processing and rendering
@functools.lru_cache(maxsize=8)
def load_font(fonttype: str, size: int) -> ImageFont.FreeTypeFont:
    for name in (fonttype, fonttype.upper(), fonttype.lower()):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass

    fontfile = imr.files(capellambse).joinpath(FALLBACK_FONT)
    with fontfile.open("rb") as fallback_font:
        te.assert_type(fallback_font, t.IO[bytes])
        fallback_font = t.cast(t.BinaryIO, fallback_font)
        return ImageFont.truetype(fallback_font, size)


@functools.lru_cache(maxsize=256)
def extent_func(
    text: str,
    fonttype: str = "OpenSans-Regular.ttf",
    size: int = DEFAULT_FONT_SIZE,
) -> tuple[float, float]:
    """Calculate the display size of the given text.

    Parameters
    ----------
    text
        Text to calculate pixel size on
    fonttype
        The font type / face
    size
        Font size (px)

    Returns
    -------
    width
        The calculated width of the text (px).
    height
        The calculated height of the text (px).
    """
    width = height = 0
    font = load_font(fonttype, size)
    (width, height), _ = font.font.getsize(text)  # type: ignore[call-arg] # broken type stubs
    return (
        width * LABEL_WIDTH_PADDING_FACTOR,
        height * LABEL_HEIGHT_PADDING_FACTOR,
    )


def get_text_extent(
    text: str,
    width: float | int = math.inf,
    fonttype: str = "OpenSans-Regular.ttf",
    fontsize: int = DEFAULT_FONT_SIZE,
) -> tuple[float, float]:
    """Calculate the bounding box size of ``text`` after line wrapping.

    Parameters
    ----------
    text
        Text to calculate the size for.
    width
        Maximum line length (px).
    fonttype
        The font type / face
    fontsize
        Font size (px)

    Returns
    -------
    width
        The width of the text after word wrapping (px).
    height
        The height of the text after word wrapping (px).
    """
    ex_func = functools.partial(extent_func, fonttype=fonttype, size=fontsize)
    lines = [*map(ex_func, word_wrap(text, width))]
    line_height = max(i[1] for i in lines)
    return max(i[0] for i in lines), line_height * len(lines)


def make_short_html(
    clsname: str,
    uuid: str,
    name: str = "",
    value: str = "",
    *,
    icon: str = "",
    iconsize: int | None = None,
) -> markupsafe.Markup:
    """Make HTML that briefly describes an element.

    The layout of the generated HTML string is:

        [icon and/or clsname] [name]: [value] ([uuid])

    If an icon is used, the clsname is used for its alt and hover text.

    All values passed except for `icon` will be HTML-escaped.

    Parameters
    ----------
    clsname
        The name of the object's class.
    uuid
        The object's UUID.
    name
        The human-readable name of the object.
    value
        If the object contains a value of some sort, which is more
        interesting to the end user than the fact that the object
        exists, this parameter can be used to display the value.
    icon
        The icon to use, encoded as `data:` URI. Note that this value
        must already be HTML-safe.
    iconsize
        Fix the width and height of the icon to this pixel value. Needed
        if the client application has dumb CSS rules.
    """
    clsname = e(clsname)
    uuid = e(uuid)
    name = e(name)
    value = e(value)
    if icon:
        icon_html = f'<img src="{icon}" alt="{clsname}" title="{clsname}"'
        if iconsize:
            icon_html += f' width="{iconsize}" height="{iconsize}"'
        icon_html += ' style="display: inline-block">'
    else:
        icon_html = f"<strong>{clsname}</strong>"

    if icon and not name:
        link = (
            f'<a href="hlink://{uuid}">'
            f"{icon_html} <strong>{clsname}</strong></a>"
        )
    elif not name:
        link = f'<a href="hlink://{uuid}">{icon_html}</a>'
    else:
        link = f'{icon_html} <a href="hlink://{uuid}">&quot;{name}&quot;</a>'

    if not value:
        return markupsafe.Markup(f"{link} ({uuid})")
    return markupsafe.Markup(f"{link}: {value} ({uuid})")


def ssvparse(
    string: str,
    cast: cabc.Callable[[str], _T],
    *,
    parens: cabc.Sequence[str] = ("", ""),
    sep: str = ",",
    num: int = 0,
) -> list[_T]:
    """Parse a string of ``sep``-separated values wrapped in ``parens``.

    Parameters
    ----------
    string
        The input string.
    cast
        A type to cast the values into.
    parens
        The parentheses that must exist around the input. Either a
        two-character string or a 2-tuple of strings.
    sep
        The separator between values.
    num
        If non-zero, only accept exactly this many values.

    Returns
    -------
    list[_T]
        A list of values cast into the given type.

    Raises
    ------
    ValueError
        If the parentheses are missing around the input string, or if
        the expected number of values doesn't match the actual number.
    """
    if not string.startswith(parens[0]) or not string.endswith(parens[1]):
        raise ValueError(f"Missing {parens} around string: {string}")
    string = string[len(parens[0]) : -len(parens[1])]
    values = [cast(v) for v in string.split(sep)]
    if num and len(values) != num:
        raise ValueError(
            f"Expected {num} values, found {len(values)}: {string}"
        )
    return values


def word_wrap(text: str, width: float | int) -> list[str]:
    """Perform word wrapping for proportional fonts.

    Whitespace at the beginning of input lines is preserved, but other
    whitespace is collapsed to single spaces. Words are kept as a whole,
    possibly leading to exceeding width bound.

    Parameters
    ----------
    text
        The text to wrap.
    width
        The width in pixels to wrap to.

    Returns
    -------
    list[str]
        A list of strings, one for each line, after wrapping.
    """

    def split_into_lines(line: str, width: float | int) -> list[str]:
        words = line.split()
        if not words:
            return [line]

        current_line = ""
        lines = []
        for word in words:
            test_line = word if not current_line else f"{current_line} {word}"
            if extent_func(test_line)[0] <= width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines

    special_chars = ("•", "-")
    output_lines = []
    input_lines = text.splitlines()
    for i, line in enumerate(input_lines):
        leading_whitespace = ""
        if i == 0:
            leading_whitespace = line[: len(line) - len(line.lstrip())]
        elif line.lstrip().startswith(special_chars):
            leading_whitespace = " "

        wrapped_lines = split_into_lines(line.lstrip(), width)
        if wrapped_lines:
            output_lines.append(f"{leading_whitespace}{wrapped_lines[0]}")
            output_lines.extend(wrapped_lines[1:])

    return output_lines or [""]


def get_term_cell_size(stream=None) -> tuple[int, int]:
    """Get the cell size of the terminal.

    Parameters
    ----------
    stream
        The stream that the terminal is connected to. If None, the
        stderr stream will be probed.

    Returns
    -------
    tuple[int, int]
        The width and height of a cell.

    Raises
    ------
    ValueError
        Raised if the cell size could not be determined.
    """
    if stream is None:
        if not sys.stderr.isatty():
            raise ValueError("No stream given and stderr is not a TTY")
        stream = sys.stderr
    elif not stream.isatty():
        raise ValueError("Passed stream is not a TTY")

    if sys.platform.startswith("win"):
        raise ValueError("Not supported on Windows")

    buf = array.array("H", [0, 0, 0, 0])
    fcntl.ioctl(stream, termios.TIOCGWINSZ, buf)
    if 0 in buf:
        raise ValueError(f"Received invalid ioctl reply: {buf!r}")
    rows, cols, screenwidth, screenheight = buf
    return (screenwidth // cols, screenheight // rows)


# XML tree modification and navigation
def repair_html(markup: str) -> markupsafe.Markup:
    """Try to repair broken HTML markup to prevent parse errors.

    Parameters
    ----------
    markup
        The markup to try and repair.

    Returns
    -------
    markupsafe.Markup
        The repaired markup.
    """

    def cb(node: etree._Element) -> None:
        for k in list(node.keys()):
            if ":" in k:
                del node.attrib[k]

    return process_html_fragments(markup, cb)


def replace_hlinks(
    markup: str,
    model: capellambse.model.MelodyModel,
    make_href: cabc.Callable[[capellambse.model.ModelElement], str | None],
    *,
    broken_link_css: str = "color: red; text-decoration: line-through;",
) -> markupsafe.Markup:
    """Replace hlink:// links with arbitrary other links.

    Parameters
    ----------
    markup
        The markup to process.
    model
        The model to use for resolving UUIDs.
    make_href
        A function that maps objects to URLs. This function is called
        once for each link (possibly multiple times for the same
        object), and must return a URL to be inserted in place of the
        original ``hlink://...`` URL.
    broken_link_css
        Broken links (links to objects that have been deleted, and links
        where the ``make_href`` callback returned None or an empty
        string) are indicated by a ``<span>`` element with this CSS
        style applied to it.
    """

    def cb(el: etree._Element) -> None:
        if el.tag != "a" or "href" not in el.attrib:
            return

        try:
            url = urllib.parse.urlparse(el.attrib["href"])
        except ValueError:
            return
        if url.scheme != "hlink":
            return

        try:
            obj = model.by_uuid(url.netloc)
        except KeyError:
            pass
        else:
            if href := make_href(obj):
                el.attrib["href"] = href
                return

        el.tag = "span"
        el.attrib["style"] = broken_link_css
        del el.attrib["href"]
        return

    return process_html_fragments(markup, cb)


def _parse_image_path(
    resources: cabc.Mapping[str, fh.FileHandler], raw_path: str, /
) -> tuple[fh.FileHandler | None, pathlib.PurePosixPath]:
    if not raw_path or "://" in raw_path:
        return (None, pathlib.PurePosixPath())

    parts = pathlib.PurePosixPath(raw_path).parts
    if len(parts) < 2:
        return (None, pathlib.PurePosixPath())

    srcpath = pathlib.PurePosixPath(*parts[1:])
    hdl = (
        resources.get(parts[0])
        or resources.get(parts[0].removesuffix(".team"))
        or resources.get("\x00")
    )
    return hdl, srcpath


def embed_images(
    markup: str,
    /,
    resources: cabc.Mapping[str, fh.FileHandler],
) -> markupsafe.Markup:
    """Embed images into description text.

    This function replaces ``<img>`` tags linking to an image file in
    one of the given resources with a base64-encoded data URI containing
    the image data directly. The original path is preserved in the
    ``data-capella-path`` attribute.

    See Also
    --------
    unembed_images : The inverse operation.
    """

    def cb(el: etree._Element) -> None:
        if el.tag != "img":
            return

        src = el.get("src", "")
        hdl, srcpath = _parse_image_path(resources, src)
        if hdl is None:
            return

        try:
            content = hdl.read_file(srcpath)
        except FileNotFoundError:
            LOGGER.warning("Image not found: %s", srcpath)
            return

        mime, _ = mimetypes.guess_type(srcpath.as_posix(), strict=False)
        if not mime:
            LOGGER.warning("Unknown image format: %s", srcpath)
            return
        el.set("src", datauri.DataURI.make(mime, None, True, content))
        el.set("data-capella-path", src)

    return process_html_fragments(markup, cb)


def unembed_images(
    markup: str,
    /,
    resources: cabc.Mapping[str, fh.FileHandler],
) -> markupsafe.Markup:
    """Unembed images from description text.

    This function replaces ``<img>`` tags containing data URIs with links that
    can be interpreted by Capella, and writes the image data into files in the
    provided model's resources.

    See Also
    --------
    embed_images : The inverse operation.
    """

    def cb(el: etree._Element) -> None:
        if el.tag != "img":
            return

        src = el.get("src", "")
        if not src.startswith("data:"):
            return
        src = datauri.DataURI(src)

        if path := el.get("data-capella-path"):
            hdl, srcpath = _parse_image_path(resources, path)
            if hdl is None:
                return
            hdlname = pathlib.PurePosixPath(path).parts[0]
        else:
            ext = (
                mimetypes.guess_extension(src.mimetype, strict=False) or ""
                if src.mimetype
                else ""
            )
            srcpath = pathlib.PurePosixPath("images", f"{generate_id()}{ext}")
            hdl = resources.get("\x00")
            if hdl is None:
                return
            try:
                dotproject = hdl.read_file(".project")
                ptree = etree.fromstring(dotproject)
                (hdlname,) = ptree.xpath("/projectDescription/name/text()")
            except Exception:
                LOGGER.debug("Could not read project name of default handler")
                return

        hdl.write_file(srcpath, src.data)
        el.set("src", f"{hdlname}/{srcpath.as_posix()}")
        el.attrib.pop("data-capella-path", None)

    return process_html_fragments(markup, cb)


def process_html_fragments(
    markup: str, node_callback: cabc.Callable[[etree._Element], None]
) -> markupsafe.Markup:
    """Repair and modify HTML markup.

    The original markup, which can be an HTML fragment (without a root
    element), is parsed and processed, and then reassembled into a
    Markup instance. If the original markup contained any errors or
    inconsistencies, these are repaired in the returned Markup instance.

    Parameters
    ----------
    markup
        The markup string to modify.
    node_callback
        A callback function to process each node in the parsed markup.
        The function should accept a single
        :py:class:`lxml.etree._Element` as argument; its return value is
        ignored.

        Note that, since the markup is parsed as fragments, more than
        the first element passed to the callback may have no parent.

        The callback will not be invoked for leading text, if there is
        any, and thus it has no ability to influence it.

    Returns
    -------
    markupsafe.Markup
        The processed markup.
    """
    rawnodes = lxml.html.fragments_fromstring(markup)
    if rawnodes and isinstance(rawnodes[0], str):
        firstnode = html.escape(rawnodes[0])
        nodes = t.cast(list[etree._Element], rawnodes[1:])
    else:
        firstnode = ""
        nodes = t.cast(list[etree._Element], rawnodes)

    for node in itertools.chain.from_iterable(
        map(operator.methodcaller("iter"), nodes)
    ):
        node_callback(node)

    othernodes = b"".join(
        etree.tostring(i, encoding="utf-8") for i in nodes
    ).decode("utf-8")

    return markupsafe.Markup(firstnode + othernodes)


def resolve_namespace(tag: str) -> str:
    """Resolve a ':'-delimited symbolic namespace to its canonical form.

    Parameters
    ----------
    tag
        Symbolic namespace delimited by ':'.

    Returns
    -------
    str
        Tag string in canonical form.
    """
    if ":" in tag:
        namespace, tag = tag.split(":")
        return f"{{{_n.NAMESPACES[namespace]}}}{tag}"
    return tag


def unescape_linked_text(
    loader: capellambse.loader.MelodyLoader, attr_text: str | None
) -> markupsafe.Markup:
    """Transform the ``linkedText`` into regular HTML."""

    def flatten_element(
        elm: str | lxml.html.HtmlElement,
    ) -> cabc.Iterator[str]:
        if isinstance(elm, str):
            yield html.escape(elm)
        elif elm.tag == "a":
            href = elm.get("href")
            if href is None:
                yield "&lt;broken link&gt;"
                yield html.escape(elm.tail or "")
                return
            ehref = html.escape(href)

            try:
                target = loader[href]
            except KeyError:
                yield f"&lt;deleted element {ehref}&gt;"
            else:
                if name := target.get("name"):
                    name = html.escape(name)
                else:
                    name = f"&lt;unnamed element {ehref}&gt;"
                yield f'<a href="hlink://{ehref}">{name}</a>'
            yield html.escape(elm.tail or "")
        else:
            yield html.escape(elm.text or "")
            for child in elm:
                yield from flatten_element(child)
            yield html.escape(elm.tail or "")

    elements = lxml.html.fragments_fromstring(attr_text or "")
    escaped_text = "".join(
        itertools.chain.from_iterable(flatten_element(i) for i in elements)
    )
    return markupsafe.Markup(escaped_text)


def escape_linked_text(
    loader: capellambse.loader.MelodyLoader, attr_text: str
) -> str:
    """Transform simple HTML with object links into ``LinkedText``.

    This is the inverse operation of :func:`unescape_linked_text`.
    """
    del loader

    def flatten_element(
        elm: str | lxml.html.HtmlElement,
    ) -> cabc.Iterator[str]:
        if isinstance(elm, str):
            yield html.escape(elm)
        elif elm.tag == "a":
            href = elm.get("href")
            if href is None or not href.startswith("hlink://"):
                yield html.escape(elm.text or "")
            else:
                yield '<a href="'
                yield html.escape(href[len("hlink://") :])
                yield '"/>'
            if len(elm) > 0:
                raise ValueError("Nesting is not allowed in LinkedText")
        else:
            raise ValueError(
                f"Only 'a' tags are allowed in LinkedText, not {elm.tag!r}"
            )

    elements = lxml.html.fragments_fromstring(attr_text)
    text = "".join(
        itertools.chain.from_iterable(flatten_element(i) for i in elements)
    )
    return markupsafe.Markup(text)


def split_links(links: str) -> cabc.Iterator[str]:
    """Split a string containing intra- and inter-fragment links.

    Intra-fragment links are simply "#UUID", whereas inter-fragment
    links look like "xtype fragment#UUID". Multiple such links are
    space-separated in a single long string to form a list. This
    function splits such a string back into its individual components
    (each being either an intra- or inter-fragment link), and yields
    them.

    Yields
    ------
    str
        A single link from the list.
    """
    next_xtype = ""
    for part in links.split():
        if "#" in part:
            if next_xtype:
                part = f"{next_xtype} {part}"
                next_xtype = ""
            if not CROSS_FRAGMENT_LINK.fullmatch(part):
                raise ValueError(f"Malformed link definition: {links}")
            yield part

        else:
            if next_xtype:
                raise ValueError(f"Malformed link definition: {links}")
            next_xtype = part
    if next_xtype:
        raise ValueError(f"Malformed link definition: {links}")


@t.overload
def xpath_fetch_unique(
    xpath: str | etree.XPath,
    tree: etree._Element,
    elm_name: str,
    elm_uid: str | None = None,
    *,
    optional: t.Literal[False] = ...,
) -> etree._Element: ...
@t.overload
def xpath_fetch_unique(
    xpath: str | etree.XPath,
    tree: etree._Element,
    elm_name: str,
    elm_uid: str | None = None,
    *,
    optional: t.Literal[True],
) -> etree._Element | None: ...
def xpath_fetch_unique(
    xpath: str | etree.XPath,
    tree: etree._Element,
    elm_name: str,
    elm_uid: str | None = None,
    *,
    optional: bool = False,
) -> etree._Element | None:
    """Fetch an XPath result from the tree, ensuring that it's unique.

    Parameters
    ----------
    xpath
        The :class:`lxml.etree.XPath` object to apply, or an XPath
        expression as str.
    tree
        The (sub-)tree to which the XPath will be applied.
    elm_name
        A human-readable element name for error messages.
    elm_uid
        UID of the element which triggered this lookup. Will be included
        in the error message if an error occured.
    optional
        True to return None in case the element is not found. Otherwise
        a ValueError will be raised.

    Returns
    -------
    lxml.etree._Element | None
        The Element found by given ``xpath``.

    Raises
    ------
    ValueError
        If more than one element was found matching the ``xpath``, or if
        ``optional`` is ``False`` and no matching element was found.
    """
    if isinstance(xpath, str):
        xpath = etree.XPath(
            xpath, namespaces=_n.NAMESPACES, smart_strings=False
        )

    result = xpath(tree)
    if len(result) > 1:
        raise ValueError(
            f"Invalid XML: {elm_name!r} is not unique, found {len(result)}"
            + (f" while processing element {elm_uid!r}" if elm_uid else "")
        )
    if not optional and not result:
        raise ValueError(
            f"Invalid XML: {elm_name!r} not found"
            + (f" while processing element {elm_uid!r}" if elm_uid else "")
        )

    return result[0] if result else None


def qtype_of(element: etree._Element) -> etree.QName | None:
    """Get the qualified type of the element."""
    parent = element.getparent()
    if parent is None or (
        parent.getparent() is None and parent.tag == TAG_XMI
    ):
        return etree.QName(element)

    xtype = element.get(ATT_XT)
    if not xtype or ":" not in xtype:
        xtype = element.get(ATT_XMT)
    if not xtype or ":" not in xtype:
        return None
    nsalias, clsname = xtype.rsplit(":", 1)
    try:
        nsuri = element.nsmap[nsalias]
    except KeyError:
        LOGGER.error("Namespace %r not found on element %r", nsalias, element)
        return None
    return etree.QName(nsuri, clsname)


def xtype_of(elem: etree._Element) -> str | None:
    """Return the ``xsi:type`` of the element.

    If the element has an ``xsi:type`` attribute, its value is returned.

    If the element does not have an ``xsi:type``, this function resolves
    the tag's namespace to the symbolic name and reconstructs the type
    with the ``namespace:tag`` template.

    Parameters
    ----------
    elem
        The :class:`lxml.etree._Element` object to return the
        ``xsi:type`` for.

    Raises
    ------
    capellambse.UnsupportedPluginError
        If the plugin is unknown and therefore not supported.
    capellambse.UnsupportedPluginVersionError
        If the plugin's version is not supported.

    Returns
    -------
    str | None
        The ``xsi:type`` string of the provided element or ``None`` if
        the type could not be determined.
    """
    if xtype := elem.get(ATT_XT):
        return xtype
    if xtype := elem.get(ATT_XMT):
        return xtype

    tag = etree.QName(elem)
    if not tag.namespace:
        return None

    nskey = _n.get_namespace_prefix(tag.namespace)
    return f"{nskey}:{tag.localname}"


# More iteration tools
@t.overload
def ntuples(
    num: int, iterable: cabc.Iterable[_T], *, pad: t.Literal[False] = ...
) -> cabc.Iterator[tuple[_T, ...]]: ...
@t.overload
def ntuples(
    num: int, iterable: cabc.Iterable[_T], *, pad: t.Literal[True]
) -> cabc.Iterator[tuple[_T | None, ...]]: ...
def ntuples(
    num: int,
    iterable: cabc.Iterable[_T],
    *,
    pad: bool = False,
) -> cabc.Iterator[tuple[_T | None, ...]]:
    r"""Yield N items of ``iterable`` at once.

    Parameters
    ----------
    num
        The number of items to yield at once.
    iterable
        An iterable.
    pad
        If the items in ``iterable`` are not evenly divisible by ``n``,
        pad the last yielded tuple with ``None``\ s. If False, the last
        tuple will be discarded.

    Yields
    ------
    items
        A ``num`` long tuple of items from ``iterable``.
    """
    iterable = iter(iterable)
    while True:
        value = tuple(itertools.islice(iterable, num))
        if len(value) == num:
            yield value
        elif value and pad:
            yield value + (None,) * (num - len(value))
        else:
            break


# Simple one-trick helper classes
class EverythingContainer(t.Container[t.Any]):
    """A container that contains everything."""

    def __contains__(self, _: t.Any) -> bool:  # pragma: no cover
        """Return ``True``.

        Parameters
        ----------
        _
            Ignored.

        Returns
        -------
        bool
            Always ``True``.
        """
        return True


def get_transformation(
    class_: str,
    pos: tuple[float, float],
    size: tuple[float, float],
) -> dict[str, str]:
    """Calculate transformation for class.

    The Scaling factor .725, translation constants (6, 5) are arbitrarily
    chosen to fit. Currently only ChoicePseudoState is tranformed.

    Parameters
    ----------
    class_
        Classtype string
    pos
        Position-vector
    size
        Size vector
    """
    if class_ != "ChoicePseudoState":
        return {}

    s = 0.725
    tx, ty = (1 - s) * pos[0] + 6, (1 - s) * pos[1] + 5
    rx, ry = pos[0] + size[0] / 2, pos[1] + size[1] / 2
    return {
        "transform": f"translate({tx},{ty}) scale({s}) rotate(45,{rx},{ry})"
    }
