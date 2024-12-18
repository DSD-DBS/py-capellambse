# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import contextlib
import logging
import os
import pathlib
import typing as t

from capellambse import helpers

from . import abc

LOGGER = logging.getLogger(__name__)


class LocalFileHandler(abc.FileHandler):
    def __init__(
        self,
        path: str | os.PathLike,
        *,
        subdir: str | pathlib.PurePosixPath = "/",
    ) -> None:
        path = pathlib.Path(path, helpers.normalize_pure_path(subdir))

        super().__init__(path)
        self.__transaction: set[pathlib.PurePosixPath] | None = None
        assert isinstance(self.path, pathlib.Path)

    def open(
        self,
        filename: str | pathlib.PurePosixPath,
        mode: t.Literal["r", "rb", "w", "wb"] = "rb",
    ) -> t.BinaryIO:
        assert isinstance(self.path, pathlib.Path)
        normpath = helpers.normalize_pure_path(filename)
        if "w" not in mode or self.__transaction is None:
            path = self.path / normpath
            return path.open("rb")

        if normpath in self.__transaction:
            raise RuntimeError(
                f"File already written in this transaction: {normpath}"
            )
        self.__transaction.add(normpath)
        tmppath = _tmpname(normpath)
        return (self.path / tmppath).open("wb")

    @contextlib.contextmanager
    def write_transaction(
        self, *, dry_run: bool = False, **kw: t.Any
    ) -> t.Generator[t.Mapping[str, t.Any], None, None]:
        """Start a write transaction.

        During the transaction, file writes are redirected to temporary
        files next to the target files, and if the transaction ends
        successfully they are moved to their destinations all at once.

        Parameters
        ----------
        dry_run
            Discard the temporary files after a successful transaction
            instead of committing them to their destinations.
        **kw
            Additional arguments are ignored.
        """
        assert isinstance(self.path, pathlib.Path)

        with super().write_transaction(**kw) as unused_kw:
            if self.__transaction is not None:
                raise RuntimeError("Another transaction is already open")
            self.__transaction = set()

            try:
                yield unused_kw
            except:
                LOGGER.debug("Aborting transaction due to exception")
                dry_run = True
                raise
            finally:
                for file in self.__transaction:
                    tmpname = _tmpname(file)
                    if dry_run:
                        LOGGER.debug("Removing temporary file %s", tmpname)
                        (self.path / tmpname).unlink()
                    else:
                        LOGGER.debug("Committing file %s to %s", tmpname, file)
                        (self.path / tmpname).replace(self.path / file)
                self.__transaction = None

    @property
    def rootdir(self) -> LocalFilePath:
        return LocalFilePath(self, pathlib.PurePosixPath("/"))

    def iterdir(
        self, subdir: str | pathlib.PurePosixPath = "."
    ) -> t.Iterator[LocalFilePath]:
        assert isinstance(self.path, pathlib.Path)
        subdir = helpers.normalize_pure_path(subdir)
        for p in self.path.joinpath(subdir).iterdir():
            yield LocalFilePath(
                self,
                pathlib.PurePosixPath(p.relative_to(self.path)),
            )


def _tmpname(filename: pathlib.PurePosixPath) -> pathlib.PurePosixPath:
    prefix = "."
    suffix = ".tmp"
    name = filename.name[0 : 255 - (len(prefix) + len(suffix))]
    return filename.with_name(f"{prefix}{name}{suffix}")


class LocalFilePath(abc.FilePath[LocalFileHandler]):
    def is_dir(self) -> bool:
        base = t.cast(pathlib.Path, self._parent.path)
        path = base.joinpath(self._path).resolve()
        return path.is_dir()

    def is_file(self) -> bool:
        base = t.cast(pathlib.Path, self._parent.path)
        path = base.joinpath(self._path).resolve()
        return path.is_file()
