# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

__all__ = [
    "MemoryFile",
    "MemoryFileHandler",
    "MemoryFilePath",
]

import collections.abc as cabc
import io
import os
import pathlib
import typing as t

from capellambse import helpers

from . import abc


class MemoryFileHandler(abc.FileHandler):
    """A file handler that stores data in memory."""

    def __init__(
        self,
        path: str | os.PathLike = "memory:",
        *,
        subdir: str | pathlib.PurePosixPath = "/",
    ) -> None:
        """Initialize a new memory file handler.

        Parameters
        ----------
        path
            An optional path to a directory to use as fallback. Opened
            files' contents will be prepopulated with the contents of
            files from this directory.
        subdir
            An optional path to prepend to all opened (physical) files.
        """
        if path != "memory:":
            raise ValueError(f"Unsupported path for MemoryFileHandler: {path}")
        super().__init__(path, subdir=subdir)

        self._data: dict[pathlib.PurePosixPath, bytearray] = {}

    def open(
        self,
        filename: str | pathlib.PurePosixPath,
        mode: t.Literal["r", "rb", "w", "wb"] = "rb",
    ) -> t.BinaryIO:
        path = helpers.normalize_pure_path(filename, base=self.subdir)
        if "w" in mode:
            self._data[path] = bytearray()
            return MemoryFile(self._data[path], "w")  # type: ignore[abstract]

        try:
            return MemoryFile(self._data[path], "r")  # type: ignore[abstract]
        except KeyError:
            pass
        raise FileNotFoundError(path)

    def __repr__(self) -> str:
        return (
            f"<memory with {len(self._data)} files: "
            f"{', '.join(map(str, self._data.keys()))}>"
        )

    @property
    def rootdir(self) -> MemoryFilePath:
        return MemoryFilePath(self, pathlib.PurePosixPath("."))

    def iterdir(
        self, path: str | pathlib.PurePosixPath = "/", /
    ) -> cabc.Iterator[MemoryFilePath]:
        path = helpers.normalize_pure_path(path)
        for p in self._data:
            if p.parent == path:
                yield MemoryFilePath(self, p)

    def all_files(self) -> dict[pathlib.PurePosixPath, bytes]:
        return {k: bytes(v) for k, v in self._data.items()}


class MemoryFile(t.BinaryIO):
    def __init__(self, data: bytearray, mode: t.Literal["r", "w"]) -> None:
        self._data = data
        self._mode = mode
        self._pos = 0

    def __enter__(self) -> MemoryFile:
        return self

    def __exit__(self, *args: t.Any) -> None:
        pass

    def write(self, s: bytes | bytearray) -> int:  # type: ignore[override]
        if self._mode != "w":
            raise io.UnsupportedOperation("not writable")
        self._data[self._pos : self._pos + len(s)] = s
        self._pos += len(s)
        return len(s)

    def read(self, n: int = -1) -> bytes:
        if self._mode != "r":
            raise io.UnsupportedOperation("not readable")
        if n < 0:
            n = len(self._data) - self._pos
        result = self._data[self._pos : self._pos + n]
        self._pos += len(result)
        return bytes(result)


class MemoryFilePath(abc.FilePath[MemoryFileHandler]):
    def is_dir(self) -> bool:
        return not self.is_file()

    def is_file(self) -> bool:
        return self._path in self._parent._data
