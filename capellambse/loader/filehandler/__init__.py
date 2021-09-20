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
from __future__ import annotations

import abc
import logging
import os
import pathlib
import re
import typing as t
from importlib import metadata

from capellambse.loader.modelinfo import ModelInfo

LOGGER = logging.getLogger(__name__)


def get_filehandler(
    path: t.Union[bytes, os.PathLike, str], **kwargs: t.Any
) -> FileHandler:
    pattern = r"^(\w+\+)?(\w+:)//"
    prefix_match: t.Optional[re.Match[t.Any]]
    if isinstance(path, bytes):
        prefix_match = re.search(pattern.encode("ascii"), path)
    else:
        prefix_match = re.search(pattern, str(path))

    if prefix_match:
        handler_name = (prefix_match.group(1) or prefix_match.group(2))[:-1]
        path = os.fspath(path)[len(handler_name) + 1 :]
    else:
        handler_name = "file"

    if isinstance(handler_name, bytes):
        handler_name = handler_name.decode("ascii")

    try:
        ep = next(
            i
            for i in metadata.entry_points()["capellambse.filehandler"]
            if i.name == handler_name
        )
    except StopIteration:
        raise ValueError(f"Unknown file handler {handler_name}") from None

    handler: t.Type[FileHandler] = ep.load()
    return handler(path, **kwargs)


class FileHandler(metaclass=abc.ABCMeta):
    path: t.Union[bytes, os.PathLike, str]
    entrypoint: str

    def __init__(
        self,
        path: t.Union[bytes, os.PathLike, str],
        entrypoint: str,
        **kw: t.Any,
    ) -> None:
        super().__init__(**kw)  # type: ignore[call-arg]
        self.path = path
        self.entrypoint = entrypoint

    @abc.abstractmethod
    def get_model_info(self) -> ModelInfo:
        pass

    @abc.abstractmethod
    def open(
        self,
        filename: pathlib.PurePosixPath,
        mode: t.Literal["r", "rb", "w", "wb"] = "rb",
    ) -> t.BinaryIO:
        pass
