# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

__all__ = [
    "FileHandler",
    "TransactionClosedError",
    "get_filehandler",
]

import logging
import os
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
    if _looks_like_local_path(uri):
        return "file", uri
    if isinstance(uri, str) and _looks_like_scp(uri):
        return "git", uri

    uri = os.fspath(uri)
    pattern = r"^(\w+)([+:])"
    prefix_match = re.search(pattern, uri)

    if prefix_match:
        handler_name = prefix_match.group(1)
        if prefix_match.group(2) == "+":
            uri = uri[len(prefix_match.group(0)) :]
    else:
        handler_name = "file"
    return (handler_name, uri)


if sys.version_info < (3, 10):

    def load_entrypoint(handler_name: str) -> type[FileHandler]:
        try:
            ep = next(
                i
                for i in metadata.entry_points()["capellambse.filehandler"]
                if i.name == handler_name
            )
        except StopIteration:
            raise ValueError(f"Unknown file handler {handler_name}") from None
        return ep.load()

else:

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
