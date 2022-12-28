# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
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
import re
import typing as t
import urllib.parse

import requests

from capellambse import helpers, loader

from . import FileHandler


class DownloadStream(t.BinaryIO):
    __stream: cabc.Iterator[bytes]
    __buffer: memoryview

    def __init__(
        self, session: requests.Session, url: str, chunk_size: int = 1024**2
    ) -> None:
        self.url = url
        self.chunk_size = chunk_size

        response = session.get(self.url, stream=True)
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
        headers: (
            dict[str, str]
            | requests.structures.CaseInsensitiveDict[str]
            | None
        ) = None,
        subdir: str | pathlib.PurePosixPath = "/",
    ) -> None:
        """Connect to a remote server through HTTP or HTTPS.

        This file handler supports three ways of specifying a URL:

        1.  If a plain URL is passed, the requested file name is
            appended after a forward slash ``/``.
        2.  If the URL contains ``%s``, it will be replaced by the
            requested file name, instead of appending it at the end.
            This allows for example to pass query parameters after the
            file name. File names are percent-escaped as implemented by
            ``urllib.parse.quote``.
        3.  The sequence ``%q`` is replaced similar to ``%s``, but the
            forward slash ``/`` is not considered a safe character and
            is percent-escaped as well.

        Examples: When requesting the file name ``demo/my model.aird``,
        ...

        - ``https://example.com/~user`` as ``path`` results in the URL
          ``https://example.com/~user/demo/my%20model.aird``
        - ``https://example.com/~user/%s`` results in
          ``https://example.com/~user/demo/my%20model.aird``
        - ``https://example.com/?file=%q`` results in
          ``https://example.com/?file=demo%2Fmy%20model.aird``

        Note that the file name that is inserted into the URL will never
        start with a forward slash. This means that a URL like
        ``https://example.com%s`` will not work; you need to hard-code
        the slash at the appropriate place.

        This also applies to the ``%q`` escape. If the server expects
        the file name argument to start with a slash, hard-code a
        percent-escaped slash in the URL. For example, instead of
        ``...?file=%q`` use ``...?file=%2F%q``.

        Parameters
        ----------
        path
            The base URL to fetch files from. Must start with
            ``http://`` or ``https://``. See above for how to specify
            complex URLs.
        username
            The username for HTTP Basic Auth.
        password
            The password for HTTP Basic Auth.
        headers
            Additional HTTP headers to send to the server.
        subdir
            Prepend this path to all requested files. It is subject to
            the same file name escaping rules explained above.
        """
        if not isinstance(path, str):
            raise TypeError(
                "HTTPFileHandler requires a str path, not"
                f" {type(path).__name__}"
            )
        if bool(username) != bool(password):
            raise ValueError(
                "Either both username and password must be given, or neither"
            )

        if "%s" not in path and "%q" not in path:
            path = path.rstrip("/") + "/%s"

        super().__init__(path, subdir=subdir)

        self.session = requests.Session()
        self.session.headers.update(headers or {})
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
        fname = self.subdir / helpers.normalize_pure_path(filename)
        fname_str = str(fname).lstrip("/")
        replace = {
            "%s": urllib.parse.quote(fname_str, safe="/"),
            "%q": urllib.parse.quote(fname_str, safe=""),
        }
        url = re.sub("%[sq]", lambda m: replace[m.group(0)], self.path)
        assert url != self.path
        return DownloadStream(  # type: ignore[abstract] # false-positive
            self.session, url
        )

    def write_transaction(self, **kw: t.Any) -> t.NoReturn:
        raise NotImplementedError(
            "Write transactions for HTTP(S) are not implemented"
        )
