# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""An Eclipse-like XML serializer.

The libxml2 XML serializer produces very different output from the one
used by Capella.  This causes a file saved by libxml2 to look vastly
different, even though semantically nothing might have changed at all.
This module implements a serializer which produces output like Capella
does.
"""
from __future__ import annotations

import collections.abc as cabc
import contextlib
import html.entities
import io
import os
import re
import typing as t

import lxml.etree

INDENT = b"  "
LINESEP = os.linesep.encode("ascii")
LINE_LENGTH = 80

ESCAPE_CHARS = r"[\x00-\x1F\x7F{}]"
P_ESCAPE_TEXT = re.compile(ESCAPE_CHARS.format('"&<'))
P_ESCAPE_COMMENTS = re.compile(ESCAPE_CHARS.format(">"))
P_NAME = re.compile(r"^(?:\{([^}]*)\})?(.+)$")

ALWAYS_EXPANDED_TAGS = frozenset({"bodies"})


@t.runtime_checkable
class _HasWrite(t.Protocol):
    def write(self, chunk: bytes) -> int:
        ...


def to_string(tree: lxml.etree._Element, /) -> str:
    """Serialize an XML tree as a ``str``.

    No XML processing instruction will be inserted at the start of the
    document.

    Arguments
    ---------
    tree
        The XML tree to serialize.

    Returns
    -------
    str
        The serialized XML.
    """
    payload = serialize(tree, encoding="utf-8", errors="surrogateescape")
    return payload.decode("utf-8", errors="surrogateescape")


def to_bytes(
    tree: lxml.etree._Element,
    /,
    *,
    encoding: str = "utf-8",
    errors: str = "strict",
    declare_encoding: bool = True,
) -> bytes:
    """Serialize an XML tree as a ``str``.

    At the start of the document, an XML processing instruction will be
    inserted declaring the used encoding.  Pass
    ``declare_encoding=False`` to inhibit this behavior.

    Arguments
    ---------
    tree
        The XML tree to serialize.
    encoding
        The encoding to use.  An XML processing instruction will be
        inserted which declares the used encoding.
    errors
        How to handle errors during encoding.

    Returns
    -------
    bytes
        The serialized XML, encoded using ``encoding``.
    """
    if declare_encoding:
        declaration = _declare(encoding)
    else:
        declaration = b""
    return declaration + serialize(tree, encoding=encoding, errors=errors)


def write(
    tree: lxml.etree._Element,
    /,
    file: _HasWrite | os.PathLike | str | bytes,
    *,
    encoding: str = "utf-8",
    errors: str = "strict",
    line_length: float | int = LINE_LENGTH,
    siblings: bool = False,
) -> None:
    """Write the XML tree to ``file``.

    Parameters
    ----------
    tree
        The XML tree to serialize.
    file
        An open file or a PathLike to write the XML into.
    encoding
        The file encoding to use when opening a file.
    errors
        Set the encoding error handling behavior of newly opened files.
    line_length
        The number of characters after which to force a line break.
    siblings
        Also include siblings of the given subtree.
    """
    ctx: t.ContextManager[_HasWrite]
    if isinstance(file, _HasWrite):
        ctx = contextlib.nullcontext(file)
    else:
        ctx = open(file, "wb")

    payload = serialize(
        tree,
        encoding=encoding,
        errors=errors,
        line_length=line_length,
        siblings=siblings,
    )
    with ctx as f:
        f.write(_declare(encoding))
        f.write(payload)


def serialize(
    tree: lxml.etree._Element | lxml.etree._ElementTree,
    /,
    *,
    encoding: str = "utf-8",
    errors: str = "strict",
    line_length: float | int = LINE_LENGTH,
    siblings: bool | None = None,
) -> bytes:
    """Serialize an XML tree.

    The iterator returned by this function yields the serialized XML
    piece by piece.

    Parameters
    ----------
    tree
        The XML tree to serialize.
    encoding
        The encoding to use when generating XML.
    errors
        The encoding error handling behavior.
    line_length
        The number of characters after which to force a line break.
    siblings
        Also include siblings of the given subtree. Defaults to yes if
        'tree' is an element tree, no if it's a single element.

    Returns
    -------
    Iterator[str]
        An iterator that yields the serialized XML piece by piece.
    """
    buffer = io.BytesIO()
    root: lxml.etree._Element
    preceding_siblings: cabc.Iterable[lxml.etree._Comment]
    following_siblings: cabc.Iterable[lxml.etree._Comment]
    if isinstance(tree, lxml.etree._ElementTree):
        if siblings is None:
            siblings = True
        root = tree.getroot()
    else:
        if siblings is None:
            siblings = False
        root = tree

    if siblings:
        preceding_siblings = reversed(list(root.itersiblings(preceding=True)))
        following_siblings = root.itersiblings()
    else:
        preceding_siblings = ()
        following_siblings = ()

    pos = 0
    for i in preceding_siblings:
        pos = _serialize_comment(
            buffer, i, encoding=encoding, errors=errors, pos=pos, indent=0
        )

    _serialize_element(
        buffer,
        root,
        0,
        encoding=encoding,
        errors=errors,
        line_length=line_length,
        pos=pos,
    )
    if (root.tail or "").strip():
        pos = _serialize_text(
            buffer,
            root.tail,
            encoding=encoding,
            errors=errors,
            pos=pos,
            multiline=True,
        )

    for i in following_siblings:
        pos = _serialize_comment(
            buffer, i, encoding=encoding, errors=errors, pos=pos, indent=0
        )

    buffer.write(b"\n")
    return buffer.getvalue()


def _declare(encoding: str) -> bytes:
    return b"".join(
        (
            b'<?xml version="1.0" encoding="',
            encoding.upper().encode("ascii"),
            b'"?>',
            os.linesep.encode("ascii"),
        )
    )


def _escape(string: str, *, pattern: re.Pattern[str] = P_ESCAPE_TEXT) -> str:
    return pattern.sub(_escape_char, string)


def _escape_char(
    match: re.Match[str], *, ord_low: int = ord(" "), ord_high: int = ord("~")
) -> str:
    char = match.group(0)
    assert len(char) == 1
    if ord_low <= ord(char) <= ord_high:
        return f"&{html.entities.codepoint2name[ord(char)]};"
    return f"&#x{ord(char):X};"


def _unmapped_attrs(
    nsmap: cabc.Mapping[str, str], element: lxml.etree._Element
) -> cabc.Iterator[tuple[str, str]]:
    if element.getparent() is None:
        parent_ns = set()
    else:
        parent_ns = set(element.getparent().nsmap)

    attribs = dict(element.items())
    try:
        yield (
            _unmap_namespace(nsmap, "xmi:version"),
            _escape(attribs.pop("{http://www.omg.org/XMI}version")),
        )
    except KeyError:
        pass

    for attr, value in element.nsmap.items():
        if attr in parent_ns:
            continue
        yield (f"xmlns:{attr}", value)

    for attr, value in attribs.items():
        yield (_unmap_namespace(nsmap, attr), _escape(value))


def _serialize_comment(
    buffer: _HasWrite,
    comment: lxml.etree._Comment,
    /,
    *,
    encoding: str,
    errors: str,
    pos: int,
    indent: int,
) -> int:
    assert isinstance(comment, lxml.etree._Comment)

    buffer.write(LINESEP)
    buffer.write(INDENT * indent)
    buffer.write(b"<!--")
    pos = _serialize_text(
        buffer,
        comment.text,
        encoding=encoding,
        errors=errors,
        pos=len(INDENT) * indent,
        pattern=re.compile(r">"),
    )
    buffer.write(b"-->")

    if (comment.tail or "").strip():
        pos = _serialize_text(
            buffer, comment.tail, encoding=encoding, errors=errors, pos=pos
        )
    else:
        buffer.write(LINESEP)
        buffer.write(INDENT * indent)
        pos = len(INDENT) * indent
    return pos


def _serialize_element(
    buffer: _HasWrite,
    element: lxml.etree._Element,
    indent: int,
    *,
    encoding: str,
    errors: str,
    pos: int = 0,
    line_length: float | int,
) -> int:
    assert isinstance(element, lxml.etree._Element)
    nsmap = dict((v, k) for k, v in element.nsmap.items())
    buffer.write(b"<")
    tag = _unmap_namespace(nsmap, element.tag).encode(encoding, errors)
    buffer.write(tag)

    pos += 1 + len(tag)
    attr_indent = INDENT * (indent + 2)
    force_break = False
    for attr, value in _unmapped_attrs(nsmap, element):
        if pos > line_length or force_break:
            buffer.write(LINESEP)
            buffer.write(attr_indent)
            pos = len(attr_indent)
            force_break = False
        else:
            buffer.write(b" ")
            pos += 1

        buffer.write(attr.encode(encoding, errors))
        buffer.write(b'="')
        buffer.write(value.encode(encoding, errors))
        buffer.write(b'"')
        pos += len(attr) + len(value) + 3

        if element.getparent() is None and attr == "id":
            force_break = True

    if (
        element.text is None
        and len(element) == 0
        and element.tag not in ALWAYS_EXPANDED_TAGS
    ):
        buffer.write(b"/>")
        return pos + 2
    buffer.write(b">")

    child_indent = INDENT * (indent + 1)
    if (element.text or "").strip():
        pos = _serialize_text(
            buffer,
            element.text,
            encoding=encoding,
            errors=errors,
            pos=pos,
            multiline=True,
        )
        text_content = True
    else:
        text_content = False

    for child in element:
        if not text_content:
            buffer.write(LINESEP)
            buffer.write(child_indent)
            pos = len(child_indent)

        pos = _serialize_element(
            buffer,
            child,
            indent + 1,
            encoding=encoding,
            errors=errors,
            pos=pos,
            line_length=line_length,
        )
        if (element.tail or "").strip():
            pos = _serialize_text(
                buffer, element.tail, encoding=encoding, errors=errors, pos=pos
            )
            text_content = True
        else:
            text_content = False

    if len(element) > 0 and not text_content:
        buffer.write(LINESEP)
        buffer.write(INDENT * indent)
        pos = len(INDENT) * indent

    buffer.write(b"</")
    buffer.write(tag)
    buffer.write(b">")
    return pos + len(tag) + 3


def _serialize_text(
    buffer: _HasWrite,
    text: str,
    /,
    *,
    encoding: str,
    errors: str,
    pos: int,
    multiline: bool = False,
    pattern: re.Pattern[str] = P_ESCAPE_TEXT,
) -> int:
    i, line = 0, ""
    for i, line in enumerate(text.split("\n")):
        if multiline and i:
            buffer.write(LINESEP)
        buffer.write(_escape(line, pattern=pattern).encode(encoding, errors))
    return len(line) + bool(i) * pos


def _unmap_namespace(nsmap: cabc.Mapping[str, str], name: str) -> str:
    match = P_NAME.search(name)
    assert match is not None
    if ns := match.group(1) or "":
        try:
            ns = nsmap[ns]
        except KeyError:
            raise ValueError(f"Namespace not found: {ns!r}") from None
        assert ns

    tag = match.group(2)
    assert tag

    return "".join((ns, ns and ":", tag))
