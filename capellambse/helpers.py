# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Miscellaneous utility functions used throughout the modules."""
from __future__ import annotations

import collections
import collections.abc as cabc
import contextlib
import errno
import functools
import html
import importlib.resources as imr
import itertools
import logging
import math
import operator
import pathlib
import re
import sys
import time
import typing as t

import lxml.html
import markupsafe
import typing_extensions as te
from lxml import etree
from PIL import ImageFont

import capellambse
import capellambse._namespaces as _n

if sys.platform.startswith("win"):
    import msvcrt
else:
    import fcntl

LOGGER = logging.getLogger(__name__)

ATT_XT = f"{{{_n.NAMESPACES['xsi']}}}type"
FALLBACK_FONT = "OpenSans-Regular.ttf"
RE_TAG_NS = re.compile(r"(?:\{(?P<ns>[^}]*)\})?(?P<tag>.*)")
RE_VALID_UUID = re.compile(
    r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
    re.IGNORECASE,
)
LINEBREAK_AFTER = frozenset({"br", "p", "ul", "li"})
TABS_BEFORE = frozenset({"li"})

UUIDString = t.NewType("UUIDString", str)
_T = t.TypeVar("_T")


def flatten_html_string(text: str) -> str:
    """Convert an HTML-string to plain text."""
    frags = lxml.html.fragments_fromstring(text)
    if not frags:
        return ""

    text_container: list[str] = []
    if isinstance(frags[0], str):
        text_container.append(frags.pop(0))

    for frag in frags:
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


# File name and path manipulation
def normalize_pure_path(
    path: str | pathlib.PurePosixPath,
    *,
    base: str | pathlib.PurePosixPath = "/",
) -> pathlib.PurePosixPath:
    """Make a PurePosixPath relative to ``/`` and collapse ``..`` components.

    Parameters
    ----------
    path
        The input path to normalize.
    base
        The base directory to which relative paths should be
        interpreted.  Ignored if the input path is not relative.

    Returns
    -------
    path
        The normalized path.
    """
    path = pathlib.PurePosixPath("/", base, path)

    parts: list[str] = []
    for i in path.parts[1:]:
        if i == "..":
            try:
                parts.pop()
            except IndexError:
                pass
        else:
            parts.append(i)

    return pathlib.PurePosixPath(*parts)


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

    with imr.open_binary("capellambse", FALLBACK_FONT) as fallback_font:
        return ImageFont.truetype(fallback_font, size)


