# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import collections.abc as cabc
import errno
import io
import logging
import math
import os
import pathlib
import sys
import typing as t
import urllib.parse
import weakref

import diskcache
import requests
import requests.exceptions
import urllib3.exceptions

import capellambse
from capellambse import helpers

from . import abc

LOGGER = logging.getLogger(__name__)
MAX_SEARCHED_JOBS = (
    int(os.environ.get("CAPELLAMBSE_GLART_MAX_JOBS", "1000")) or sys.maxsize
)


class GitlabArtifactsFiles(abc.FileHandler):
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
        The URL to fetch artifacts from, in one of the following formats:

        -   The literal string ``glart:`` (or ``glart://``), which uses
            the URL from ``$CI_SERVER_FQDN`` or - if that is not set -
            the public Gitlab instance at ``https://gitlab.com``.
        -   The base URL of the Gitlab server, using ``glart:``,
            ``glart+http:`` or ``glart+https:`` as the protocol.
            ``glart:`` uses the protocol specified by
            ``$CI_SERVER_PROTOCOL``, or falls back to HTTPS.
        -   A URL that combines the above with some of the required
            parameters described below, using the format::

                glart://gitlab.mycompany.com/group/subgroup/project#branch=<branch>&job=<jobname>

            Note that this format does not support numeric IDs for the
            project and job, thus requiring to pass a branch name. Any
            of the parts of this combined URL may instead be passed
            explicitly via keyword arguments.

            Keyword arguments have precedence over the combined URL.
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
        The path (e.g. ``group/subgroup/project``) or numeric ID of the
        project to pull the artifacts from. Defaults to the
        ``$CI_PROJECT_ID`` environment variable, which Gitlab sets to
        the project currently executing a pipeline.
    branch
        The branch to pull artifacts from. Defaults to the value of the
        ``CI_DEFAULT_BRANCH`` environment variable, or ``main`` if that
        is unset. Ignored if a numeric ID is given for ``job``.
    job
        Name of the job to pull artifacts from. May also be a numeric
        job ID. Defaults to "update_capella_diagram_cache".

        If a job name was given, the Gitlab API is queried for the most
        recent successful job on the given ``branch`` that has attached
        artifacts. Note that jobs whose artifacts have been deleted (for
        example, because their retention period expired) are ignored.

        By default, at most 1000 jobs will be checked. This includes all
        successful jobs in the repo, regardless of their name or the
        branch they ran on. This number can be changed using the
        ``CAPELLAMBSE_GLART_MAX_JOBS`` environment variable.
    subdir
        An optional path prefix inside the artifacts archive to prepend
        to all file names.
    disable_cache
        Clear the local cache and discard any previously cached data.

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
        job: str | int | None = None,
        disable_cache: bool = False,
    ) -> None:
        path = str(path)
        super().__init__(path, subdir=subdir)

        self.__session = requests.Session()

        self.__path, urlparts = self.__resolve_path(path)
        if not project:
            project = urlparts["project"]
        if not branch:
            branch = urlparts["branch"]
        if not job:
            job = urlparts["job"]
        if str(self.subdir) in ("", ".", "/"):
            self.subdir = helpers.normalize_pure_path(urlparts["subdir"])

        self.__token = self.__resolve_token(token)
        self.__project = self.__resolve_project(project)
        self.__branch = branch or os.getenv("CI_DEFAULT_BRANCH") or "main"
        self.__job, job = self.__resolve_job(job)

        self.path = (
            f"glart+{self.__path}/{project}/-/{self.subdir}"
            f"#branch={branch}&job={job}"
        )
        self.__cache = diskcache.Cache(
            capellambse.dirs.user_cache_path / "gitlab-artifacts"
        )
        self.__fnz = weakref.finalize(self, self.__cache.close)

        if disable_cache:
            self.__cache.clear()

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(path={self.__path!r}, token=<HIDDEN>,"
            f" project={self.__project!r}, branch={self.__branch!r},"
            f" job={self.__job!r}, subdir={self.subdir!r})"
        )

    @staticmethod
    def __resolve_path(path: str) -> tuple[str, _URLParts]:
        scheme, netloc, project, _, _, fragment = urllib.parse.urlparse(path)
        scheme = scheme.removeprefix("glart+")

        if netloc:
            if scheme == "glart":
                scheme = os.getenv("CI_SERVER_PROTOCOL", "https")
            path = urllib.parse.urlunparse((scheme, netloc, "", "", "", ""))
        elif path := os.getenv("CI_SERVER_URL", ""):
            LOGGER.debug("Using current Gitlab instance: %s", path)
        else:
            path = "https://gitlab.com"
            LOGGER.debug("Using public Gitlab instance at: %s", path)

        if "/-/" in project:
            project, subdir = project.split("/-/", 1)
        else:
            subdir = ""
        args = dict(i.split("=", 1) for i in fragment.split("&") if "=" in i)
        urlparts = _URLParts(
            project=project.strip("/").removesuffix(".git"),
            branch=args.get("branch", ""),
            job=args.get("job", ""),
            subdir=subdir.strip("/"),
        )
        return path, urlparts

    @classmethod
    def __resolve_token(cls, token: str | None) -> str:
        if token:
            return cls.__load_token_from_arg(token)

        if cred_dir := os.getenv("CREDENTIALS_DIRECTORY"):
            token = cls.__load_token_from_credentials(cred_dir)
            if token:
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
            raise ValueError(
                f"Token file from {token} not found"
                " - did you set the variable type to FILE?"
            ) from None
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
            LOGGER.debug("Token file is empty: %s", cred_file)
        return None

    def __resolve_project(self, project: str | int | None) -> int:
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

    def __resolve_job(self, job: str | int) -> tuple[int, str]:
        try:
            job = int(job)
            return job, str(job)
        except ValueError:
            pass
        assert isinstance(job, str)

        if not job:
            job = "update_capella_diagram_cache"

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
                return (jobinfo["id"], job)

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
        return self.__session.get(
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
        stop = max or math.inf

        while next_url:
            response = self.__rawget(next_url)
            response.raise_for_status()
            for i, object in enumerate(response.json()):
                yield object
                if i >= stop:
                    return

            next_url = response.links.get("next", {}).get("url")

    def open(
        self,
        filename: str | pathlib.PurePosixPath,
        mode: t.Literal["r", "rb", "w", "wb"] = "rb",
    ) -> t.BinaryIO:
        path = str(helpers.normalize_pure_path(filename, base=self.subdir))

        if "w" in mode:
            raise TypeError("Cannot write to Gitlab artifacts")

        cachekey = f"{self.__path}|{self.__project}|{self.__job}|{path}"
        try:
            content = self.__cache[cachekey]
        except KeyError:
            pass
        else:
            if content is None:
                LOGGER.debug("Negative cache hit for %r", path)
                raise FileNotFoundError(errno.ENOENT, filename)
            LOGGER.debug("Opening cached file %r for reading", path)
            return io.BytesIO(content)

        try:
            response = self.__rawget(
                f"{self.__path}/api/v4/projects/{self.__project}"
                f"/jobs/{self.__job}/artifacts/{path}"
            )
        # <https://gitlab.com/gitlab-org/gitlab/-/issues/414807>
        except requests.exceptions.ChunkedEncodingError as err:
            if len(err.args) != 1:
                raise
            (err1,) = err.args
            if not isinstance(err1, urllib3.exceptions.ProtocolError):
                raise
            if len(err1.args) != 2:
                raise
            (_, err2) = err1.args
            if not isinstance(err2, urllib3.exceptions.IncompleteRead):
                raise
            if err2.args != (0, 2):
                raise

            LOGGER.debug("File not found in artifacts archive: %r", path)
            self.__cache[cachekey] = None
            raise FileNotFoundError(errno.ENOENT, filename) from None
        if response.status_code in (400, 404):
            LOGGER.debug("File not found in artifacts archive: %r", path)
            self.__cache[cachekey] = None
            raise FileNotFoundError(errno.ENOENT, filename)
        response.raise_for_status()
        LOGGER.debug("Opening file %r for reading", path)
        self.__cache[cachekey] = response.content
        return io.BytesIO(response.content)


class _URLParts(t.TypedDict):
    project: str
    branch: str
    job: str
    subdir: str
