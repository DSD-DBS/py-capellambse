# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Facilities for working with a native Capella instance."""
from __future__ import annotations

__all__ = ["ARGS_CMDLINE", "native_capella"]

import collections.abc as cabc
import contextlib
import dataclasses
import errno
import json
import logging
import os
import pathlib
import random
import shutil
import string
import subprocess
import tempfile
import typing as t

import capellambse

_LOGGER = logging.getLogger(__name__)

_Runner = t.Union["_SimpleRunner", "_DockerRunner"]
_COMMON_ARGS: t.Final = (
    "--launcher.suppressErrors",
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
    """Prepare for running a native Capella instance.

    This context manager prepares a temporary workspace and project
    directory, and provides a function for running a native Capella
    instance with the given arguments.

    It currently supports two ways of running a native Capella instance:

    - Using a native executable, by using the ``exe`` argument to
      specify the path to the executable, or the name of the executable
      if it is in the ``PATH``.
    - Using a Docker image, by specifying the image name with the
      ``docker`` argument.

    Both argument values may be strings containing a ``{VERSION}``
    placeholder, which will be replaced with the Capella version of the
    given model. Note that no substitution will be performed if the
    argument is a :class:`pathlib.Path` object.

    Additionally, to facilitate writing wrapper scripts, the process
    specified by the ``exe`` argument is invoked with the following
    additional environment variables:

    - ``CAPELLA_PROJECT``: The path to the project directory
    - ``CAPELLA_WORKSPACE``: The path to the workspace directory
    - ``CAPELLA_VERSION``: The Capella version of the given model

    The context manager yields a callable that can be used to run the
    native Capella instance. The callable takes the arguments to pass
    to Capella as positional arguments, and returns a
    :class:`subprocess.CompletedProcess` object with the result of the
    execution.

    Some cases may require multiple internal subprocess calls, in which
    case either of them may fail. The caller can therefore not rely on a
    :class:`subprocess.CalledProcessError` to belong to the actual
    Capella execution; it may belong to any of the preparation or
    cleanup calls as well. However, the CompletedProcess object returned
    in case of success always belongs to the Capella process.
    """
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
            runner: _Runner = _SimpleRunner(exe, model.info.capella_version)
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
    def __init__(self, path: str | pathlib.Path, capella_version: str) -> None:
        self.capella_version = capella_version
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
        env = os.environ | {
            "CAPELLA_PROJECT": str(project),
            "CAPELLA_WORKSPACE": str(workspace),
            "CAPELLA_VERSION": self.capella_version,
        }
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
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True,
            text=True,
        )


class _DockerRunner:
    def __init__(self, image: str) -> None:
        self.image = image
        self.entrypoint = self.get_entrypoint()

    def __call__(
        self,
        workspace: pathlib.Path,
        project: pathlib.Path,
        /,
        *args: str | pathlib.Path,
    ) -> subprocess.CompletedProcess:
        container_name = "capellambse-" + "".join(
            random.choice(string.ascii_lowercase) for i in range(5)
        )
        with self.start_container(container_name):
            self.copy_files_to_container(
                workspace, "/workspace", container_name
            )
            self.copy_files_to_container(project, "/model", container_name)

            capella = self.run_capella_in_container(
                container_name, self.entrypoint, *args
            )

            self.copy_files_from_container(
                "/workspace/.", workspace, container_name
            )
            self.copy_files_from_container("/model/.", project, container_name)

        return capella

    def get_entrypoint(self) -> list[str]:
        subprocess.run(["docker", "pull", self.image], check=True)
        proc = subprocess.run(
            ["docker", "inspect", self.image],
            check=True,
            stdout=subprocess.PIPE,
            encoding="utf-8",
        )
        parsed_output = json.loads(proc.stdout)[0]
        ep = parsed_output["Config"]["Entrypoint"]
        if not ep:
            raise ValueError(f"Docker image has no entrypoint: {self.image}")
        return ep

    @contextlib.contextmanager
    def start_container(self, name: str) -> cabc.Iterator[None]:
        _LOGGER.debug("Starting container %s from %s", name, self.image)
        with subprocess.Popen(
            [
                "docker",
                "run",
                "--rm",
                "-i",
                "--entrypoint",
                "/bin/sh",
                "--name",
                name,
                self.image,
                "-ec",
                "echo OK; read REPLY || true",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        ) as process:
            assert process.stdin is not None is not process.stdout
            try:
                if process.stdout.readline() != b"OK\n":
                    raise RuntimeError(
                        f"Failed handshake with container image {self.image}"
                    )

                _LOGGER.debug("Started container %s", name)
                yield
            finally:
                _LOGGER.debug("Stopping container %s", name)
                process.communicate(b"\n", timeout=30)

    def run_capella_in_container(
        self,
        container_name: str,
        entrypoint: cabc.Sequence[str],
        *args: str | pathlib.Path,
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                "docker",
                "exec",
                f"{container_name}",
                *entrypoint,
                *_COMMON_ARGS,
                _ARG_WORKSPACE,
                "/workspace",
                _ARG_PROJECT,
                "/model/main_model",
                *args,
            ],
            check=True,
        )

    def copy_files_to_container(
        self, directory: pathlib.Path, destination: str, container_name: str
    ) -> None:
        subprocess.check_call(
            [
                "docker",
                "cp",
                f"{directory}",
                f"{container_name}:{destination}",
            ],
        )

    def copy_files_from_container(
        self, directory: str, destination: pathlib.Path, container_name: str
    ) -> None:
        subprocess.check_call(
            [
                "docker",
                "cp",
                f"{container_name}:{directory}",
                f"{destination}",
            ],
        )
