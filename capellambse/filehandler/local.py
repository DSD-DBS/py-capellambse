# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import contextlib
import logging
import os
import pathlib
import subprocess
import typing as t

from capellambse import helpers
from capellambse.loader.modelinfo import ModelInfo

from . import FileHandler

LOGGER = logging.getLogger(__name__)


class LocalFileHandler(FileHandler):
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
            return t.cast(t.BinaryIO, path.open(mode))

        if normpath in self.__transaction:
            raise RuntimeError(
                f"File already written in this transaction: {normpath}"
            )
        self.__transaction.add(normpath)
        tmppath = _tmpname(normpath)
        return t.cast(t.BinaryIO, (self.path / tmppath).open(mode))

    def get_model_info(self) -> ModelInfo:
        assert isinstance(self.path, pathlib.Path)
        if (self.path / ".git").exists():
            return ModelInfo(
                branch=self.__git_rev_parse("--abbrev-ref", "HEAD"),
                title=self.path.name,
                url=self.__git_get_remote_url(),
                rev_hash=self.__git_rev_parse("HEAD"),
            )
        return ModelInfo(title=self.path.name)

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

    def __git_rev_parse(self, *options: str) -> str | None:
        assert isinstance(self.path, pathlib.Path)
        try:
            return (
                subprocess.run(
                    ["git", "rev-parse", *options],
                    cwd=self.path,
                    check=True,
                    capture_output=True,
                )
                .stdout.decode("utf-8")
                .strip()
            )
        except subprocess.CalledProcessError:
            LOGGER.warning(
                "Git rev-parse with options %s failed",
                options,
            )
            return None

    def __git_get_remote_url(self) -> str | None:
        assert isinstance(self.path, pathlib.Path)
        try:
            remotes = (
                subprocess.run(
                    ["git", "remote"],
                    cwd=self.path,
                    check=True,
                    capture_output=True,
                )
                .stdout.decode("utf-8")
                .splitlines()
            )
            return (
                subprocess.run(
                    ["git", "remote", "get-url", remotes[0]],
                    cwd=self.path,
                    check=True,
                    capture_output=True,
                )
                .stdout.decode("utf-8")
                .strip()
            )
        except (IndexError, subprocess.CalledProcessError):
            return None


def _tmpname(filename: pathlib.PurePosixPath) -> pathlib.PurePosixPath:
    prefix = "."
    suffix = ".tmp"
    name = filename.name[0 : 255 - (len(prefix) + len(suffix))]
    return filename.with_name(f"{prefix}{name}{suffix}")