@functools.lru_cache(maxsize=256)
def extent_func(
    text: str,
    fonttype: str = "segoeui.ttf",
    size: int = 8,
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
    (width, height), _ = font.font.getsize(text)
    return (width * 10 / 7, height * 10 / 7)


def get_text_extent(
    text: str,
    width: float | int = math.inf,
) -> tuple[float, float]:
    """Calculate the bounding box size of ``text`` after line wrapping.

    Parameters
    ----------
    text
        Text to calculate the size for.
    width
        Maximum line length (px).

    Returns
    -------
    width
        The width of the text after word wrapping (px).
    height
        The height of the text after word wrapping (px).
    """
    lines = [*map(extent_func, word_wrap(text, width))]
    line_height = max(l[1] for l in lines)
    return max(l[0] for l in lines), line_height * len(lines)


def ssvparse(
    string: str,
    cast: cabc.Callable[[str], _T],
    *,
    parens: cabc.Sequence[str] = ("", ""),
    sep: str = ",",
    num: int = 0,
) -> cabc.Sequence[_T]:
    """Parse a string of ``sep``-separated values wrapped in ``parens``.

    Parameters
    ----------
    string
        The input string.
    cast
        A type to cast the values into.
    parens
        The parentheses that must exist around the input.  Either a
        two-character string or a 2-tuple of strings.
    sep
        The separator between values.
    num
        If non-zero, only accept exactly this many values.

    Returns
    -------
    values
        List of values cast into given type.

    Raises
    ------
    ValueError
        *   If the parentheses are missing around the input string.
        *   If the expected number of values doesn't match the actual
            number.
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


def word_wrap(text: str, width: float | int) -> cabc.Sequence[str]:
    """Perform word wrapping for proportional fonts.

    Whitespace at the beginning of input lines is preserved, but other
    whitespace is collapsed to single spaces.

    Parameters
    ----------
    text
        The text to wrap.
    width
        The width in pixels to wrap to.

    Returns
    -------
    lines
        A list of strings, one for each line, after wrapping.
    """

    def rejoin(words: cabc.Iterable[str], start: int, stop: int | None) -> str:
        return " ".join(itertools.islice(words, start, stop))

    def splitline(line: str) -> list[str]:
        match = re.search(r"^\s*", line)
        assert match is not None
        words = line.split()

        if words:
            words[0] = match.group(0) + words[0]
        return words

    output_lines = []
    input_lines = collections.deque(text.splitlines())
    while input_lines:
        words = collections.deque(splitline(input_lines.popleft()))
        if not words:
            output_lines.append("")
            continue

        words_count = len(words)
        while (
            extent_func(rejoin(words, 0, words_count))[0] > width
            and words_count > 0
        ):
            words_count -= 1

        if words_count > 0:
            output_lines.append(rejoin(words, 0, words_count))
            if words_count < len(words):
                input_lines.appendleft(rejoin(words, words_count, None))

        else:
            word = words.popleft()
            letters_count = len(word)
            while (
                extent_func(word[:letters_count])[0] > width
                and letters_count > 1
            ):
                letters_count -= 1

            output_lines.append(word[:letters_count])
            if letters_count < len(word):
                words.appendleft(word[letters_count:])

            input_lines.appendleft(" ".join(words))

    return output_lines or [""]


# XML tree modification and navigation
def repair_html(markup: str) -> markupsafe.Markup:
    """Try to repair broken HTML markup to prevent parse errors.

    Parameters
    ----------
    markup
        The markup to try and repair.

    Returns
    -------
    markup
        The repaired markup.
    """
    nodes: list[str | lxml.html._Element]
    nodes = lxml.html.fragments_fromstring(markup)
    if nodes and isinstance(nodes[0], str):
        firstnode: str = html.escape(nodes.pop(0))
    else:
        firstnode = ""
    assert all(isinstance(i, etree._Element) for i in nodes)

    for node in itertools.chain.from_iterable(
        map(operator.methodcaller("iter"), nodes)
    ):
        for k in list(node.keys()):
            if ":" in k:
                del node.attrib[k]

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
    tag
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
        elm: str | lxml.html.HTMLElement,
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
        elm: str | lxml.html.HTMLElement,
    ) -> cabc.Iterator[str]:
        if isinstance(elm, str):
            yield html.escape(elm)
        elif elm.tag == "a":
            href = elm.get("href")
            if not (href or "").startswith("hlink://"):
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
                yield f"{next_xtype} {part}"
            else:
                yield part
            next_xtype = ""

        else:
            if next_xtype:
                raise ValueError(f"Malformed link definition: {links}")
            next_xtype = part


@t.overload
def xpath_fetch_unique(
    xpath: str | etree.XPath,
    tree: etree._Element,
    elm_name: str,
    elm_uid: str | None = None,
    *,
    optional: t.Literal[False] = ...,
) -> etree._Element:
    ...


@t.overload
def xpath_fetch_unique(
    xpath: str | etree.XPath,
    tree: etree._Element,
    elm_name: str,
    elm_uid: str | None = None,
    *,
    optional: t.Literal[True],
) -> etree._Element | None:
    ...


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
        UID of the element which triggered this lookup.  Will be
        included in the error message if an error occured.
    optional
        True to return None in case the element is not found.  Otherwise
        a ValueError will be raised.

    Returns
    -------
    element
        The Element found by given ``xpath``.

    Raises
    ------
    ValueError
        *   If more than one element was found matching the ``xpath``.
        *   If ``optional`` is ``False`` and no element was found
            matching the ``xpath``.
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
    UnsupportedPluginError
        If the plugin is unknown and therefore not supported.
    UnsupportedPluginVersionError
        If the plugin's version is not supported.

    Returns
    -------
    xtype
        The ``xsi:type`` string of the provided element or ``None`` if
        the type could not be determined.
    """
    xtype = elem.get(ATT_XT)
    if xtype:
        return xtype

    tagmatch = RE_TAG_NS.fullmatch(elem.tag)
    assert tagmatch is not None
    ns = tagmatch.group("ns")
    tag = tagmatch.group("tag")
    if not ns:
        return None

    nskey, plugin = _n.get_keys_and_plugins_from_namespaces_by_url(ns)
    _n.check_plugin(nskey, plugin)
    return f"{nskey}:{tag}"


# More iteration tools
@t.overload
def ntuples(
    num: int, iterable: cabc.Iterable[_T], *, pad: t.Literal[False] = ...
) -> cabc.Iterator[tuple[_T, ...]]:
    ...


@t.overload
def ntuples(
    num: int, iterable: cabc.Iterable[_T], *, pad: t.Literal[True]
) -> cabc.Iterator[tuple[_T | None, ...]]:
    ...


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
        pad the last yielded tuple with ``None``\ s.  If False, the last
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
        is_contained
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
