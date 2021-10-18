# Copyright 2021 DB Netz AG
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import os
import pathlib
import subprocess
import typing as t

import capellambse.helpers
from capellambse.loader.modelinfo import ModelInfo

from . import FileHandler

LOGGER = logging.getLogger(__name__)


class LocalFileHandler(FileHandler):
    def __init__(
        self,
        path: t.Union[bytes, os.PathLike, str],
        entrypoint: str = "",
    ) -> None:
        if isinstance(path, bytes):
            path = path.decode("utf-8")

        path = pathlib.Path(path)

        if not entrypoint:
            entrypoint = path.name
            path = path.parent

        super().__init__(path, entrypoint)
        assert isinstance(self.path, pathlib.Path)

    def open(
        self,
        filename: pathlib.PurePosixPath,
        mode: t.Literal["r", "rb", "w", "wb"] = "rb",
    ) -> t.BinaryIO:
        assert isinstance(self.path, pathlib.Path)
        path = self.path / capellambse.helpers.normalize_pure_path(filename)
        return t.cast(t.BinaryIO, path.open(mode))

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

    def __git_rev_parse(self, *options: str) -> t.Optional[str]:
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

    def __git_get_remote_url(self) -> t.Optional[str]:
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
        except IndexError:
            return None
        except subprocess.CalledProcessError:
            return None
