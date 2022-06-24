# Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=abstract-method, useless-suppression
# For some reason, pylint in Github CI didn't get the memo that these aren't
# actually abstract methods. Other pylint installations seem to agree that
# implementing these methods isn't necessary. So we just ignore the warning
# about that here.
# TODO Revisit this decision some time in the future

from __future__ import annotations

import collections.abc as cabc
import itertools
import os
import pathlib
import typing as t
import urllib.parse

import requests

from capellambse import helpers, loader

from . import FileHandler


class DownloadStream(t.BinaryIO):
    __stream: cabc.Iterator[bytes]
    __buffer: memoryview

    def __init__(self, url: str, chunk_size: int = 1024**2) -> None:
        self.url = url
        self.chunk_size = chunk_size

        response = requests.get(self.url, stream=True)
        if response.status_code == 404:
            raise FileNotFoundError(url)
        response.raise_for_status()
        self.__stream = response.iter_content(
            self.chunk_size, decode_unicode=False
        )
        self.__buffer = memoryview(b"")

    def __enter__(self) -> DownloadStream:
        return self

    def __exit__(self, *args: t.Any) -> None:
        self.close()

    def read(self, n: int = -1) -> bytes:
        if n == -1:
            return b"".join(itertools.chain((self.__buffer,), self.__stream))

        if not self.__buffer:
            try:
                self.__buffer = memoryview(next(self.__stream))
            except StopIteration:
                return b""

        chunk = bytes(self.__buffer[:n])
        self.__buffer = self.__buffer[n:]
        return chunk

    def readable(self) -> bool:
        return True

    def write(self, s: bytes | bytearray) -> int:
        raise TypeError("Cannot write to a read-only stream")

    def writable(self) -> bool:
        return False

    def close(self) -> None:
        del self.__stream
        del self.__buffer


class HTTPFileHandler(FileHandler):
    """A remote file handler that fetches files using HTTP GET."""

    def __init__(
        self,
        path: str | os.PathLike,
        username: str | None = None,
        password: str | None = None,
        *,
        subdir: str | pathlib.PurePosixPath = "/",
    ) -> None:
        if not isinstance(path, str):
            raise TypeError(
                f"HTTPFileHandler requires a str path, not {type(path).__name__}"
            )
        if bool(username) != bool(password):
            raise ValueError(
                "Either both username and password must be given, or neither"
            )
        if subdir != "/":
            raise ValueError("`subdir=` is not supported in HTTP(S)")
        super().__init__(path)

        self.session = requests.Session()
        if username and password:
            self.session.auth = (username, password)

    def get_model_info(self) -> loader.ModelInfo:
        assert isinstance(self.path, str)
        parts = urllib.parse.urlparse(self.path)
        return loader.ModelInfo(
            title=parts.path.rsplit("/", maxsplit=1)[-1],
            url=self.path,
        )

    def open(
        self,
        filename: str | pathlib.PurePosixPath,
        mode: t.Literal["r", "rb", "w", "wb"] = "rb",
    ) -> t.BinaryIO:
        if "w" in mode:
            raise NotImplementedError("Cannot upload to HTTP(S) locations")
        assert isinstance(self.path, str)
        fname_str = str(helpers.normalize_pure_path(filename))
        return DownloadStream(  # type: ignore[abstract] # false-positive
            "/".join((self.path, fname_str))
        )

    def write_transaction(self, **kw: t.Any) -> t.NoReturn:
        raise NotImplementedError(
            "Write transactions for HTTP(S) are not implemented"
        )
