# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import collections.abc as cabc
import errno
import io
import logging
import math
import os
import pathlib
import re
import sys
import typing as t
import urllib.parse

import requests

from capellambse import helpers, loader

from . import FileHandler

LOGGER = logging.getLogger(__name__)
RE_LINK_NEXT = re.compile("<(http.*)>; rel=(?P<quote>[\"']?)next(?P=quote)")
MAX_SEARCHED_JOBS = (
    int(os.environ.get("CAPELLAMBSE_GLART_MAX_JOBS", 1000)) or sys.maxsize
)


class GitlabArtifactsFiles(FileHandler):
    """Download files from Gitlab's artifacts hosting service.

    This file handler is roughly equivalent to an HTTPFileHandler with
    appropriate headers and the following URL::

        https://<path>/api/v4/projects/<project>/jobs/artifacts/<branch>/raw/<subdir>/%s?job_name=<job>

    One important difference is that this file handler will always use
    the latest successful job, regardless of the overall pipeline
    status, while an HTTPFileHandler with the above URL would only
    consider jobs from successful pipelines.

    This file handler uses several of the Gitlab CI/CD `pre-defined
    environment variables`__. Refer to the documentation for their exact
    meaning and behavior during CI runs, and see below for how they are
    used.

    __ https://docs.gitlab.com/ee/ci/variables/predefined_variables.html

    Parameters
    ----------
    path
        The base URL of the Gitlab server. Must start with one of
        ``glart://``, ``glart+http://`` or ``glart+https://``; the
        ``glart:`` prefix uses HTTPS to communicate with the server. May
        also be set to ``glart:`` (without a server name), which uses
        the ``$CI_SERVER_URL`` environment variable to find the
        instance; if that is not set, the public Gitlab instance at
        ``https://gitlab.com`` is used.

        Example: If your project is hosted at
        ``https://gitlab.example.com/my_username/my_cool_project``, use
        ``glart://gitlab.example.com`` as path argument.
    token
        A personal or project access token with ``read_api`` permission
        on the specified project. The following ways are supported for
        passing the token, which are checked in order:

        1. Directly via this argument.
        2. If the argument starts with a dollar sign (``$``), it is
           treated as the name of an environment variable that points to
           a file containing the token. This is compatible with
           variables of type "File" in Gitlab CI/CD.
        3. A file called ``gitlab_artifacts_token`` in the
           ``$CREDENTIALS_DIRECTORY``.
        4. The ``CI_JOB_TOKEN`` environment variable. This is intended
           for use in Gitlab pipelines, in order to avoid having to
           create explicit tokens. Note that your instance might be set
           up with restrictive default permissions for the job token.
    project
        The path (e.g. ``my_username/my_cool_project``) or numeric ID of the
        project to pull the artifacts from. Defaults to the
        ``$CI_PROJECT_ID`` environment variable, which Gitlab sets to
        the project currently executing a pipeline.
    branch
        The branch to pull artifacts from. Defaults to the value of the
        ``CI_DEFAULT_BRANCH`` environment variable, or ``main`` if that
        is unset. Ignored if a numeric ID is given for ``job``.
    job
        Name of the job to pull artifacts from. May also be a numeric
        job ID.

        The last 20 pipeline runs on the given branch are searched for a
        successful job with this name that has artifacts. If nothing is
        found, an exception is raised, and a numeric job ID has to be
        specified explicitly.
    subdir
        An optional path prefix inside the artifacts archive to prepend
        to all file names.

    See Also
    --------
    capellambse.filehandler.http.HTTPFileHandler :
        A general-purpose HTTP file handler.
    """

    def __init__(
        self,
        path: str,
        *,
        subdir: str | pathlib.PurePosixPath = "/",
        token: str | None = None,
        project: str | int | None = None,
        branch: str | None = None,
        job: str | int,
    ) -> None:
        super().__init__(path, subdir=subdir)

        self.__path = self.__resolve_path(path)
        self.__token = self.__resolve_token(token)
        self.__project = self.__resolve_project(project)
        self.__branch = branch or os.getenv("CI_DEFAULT_BRANCH") or "main"
        self.__job = self.__resolve_job(job)

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(path={self.__path!r}, token=<HIDDEN>,"
            f" project={self.__project!r}, branch={self.__branch!r},"
            f" job={self.__job!r}, subdir={self.subdir!r})"
        )

    @staticmethod
    def __resolve_path(path: str) -> str:
        if path in {"glart:", "glart://"}:
            if host := os.getenv("CI_SERVER_URL"):
                LOGGER.debug("Using current Gitlab instance: %s", host)
                return host
            else:
                LOGGER.debug("Using public Gitlab instance at gitlab.com")
                return "https://gitlab.com"

        if path.startswith("glart:"):
            return "https:" + path[6:]

        return path

    @classmethod
    def __resolve_token(cls, token: str | None) -> str:
        if token:
            return cls.__load_token_from_arg(token)

        if cred_dir := os.getenv("CREDENTIALS_DIRECTORY"):
            if token := cls.__load_token_from_credentials(cred_dir):
                return token

        if token := os.getenv("CI_JOB_TOKEN"):
            LOGGER.debug("Using the $CI_JOB_TOKEN")
            return token

        raise TypeError("Cannot connect to Gitlab: No 'token' found")

    @staticmethod
    def __load_token_from_arg(token: str) -> str:
        if not token.startswith("$"):
            return token

        try:
            filename = os.environ[token[1:]]
        except KeyError:
            raise ValueError(
                f"Token environment variable {token} is unset"
            ) from None

        try:
            contents = pathlib.Path(filename).read_text(encoding="ascii")
        except FileNotFoundError:
            raise ValueError(f"Token file from {token} not found") from None
        except OSError:
            raise ValueError(f"Cannot read token file from {token}") from None

        contents = contents.strip()
        if not contents:
            raise ValueError(f"Token file from {token} is empty")
        return contents

    @staticmethod
    def __load_token_from_credentials(cred_dir: str) -> str | None:
        cred_file = pathlib.Path(cred_dir, "gitlab_artifacts_token")
        try:
            token = cred_file.read_text(encoding="locale").strip()
        except OSError as err:
            LOGGER.debug("Cannot read token from %r: %s", cred_file, err)
        else:
            if token:
                LOGGER.debug("Using token from %s", cred_file)
                return token
            else:
                LOGGER.debug("Token file is empty: %s", cred_file)
        return None

    def __resolve_project(self, project: str | int | None) -> str | int:
        if isinstance(project, int):
            return project

        if project:
            project = urllib.parse.quote(project, safe="")
            info = self.__get(f"/projects/{project}")
            LOGGER.debug("Resolved project %r to ID %d", project, info["id"])
            return info["id"]

        if project := os.getenv("CI_PROJECT_ID"):
            return int(project)

        raise TypeError("No 'project' specified, and not running in Gitlab CI")

    def __resolve_job(self, job: str | int) -> int:
        if isinstance(job, int):
            return job

        for jobinfo in self.__iterget(
            f"/projects/{self.__project}/jobs?scope=success",
            max=MAX_SEARCHED_JOBS,
        ):
            if (
                jobinfo["name"] == job
                and jobinfo["pipeline"]["ref"] == self.__branch
                and any(
                    i["file_type"] == "archive"
                    for i in jobinfo.get("artifacts", [])
                )
            ):
                LOGGER.debug("Selected job with ID %d", jobinfo["id"])
                return jobinfo["id"]

        raise RuntimeError(
            f"No recent successful {job!r} job found on {self.__branch!r}"
        )

    def __rawget(self, url: str) -> requests.Response:
        """Make a GET request and return the raw Response object.

        Parameters
        ----------
        url
            The full URL to request, including the server and protocol.
        """
        LOGGER.debug("GET %s", url)
        return requests.get(
            url, headers={"PRIVATE-TOKEN": self.__token}, timeout=30
        )

    def __get(self, path: str) -> t.Any:
        """Make a GET request and return the decoded JSON response."""
        response = self.__rawget(f"{self.__path}/api/v4{path}")
        LOGGER.debug("Status: %d", response.status_code)
        response.raise_for_status()
        return response.json()

    def __iterget(self, path: str, *, max: int = 0) -> cabc.Iterator[t.Any]:
        """Iterate over a result set, using multiple GET requests if necessary.

        This method implements the keyset-based pagination method.

        Parameters
        ----------
        path
            The base URL for the first request.
        max
            Maximum number of entries to yield. If 0, yield everything.
        """
        sep = ("?", "&")["?" in path]
        next_url = (
            f"{self.__path}/api/v4{path}{sep}pagination=keyset&per_page="
            + str(min(100, max or 100))
        )
        i = 0
        stop = max or math.inf

        while True:
            response = self.__rawget(next_url)
            response.raise_for_status()
            for i, object in enumerate(response.json(), start=i):
                yield object
                if i >= stop:
                    return

            match = RE_LINK_NEXT.fullmatch(response.headers.get("Link", ""))
            if not match:
                break
            next_url = match.group(1)

    def get_model_info(self) -> loader.ModelInfo:
        return loader.ModelInfo(branch=self.__branch, url=self.__path)

    def open(
        self,
        filename: str | pathlib.PurePosixPath,
        mode: t.Literal["r", "rb", "w", "wb"] = "rb",
    ) -> t.BinaryIO:
        path = str(helpers.normalize_pure_path(filename, base=self.subdir))

        if "w" in mode:
            raise TypeError("Cannot write to Gitlab artifacts")

        LOGGER.debug("Opening file %r for reading", path)
        response = self.__rawget(
            f"{self.__path}/api/v4/projects/{self.__project}"
            f"/jobs/{self.__job}/artifacts/{path}"
        )
        if response.status_code in (400, 404):
            raise FileNotFoundError(errno.ENOENT, filename)
        response.raise_for_status()
        return io.BytesIO(response.content)
