# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

__all__ = [
    "FileHandler",
    "TransactionClosedError",
    "get_filehandler",
]

import logging
import os
import pathlib
import re
import sys
import typing as t
from importlib import metadata

from .abc import *

LOGGER = logging.getLogger(__name__)


def _looks_like_local_path(path: str | os.PathLike) -> bool:
    path = os.fspath(path)
    return bool(
        path.startswith(("/", r"\\")) or re.search(r"^[A-Za-z]:[\\/]", path)
    )


def _looks_like_scp(path: str) -> bool:
    return bool(re.search(r"^(?:\w+@)?[\w.]+:(?:/?[^/].*)?$", path))


def split_protocol(uri: str | os.PathLike) -> tuple[str, str | os.PathLike]:
    """Split the protocol from the URI.

    This function is used to find the name of the file handler for a
    given URI. It takes a URI and returns a tuple of the handler name
    and the potentially modified URI. This function performs the
    following checks and modifications:

    - If the URI either does not contain a protocol, uses the
      ``file://`` protocol, or is a PathLike object, the handler name is
      ``file`` and the URI is converted to a :class:`pathlib.Path`
      object.

    - If the URI is an SCP-style URI (``user@host:path``), the handler
      name is ``git`` and the URI is not modified.

    - If the URI contains nested protocols (e.g. ``git+file://repo``),
      the outermost protocol (i.e. ``git``) is split off and becomes the
      handler name. The rest of the URI (``file://repo``) is returned
      unmodified.
    """
    if _looks_like_local_path(uri):
        return "file", pathlib.Path(uri)
    if isinstance(uri, str) and _looks_like_scp(uri):
        return "git", uri

    uri = os.fspath(uri)
    pattern = r"^(\w+)([+:])"
    prefix_match = re.search(pattern, uri)

    if prefix_match:
        handler_name = prefix_match.group(1)
        if prefix_match.group(2) == "+":
            uri = uri[len(prefix_match.group(0)) :]
        elif handler_name == "file":
            if match := re.match(r"^file://(?:localhost)?/", uri):
                uri = uri[len(match.group(0)) :]
            else:
                raise ValueError(f"Invalid non-local file URI: {uri}")
            uri = pathlib.Path(
                "/" * (not sys.platform.startswith("win")) + uri
            )
    else:
        handler_name = "file"
        uri = pathlib.Path(uri)
    return (handler_name, uri)


def load_entrypoint(handler_name: str) -> type[FileHandler]:
    eps = metadata.entry_points(
        group="capellambse.filehandler", name=handler_name
    )
    if not eps:
        raise ValueError(f"Unknown file handler {handler_name}")
    return next(iter(eps)).load()


def get_filehandler(path: str | os.PathLike, **kwargs: t.Any) -> FileHandler:
    handler_name, path = split_protocol(path)
    handler = load_entrypoint(handler_name)
    return handler(path, **kwargs)
