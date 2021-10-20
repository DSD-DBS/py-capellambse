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

import hashlib
import io
import logging
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import typing as t
import urllib.parse

import capellambse.helpers

from .. import modelinfo
from . import FileHandler

LOGGER = logging.getLogger(__name__)


class GitFileHandler(FileHandler):
    """File handler for ``git://`` and related protocols."""

    username: str
    password: str
    identity_file: str
    known_hosts_file: str
    cache_dir: pathlib.Path

    __lfsfiles: frozenset[str]

    def __init__(
        self,
        path: bytes | str | os.PathLike,
        entrypoint: str,
        revision: str = "HEAD",
        username: str = "",
        password: str = "",
        identity_file: str = "",
        known_hosts_file: str = "",
        disable_cache: bool = False,
        update_cache: bool = True,
    ) -> None:
        super().__init__(path, entrypoint)
        self.revision = revision
        self.entrypoint = entrypoint
        self.disable_cache = disable_cache
        self.username = username
        self.password = password
        self.identity_file = identity_file
        self.known_hosts_file = known_hosts_file
        self.update_cache = update_cache

        self.__init_cache_dir()

        self.__lfsfiles = frozenset(
            self.__git("lfs", "ls-files", "-n")
            .decode("utf-8", errors="surrogateescape")
            .splitlines()
        )

    def open(
        self,
        filename: pathlib.PurePosixPath,
        mode: t.Literal["r", "rb", "w", "wb"] = "rb",
    ) -> io.BytesIO:
        if "w" in mode:
            raise TypeError("Writing to git repositories is not supported!")

        path = capellambse.helpers.normalize_pure_path(filename)
        if str(path) in self.__lfsfiles:
            content = self.__open_from_lfs(path)
        else:
            content = self.__open_from_index(path)
        return io.BytesIO(content)

    def get_model_info(self) -> modelinfo.ModelInfo:
        def revparse(*args: str) -> str:
            return (
                self.__git("rev-parse", *args, silent=True)
                .decode("utf-8", errors="surrogateescape")
                .strip()
            )

        if isinstance(self.path, bytes):
            title = self.path.decode("utf-8", errors="replace").rsplit(
                "/", maxsplit=1
            )[-1]
            url = self.path.decode("utf-8", errors="surrogateescape")
        else:
            title = str(self.path).rsplit("/", maxsplit=1)[-1]
            url = str(self.path)
        if title.endswith(".git"):
            title = title[: -len(".git")]

        return modelinfo.ModelInfo(
            branch=revparse("--abbrev-ref", self.revision),
            title=title,
            url=url,
            short_rev=revparse("--short", self.revision),
            rev_hash=revparse(self.revision),
        )

    def __get_git_env(self) -> dict[str, str]:
        git_env = os.environ.copy()
        if not os.environ.get("GIT_ASKPASS"):
            path_to_askpass = (
                pathlib.Path(__file__).parent / "git_askpass.py"
            ).absolute()

            git_env["GIT_ASKPASS"] = str(path_to_askpass)

            try:
                os.chmod(path_to_askpass, 0o755)
            except OSError:
                LOGGER.info(
                    "Setting permission 755 for GIT_ASKPASS file failed"
                )

        if self.username and self.password:
            git_env["GIT_USERNAME"] = self.username
            git_env["GIT_PASSWORD"] = self.password

        if self.identity_file and self.known_hosts_file:
            ssh_command = [
                "ssh",
                "-i",
                self.identity_file,
                f"-oUserKnownHostsFile={self.known_hosts_file}",
            ]
            git_env["GIT_SSH_COMMAND"] = shlex.join(ssh_command)

        return git_env

    def __init_cache_dir(self) -> None:
        if isinstance(self.path, bytes):
            is_file_uri = self.path.startswith(b"file://")
        else:
            is_file_uri = str(self.path).startswith("file://")

        if is_file_uri:
            self.__init_cache_dir_local()
        else:
            self.__init_cache_dir_remote()

    def __init_cache_dir_local(self) -> None:
        if isinstance(self.path, bytes):
            uri = self.path.decode("utf-8", errors="surrogateescape")
        else:
            uri = str(self.path)
        parts = urllib.parse.urlparse(uri)
        if parts.netloc and parts.netloc != "localhost":
            raise ValueError(f"Unsupported file:// URL netloc: {parts.netloc}")

        path = urllib.parse.unquote(parts.path)
        self.cache_dir = pathlib.Path("/", path).resolve()

    def __init_cache_dir_remote(self) -> None:
        slug_pattern = '[\x00-\x1F\x7F"*/:<>?\\|]+'
        if isinstance(self.path, bytes):
            path_hash = hashlib.sha256(self.path).hexdigest()
            path_slug = re.sub(
                slug_pattern.encode("ascii"), b"-", self.path
            ).decode("utf-8", errors="surrogateescape")
        else:
            path_hash = hashlib.sha256(
                str(self.path).encode("utf-8", errors="surrogatepass")
            ).hexdigest()
            path_slug = re.sub(slug_pattern, "-", str(self.path))
        self.cache_dir = pathlib.Path(
            capellambse.dirs.user_cache_dir,
            "models",
            path_hash,
            path_slug,
        )

        if self.cache_dir.exists() and self.disable_cache:
            shutil.rmtree(str(self.cache_dir))

        if not (self.cache_dir / "config").exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            LOGGER.debug("Cloning %r to %s", self.path, self.cache_dir)
            self.__git("clone", self.path, ".", "--bare", "--mirror")
        elif self.update_cache:
            LOGGER.debug("Updating cache at %s", self.cache_dir)
            self.__git("fetch")

    def __open_from_index(self, filename: pathlib.PurePosixPath) -> bytes:
        return self.__git("cat-file", "blob", f"{self.revision}:{filename}")

    def __open_from_lfs(self, filename: pathlib.PurePosixPath) -> bytes:
        lfsinfo = self.__open_from_index(filename)
        return self.__git("lfs", "smudge", "--", filename, input=lfsinfo)

    def __git(self, *cmd: t.Any, silent: bool = False, **kw: t.Any) -> bytes:
        LOGGER.debug("Running command %s", cmd)
        returncode = 0
        stderr = None
        try:
            proc = subprocess.run(
                ["git"] + [str(i) for i in cmd],
                capture_output=True,
                check=True,
                cwd=self.cache_dir,
                env=self.__get_git_env(),
                **kw,
            )
            returncode = proc.returncode
            stderr = proc.stderr
            return proc.stdout
        except subprocess.CalledProcessError as err:
            returncode = err.returncode
            stderr = err.stderr
            raise
        finally:
            err_level = (logging.ERROR, logging.DEBUG)[silent]
            ret_level = (logging.DEBUG, err_level)[bool(returncode and stderr)]
            if stderr:
                for line in stderr.decode("utf-8").splitlines():
                    LOGGER.getChild("git").log(err_level, "%s", line)
            LOGGER.log(ret_level, "Exit status: %d", returncode)
