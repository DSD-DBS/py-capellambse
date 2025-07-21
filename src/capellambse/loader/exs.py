# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""An Eclipse-like XML serializer.

The libxml2 XML serializer produces very different output from the one
used by Capella. This causes a file saved by libxml2 to look vastly
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
import sys
import typing as t
import warnings

import lxml.etree

try:
    from capellambse._compiled import serialize as _native_serialize
except ImportError:
    if (
        os.environ.get("CIBUILDWHEEL", "0") == "1"
        or os.environ.get("CAPELLAMBSE_REQUIRE_NATIVE", "0") == "1"
    ):
        raise

    def _native_serialize(*_1, **_2):  # type: ignore[misc]
        raise TypeError("Native module is not available")

    HAS_NATIVE = False
else:
    HAS_NATIVE = True

_UnspecifiedType = t.NewType("_UnspecifiedType", object)
_NOT_SPECIFIED = _UnspecifiedType(object())

INDENT = b"  "
LINESEP = os.linesep.encode("ascii")
LINE_LENGTH = 80

ESCAPE_CHARS = r"[\x00-\x08\x0A-\x1F\x7F{}]"
P_ESCAPE_TEXT = re.compile(ESCAPE_CHARS.format('"&<'))
P_ESCAPE_COMMENTS = re.compile(ESCAPE_CHARS.format(">"))
P_ESCAPE_ATTR = re.compile(ESCAPE_CHARS.format('"&<\x09'))
P_NAME = re.compile(r"^(?:\{([^}]*)\})?(.+)$")

ALWAYS_EXPANDED_TAGS = frozenset({"bodies", "semanticResources"})


@t.runtime_checkable
class HasWrite(t.Protocol):
    """A simple protocol to check for a writable file-like object."""

    def write(self, chunk: bytes) -> t.Any: ...


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
    encoding: str | _UnspecifiedType = _NOT_SPECIFIED,
    errors: str | _UnspecifiedType = _NOT_SPECIFIED,
    declare_encoding: bool = True,
) -> bytes:
    """Serialize an XML tree as a ``str``.

    At the start of the document, an XML processing instruction will be
    inserted declaring the used encoding. Pass
    ``declare_encoding=False`` to inhibit this behavior.

    Arguments
    ---------
    tree
        The XML tree to serialize.
    encoding
        The encoding to use. An XML processing instruction will be
        inserted which declares the used encoding.
    errors
        How to handle errors during encoding.

    Returns
    -------
    bytes
        The serialized XML, encoded using ``encoding``.
    """
    args = {}
    if encoding is not _NOT_SPECIFIED:
        assert isinstance(encoding, str)
        args["encoding"] = encoding
    else:
        encoding = "utf-8"
    if errors is not _NOT_SPECIFIED:
        assert isinstance(errors, str)
        args["errors"] = errors

    if declare_encoding:
        declaration = _declare(encoding)
    else:
        declaration = b""
    return declaration + serialize(tree, **args)  # type: ignore[call-overload]


