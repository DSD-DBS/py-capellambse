# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import collections.abc as cabc
import errno
import io
import logging
import os
import pathlib
import typing as t
import weakref
import zipfile

from capellambse import helpers

from . import abc, get_filehandler

LOGGER = logging.getLogger(__name__)


class ZipFileHandler(abc.FileHandler):
    """File handler that can read from zip files.

    Parameters
    ----------
    path
        Location of the zip file. May contain a nested path, like
        ``zip+https://host.name/%s``, which will be resolved using an
        appropriate file handler.

        If ``zipname`` is not passed or is None, the path may include the zip
        file name as well, using either ``!`` or ``/`` as separator. For
        example, the following calls are equivalent:

        .. code-block:: python

           ZipFileHandler("zip+https://host.name/path/to/file.zip")
           ZipFileHandler("zip+https://host.name/path/to!file.zip")
           ZipFileHandler("zip+https://host.name/path/to/%s!file.zip")

        .. note::

           The ``%s`` replacement shown in this example is done by the
           underlying :class:`~capellambse.filehandler.http.HTTPFileHandler`,
           which is used to fetch the nested ``https://`` URL. Other nested
           protocols may require different syntax.)

        .. note::

           It is currently not possible to pass down arbitrary arguments to the
           underlying FileHandler other than the ``path``.
    zipname
        Name of the zip file in the above path.
    subdir
        A subdirectory inside the zip file to use as base directory.

        If the zip file contains only a single directory entry and no
        other files at the root, this directory is used as default. Pass
        ``subdir="."`` explicitly to override this behaviour.
    """

    def __init__(
        self,
        path: str | os.PathLike,
        zipname: str | pathlib.PurePosixPath | None = None,
        subdir: str | pathlib.PurePosixPath | None = None,
    ) -> None:
        super().__init__(path, subdir=subdir or ".")
        path = os.fspath(path)
        if path.startswith("zip://"):
            path = path.replace("zip", "file", 1)
        if zipname is None:
            if "!" in path:
                path, zipname = path.split("!", 1)
            elif "/" in path:
                path, zipname = path.rsplit("/", 1)
            else:
                path, zipname = ".", path

        slave = get_filehandler(path)
        file = slave.read_file(zipname)
        self.__file = zipfile.ZipFile(io.BytesIO(file))
        self.__fnz = weakref.finalize(self, self.__file.close)

        if subdir is None:
            subdir = os.path.commonprefix(self.__file.namelist())
            subdir = subdir[: subdir.rfind("/") + 1].rstrip("/")
            LOGGER.debug("Auto-selected base directory: %s", subdir)
            self.subdir = pathlib.PurePosixPath(subdir)

    def open(
        self,
        filename: str | pathlib.PurePosixPath,
        mode: t.Literal["r", "rb", "w", "wb"] = "rb",
    ) -> t.IO[bytes]:
        if "w" in mode:
            raise ValueError("Writing to zip files is not supported")

        filename = helpers.normalize_pure_path(filename, base=self.subdir)
        try:
            return self.__file.open(str(filename), "r")
        except KeyError:
            raise FileNotFoundError(errno.ENOENT, filename) from None

    @property
    def rootdir(self) -> abc.FilePath[ZipFileHandler]:
        return abc.FilePath(self, pathlib.PurePosixPath("."))

    def iterdir(
        self, path: str | pathlib.PurePosixPath = ".", /
    ) -> cabc.Iterator[abc.FilePath[ZipFileHandler]]:
        path, zpath = _normalize_path(path, self.subdir)
        for zsub in zipfile.Path(self.__file, zpath).iterdir():
            yield abc.FilePath(self, path / zsub.name)

    def is_dir(self, path: str | pathlib.PurePosixPath, /) -> bool:
        _, zpath = _normalize_path(path, self.subdir)
        return zipfile.Path(self.__file, zpath).is_dir()

    def is_file(self, path: str | pathlib.PurePosixPath, /) -> bool:
        _, zpath = _normalize_path(path, self.subdir)
        return zipfile.Path(self.__file, zpath).is_file()


def _normalize_path(
    path: str | pathlib.PurePosixPath, base: pathlib.PurePosixPath, /
) -> tuple[pathlib.PurePosixPath, str]:
    path = helpers.normalize_pure_path(path)
    zpath = str(base / path) + "/"
    if zpath == "./":
        zpath = ""
    return path, zpath
