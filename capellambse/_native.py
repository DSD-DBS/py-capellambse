# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Facilities for working with a native Capella instance."""
from __future__ import annotations

__all__ = ["ARGS_CMDLINE", "native_capella"]

import collections.abc as cabc
import contextlib
import dataclasses
import errno
import logging
import pathlib
import shutil
import subprocess
import tempfile
import typing as t

import capellambse

_LOGGER = logging.getLogger(__name__)

_Runner = t.Union["_SimpleRunner", "_DockerRunner"]
_COMMON_ARGS: t.Final = (
    "-nosplash",
    "-consolelog",
    "-forceimport",
    "-input",
    "main_model",
)
_ARG_WORKSPACE: t.Final = "-data"
_ARG_PROJECT: t.Final = "-import"

ARGS_CMDLINE: t.Final = (
    "-application",
    "org.polarsys.capella.core.commandline.core",
)


@contextlib.contextmanager
def native_capella(
    model: capellambse.MelodyModel,
    *,
    exe: str | pathlib.Path | None = None,
    docker: str | None = None,
) -> cabc.Iterator[_NativeCapella]:
    with contextlib.ExitStack() as stack:
        workspace = tempfile.TemporaryDirectory(prefix="workspace.")
        workspace_path = pathlib.Path(stack.enter_context(workspace))
        _LOGGER.debug("Creating workspace at %s", workspace_path)

        project = model._loader.write_tmp_project_dir()
        project_path = stack.enter_context(project)
        _LOGGER.debug("Project files written to %s", project_path)

        assert model.info.capella_version
        if exe:
            if isinstance(exe, str):
                exe = exe.replace("{VERSION}", model.info.capella_version)
            runner: _Runner = _SimpleRunner(exe)
        elif docker:
            docker = docker.replace("{VERSION}", model.info.capella_version)
            runner = _DockerRunner(docker)
        else:
            assert False

        yield _NativeCapella(project_path, workspace_path, runner)


@dataclasses.dataclass
class _NativeCapella:
    project: pathlib.Path
    workspace: pathlib.Path
    __runner: _Runner

    def __call__(
        self, *args: str | pathlib.Path
    ) -> subprocess.CompletedProcess:
        try:
            return self.__runner(self.workspace, self.project, *args)
        except subprocess.CalledProcessError as err:
            _LOGGER.error(
                "Native Capella failed with code %d\n%s",
                err.returncode,
                err.stdout,
            )
            raise


class _SimpleRunner:
    def __init__(self, path: str | pathlib.Path) -> None:
        path = pathlib.Path(path)
        if path.is_absolute():
            self.path = path
        else:
            if path.parent == pathlib.Path("."):
                exe = shutil.which(path.name)
                if exe is None:
                    raise FileNotFoundError(
                        errno.ENOENT, f"Not found in PATH: {path.name}"
                    )
                self.path = pathlib.Path(exe)
            elif path.exists():
                self.path = path.resolve()
            else:
                raise FileNotFoundError(
                    errno.ENOENT, f"File not found: {path.name}"
                )

    def __call__(
        self,
        workspace: pathlib.Path,
        project: pathlib.Path,
        /,
        *args: str | pathlib.Path,
    ) -> subprocess.CompletedProcess:
        cmd: list[str | pathlib.Path] = [
            self.path,
            *_COMMON_ARGS,
            _ARG_WORKSPACE,
            workspace,
            _ARG_PROJECT,
            project / "main_model",
            *args,
        ]
        _LOGGER.debug("Running native Capella with command %r", cmd)
        return subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True,
            text=True,
        )


class _DockerRunner:
    def __init__(self, image: str) -> None:
        self.image = image

    def __call__(
        self,
        workspace: pathlib.Path,
        project: pathlib.Path,
        /,
        *args: str | pathlib.Path,
    ) -> subprocess.CompletedProcess:
        cmd: list[str | pathlib.Path] = [
            "docker",
            "run",
            "--rm",
            "--detach=false",
            f"-v{workspace}:/workspace",
            f"-v{project}:/model",
            self.image,
            *_COMMON_ARGS,
            _ARG_WORKSPACE,
            "/workspace",
            _ARG_PROJECT,
            "/model/main_model",
            *args,
        ]
        _LOGGER.debug("Running Capella in Docker with command %r", cmd)
        return subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True,
            text=True,
        )