def write(
    tree: lxml.etree._Element | lxml.etree._ElementTree,
    /,
    file: HasWrite | os.PathLike | str | bytes,
    *,
    encoding: str | _UnspecifiedType = _NOT_SPECIFIED,
    errors: str | _UnspecifiedType = _NOT_SPECIFIED,
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
    args = {}
    if encoding is not _NOT_SPECIFIED:
        assert isinstance(encoding, str)
        args["encoding"] = encoding
    else:
        encoding = "utf-8"
    if errors is not _NOT_SPECIFIED:
        assert isinstance(errors, str)
        args["errors"] = errors

    ctx: t.ContextManager[HasWrite]
    if isinstance(file, HasWrite):
        ctx = contextlib.nullcontext(file)
    else:
        ctx = open(file, "wb")  # noqa: SIM115

    with ctx as f:
        f.write(_declare(encoding))
        serialize(
            tree,
            **args,
            line_length=line_length,
            siblings=siblings,
            file=f,
        )


@t.overload
def serialize(
    tree: lxml.etree._Element | lxml.etree._ElementTree,
    /,
    *,
    encoding: str = ...,
    errors: str = ...,
    line_length: float | int = ...,
    siblings: bool | None = ...,
    file: None = ...,
) -> bytes: ...
@t.overload
def serialize(
    tree: lxml.etree._Element | lxml.etree._ElementTree,
    /,
    *,
    encoding: str = ...,
    errors: str = ...,
    line_length: float | int = ...,
    siblings: bool | None = ...,
    file: HasWrite,
) -> None: ...
def serialize(
    tree: lxml.etree._Element | lxml.etree._ElementTree,
    /,
    *,
    encoding: str | _UnspecifiedType = _NOT_SPECIFIED,
    errors: str | _UnspecifiedType = _NOT_SPECIFIED,
    line_length: float | int = LINE_LENGTH,
    siblings: bool | None = None,
    file: HasWrite | None = None,
) -> bytes | None:
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
    file
        A file-like object to write the serialized tree to. If None, the
        serialized tree will be returned as bytes instead.

    Returns
    -------
    bytes | None
        The serialized tree (if no *file* was given), or None.
    """
    root: lxml.etree._Element
    if isinstance(tree, lxml.etree._ElementTree):
        if siblings is None:
            siblings = True
        root = tree.getroot()
    else:
        if siblings is None:
            siblings = False
        root = tree

    if encoding is not _NOT_SPECIFIED or errors is not _NOT_SPECIFIED:
        warnings.warn(
            (
                "The 'encoding' and 'errors' arguments are deprecated."
                " The default of strict UTF-8 will soon become the only option."
                " Please remove the arguments from your calls into exs."
            ),
            DeprecationWarning,
            stacklevel=2,
        )

    if encoding is _NOT_SPECIFIED:
        encoding = "utf-8"
    if errors is _NOT_SPECIFIED:
        errors = "strict"
    assert isinstance(encoding, str)
    assert isinstance(errors, str)

    if HAS_NATIVE and encoding == "utf-8" and errors == "strict":
        line_length = min(line_length, sys.maxsize)
        return _native_serialize(
            root, line_length=int(line_length), siblings=siblings, file=file
        )
    return _python_serialize(
        root,
        encoding=encoding,
        errors=errors,
        line_length=line_length,
        siblings=siblings,
        file=file,
    )


def _python_serialize(
    root,
    *,
    encoding: str,
    errors: str,
    line_length: float | int,
    siblings: bool,
    file: HasWrite | None,
) -> bytes | None:
    buffer = io.BytesIO()
    preceding_siblings: cabc.Iterable[lxml.etree._Element]
    following_siblings: cabc.Iterable[lxml.etree._Element]

    if siblings:
        preceding_siblings = reversed(list(root.itersiblings(preceding=True)))
        following_siblings = root.itersiblings()
    else:
        preceding_siblings = ()
        following_siblings = ()

    pos = 0
    for i in preceding_siblings:
        assert isinstance(i, lxml.etree._Comment), "Non-comment before tree"
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
            escape_pattern=P_ESCAPE_TEXT,
        )

    for i in following_siblings:
        assert isinstance(i, lxml.etree._Comment), "Non-comment after tree"
        pos = _serialize_comment(
            buffer, i, encoding=encoding, errors=errors, pos=pos, indent=0
        )

    buffer.write(LINESEP)

    if file is not None:
        file.write(buffer.getvalue())
        return None
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


def _escape(string: str, *, pattern: re.Pattern[str]) -> str:
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
    parent = element.getparent()
    if parent is None:
        parent_ns = set()
    else:
        parent_ns = set(parent.nsmap)

    attribs = dict(element.items())
    for attr in (
        "{http://www.omg.org/XMI}version",
        "{http://www.omg.org/XMI}type",
        "{http://www.omg.org/XMI}id",
        "{http://www.w3.org/2001/XMLSchema-instance}type",
    ):
        value = attribs.pop(attr, None)
        if value is not None:
            yield (
                _unmap_namespace(nsmap, attr),
                _escape(value, pattern=P_ESCAPE_ATTR),
            )

    assert None not in element.nsmap
    for nsname, value in sorted(element.nsmap.items(), key=_ns_sortkey):
        if nsname in parent_ns:
            continue
        yield (f"xmlns:{nsname}", value)

    for attr, value in attribs.items():
        yield (
            _unmap_namespace(nsmap, attr),
            _escape(value, pattern=P_ESCAPE_ATTR),
        )


def _ns_sortkey(v: tuple[str | None, str]) -> tuple[int, str | None]:
    ns, _ = v
    if ns == "xmi":
        return (0, ns)
    if ns == "xsi":
        return (1, ns)
    return (2, ns)


def _serialize_comment(
    buffer: HasWrite,
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
        escape_pattern=P_ESCAPE_COMMENTS,
    )
    buffer.write(b"-->")

    if (comment.tail or "").strip():
        pos = _serialize_text(
            buffer,
            comment.tail,
            encoding=encoding,
            errors=errors,
            pos=pos,
            escape_pattern=P_ESCAPE_TEXT,
        )
    else:
        buffer.write(LINESEP)
        buffer.write(INDENT * indent)
        pos = len(INDENT) * indent
    return pos


def _serialize_element(
    buffer: HasWrite,
    element: lxml.etree._Element,
    indent: int,
    *,
    encoding: str,
    errors: str,
    pos: int = 0,
    line_length: float | int,
) -> int:
    assert isinstance(element, lxml.etree._Element)
    assert None not in element.nsmap
    nsmap = {v: k for k, v in element.nsmap.items() if k}
    buffer.write(b"<")
    assert isinstance(element.tag, str)
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
            escape_pattern=P_ESCAPE_TEXT,
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
                buffer,
                element.tail,
                encoding=encoding,
                errors=errors,
                pos=pos,
                escape_pattern=P_ESCAPE_TEXT,
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
    buffer: HasWrite,
    text: str | None,
    /,
    *,
    encoding: str,
    errors: str,
    pos: int,
    multiline: bool = False,
    escape_pattern: re.Pattern[str],
) -> int:
    if not text:
        return pos
    i, line = 0, ""
    for i, line in enumerate(text.split("\n")):
        if multiline and i:
            buffer.write(LINESEP)
        buffer.write(
            _escape(line, pattern=escape_pattern).encode(encoding, errors)
        )
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
