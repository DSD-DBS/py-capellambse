# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=redefined-outer-name
from __future__ import annotations

import base64
import contextlib
import errno
import logging
import pathlib
import re
import shutil
import subprocess
import sys
from importlib import metadata
from unittest import mock

import pytest
import requests_mock

import capellambse
from capellambse.filehandler import gitlab_artifacts

# pylint: disable-next=relative-beyond-top-level, useless-suppression
from .conftest import TEST_MODEL, TEST_ROOT  # type: ignore[import]

TEST_MODEL_5_0 = TEST_ROOT / "5_0" / TEST_MODEL


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(str(TEST_MODEL_5_0), id="From string"),
        pytest.param(TEST_MODEL_5_0, id="From path"),
    ],
)
def test_model_loading_via_LocalFileHandler(path: str | pathlib.Path):
    capellambse.MelodyModel(path)


@pytest.mark.parametrize("suffix", [".capella", ".melodymodel"])
def test_model_loading_with_invalid_entrypoint_fails(suffix: str):
    with pytest.raises(ValueError, match="(?i)invalid entrypoint"):
        capellambse.MelodyModel(TEST_MODEL_5_0.with_suffix(suffix))


def test_model_loading_via_GitFileHandler():
    path = "git+" + pathlib.Path.cwd().as_uri()
    capellambse.MelodyModel(
        path, entrypoint="tests/data/melodymodel/5_0/Melody Model Test.aird"
    )


def test_GitFileHandler_locks_repo_during_tasks(monkeypatch, caplog):
    did_ls_files = False

    def mock_run(cmd, *args, encoding="", **kw):
        del args, kw
        nonlocal did_ls_files
        if len(cmd) >= 2 and cmd[1] == "ls-remote":
            assert not did_ls_files
            did_ls_files = True
            data = "0123456789abcdef0123456789abcdef01234567\tHEAD"
            mock_return = mock.Mock()
            mock_return.stdout = data if encoding else data.encode("ascii")
            mock_return.stderr = "" if encoding else b""
            mock_return.returncode = 0
            return mock_return

        assert did_ls_files
        raise FileNotFoundError(errno.ENOENT, "--mocked end of test--")

    did_flock = False

    @contextlib.contextmanager
    def mock_flock(file):
        del file
        nonlocal did_flock
        assert not did_flock
        did_flock = True
        yield

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(capellambse.helpers, "flock", mock_flock)
    caplog.set_level(logging.DEBUG)
    caplog.clear()

    with pytest.raises(FileNotFoundError, match="--mocked end of test--$"):
        capellambse.get_filehandler("git+https://domain.invalid/demo.git")

    assert did_ls_files
    assert did_flock


def test_model_loading_from_badpath_raises_FileNotFoundError():
    badpath = TEST_ROOT / "Missing.aird"
    with pytest.raises(FileNotFoundError):
        capellambse.MelodyModel(badpath)


class FakeEntrypoint:
    def __init__(self, expected_name, expected_url):
        self._expected_name = expected_name
        self._expected_url = expected_url

    @property
    def name(self):
        class AlwaysEqual:
            def __eq__(_, name):  # pylint: disable=E,I
                nonlocal self
                assert name == self._expected_name
                return True

        return AlwaysEqual()

    def load(self):
        def filehandler(url):
            assert url == self._expected_url

        return filehandler

    if sys.version_info < (3, 10):

        @classmethod
        def patch(cls, monkeypatch, expected_name, expected_url):
            eps = {
                "capellambse.filehandler": (cls(expected_name, expected_url),)
            }
            monkeypatch.setattr(metadata, "entry_points", lambda: eps)

    else:

        @classmethod
        def patch(cls, monkeypatch, expected_name, expected_url):
            def entry_points(group, name):
                assert group == "capellambse.filehandler"
                assert name == expected_name
                return (cls(expected_name, expected_url),)

            monkeypatch.setattr(metadata, "entry_points", entry_points)


def test_a_single_protocol_is_not_swallowed_by_get_filehandler(
    monkeypatch,
):
    FakeEntrypoint.patch(monkeypatch, "testproto", "testproto://url")

    capellambse.get_filehandler("testproto://url")


def test_a_wrapping_protocol_separated_by_plus_is_stripped(monkeypatch):
    FakeEntrypoint.patch(monkeypatch, "realproto", "wrappedproto://url")

    capellambse.get_filehandler("realproto+wrappedproto://url")


@pytest.mark.parametrize(
    "path",
    [
        "/data/model/model.aird",
        r"S:\model\model.aird",
        r"S:/model/model.aird",
        r"\\?\S:\model\model.aird",
        r"\\modelserver\model\model.aird",
    ],
)
def test_plain_file_paths_are_recognized_as_file_protocol(monkeypatch, path):
    FakeEntrypoint.patch(monkeypatch, "file", path)

    capellambse.get_filehandler(path)


@pytest.mark.parametrize(
    "url",
    [
        "myhost:myrepo.git",
        "git@host:",
        "git@host:repo.git",
        "git@host:path/to/repo",
        "git@host:/path/to/repo",
    ],
)
def test_the_scp_short_form_is_recognized_as_git_protocol(monkeypatch, url):
    FakeEntrypoint.patch(monkeypatch, "git", url)

    capellambse.get_filehandler(url)


@pytest.mark.parametrize(
    "link",
    [
        "xtype MelodyModelTest.aird#078b2c69-4352-4cf9-9ea5-6573b75e5eec",
        "MelodyModelTest.aird#071b2c69-4352-4cf9-9ea5-6573b75e5eec",
        "#071b2c69-4352-4cf9-9ea5-6573b75e5eec",
        "xtype MelodyModel%20Test.aird#078b2c69-4352-4cf9-9ea5-6573b75e5eec",
        "MelodyModel%20Test.aird#071b2c69-4352-4cf9-9ea5-6573b75e5eec",
    ],
)
def test_MelodyLoader_follow_link_finds_target(link: str):
    loader = capellambse.loader.MelodyLoader(TEST_MODEL_5_0)

    with pytest.raises(KeyError):
        assert loader.follow_link(None, link) is not None


@pytest.mark.parametrize(
    ["path", "subdir", "req_url"],
    [
        (
            "https://example.com/~user",
            "/",
            "https://example.com/~user/demo/my%20model.aird",
        ),
        (
            "https://example.com/~user/%s",
            "/",
            "https://example.com/~user/demo/my%20model.aird",
        ),
        (
            "https://example.com/?file=%q",
            "/",
            "https://example.com/?file=demo%2Fmy%20model.aird",
        ),
        (
            "https://example.com/",
            "~user",
            "https://example.com/~user/demo/my%20model.aird",
        ),
        (
            "https://example.com/%s",
            "~user",
            "https://example.com/~user/demo/my%20model.aird",
        ),
        (
            "https://example.com/?file=%q",
            "~user",
            "https://example.com/?file=~user%2Fdemo%2Fmy%20model.aird",
        ),
    ],
)
def test_http_file_handler_replaces_percent_s_percent_q(
    requests_mock: requests_mock.Mocker, path: str, subdir: str, req_url: str
) -> None:
    endpoint = requests_mock.get(req_url)

    file_handler = capellambse.get_filehandler(path, subdir=subdir)
    file_handler.open("demo/my model.aird", "rb").close()

    assert endpoint.called_once


def test_http_file_handler_hands_auth_to_server(
    requests_mock: requests_mock.Mocker,
) -> None:
    username = "testuser"
    password = "testpassword"
    auth_header = base64.standard_b64encode(
        f"{username}:{password}".encode("utf-8")
    ).decode("ascii")
    expected_headers = {"Authorization": f"Basic {auth_header}"}
    endpoint = requests_mock.get(
        "https://example.com/test.svg",
        request_headers=expected_headers,
    )

    file_handler = capellambse.get_filehandler(
        "https://example.com", username=username, password=password
    )
    file_handler.open("test.svg", "rb").close()

    assert endpoint.called_once


def test_http_file_handlers_passed_through_custom_headers(
    requests_mock: requests_mock.Mocker,
) -> None:
    expected_headers = {"X-Test-Header": "PASSED"}
    endpoint = requests_mock.get(
        "https://example.com/test.svg",
        request_headers=expected_headers,
    )

    file_handler = capellambse.get_filehandler(
        "https://example.com", headers=expected_headers
    )
    file_handler.open("test.svg", "rb").close()

    assert endpoint.called_once


def test_gitlab_artifacts_handler_uses_public_gitlab_when_no_hostname_given(
    requests_mock: requests_mock.Mocker,  # pylint: disable=unused-argument
) -> None:
    # pylint: disable=line-too-long

    hdl = capellambse.get_filehandler(
        "glart://",
        project=1,
        branch="some-branch",
        token="my-access-token",
        job=3,
    )

    assert isinstance(hdl, gitlab_artifacts.GitlabArtifactsFiles)
    assert hdl._GitlabArtifactsFiles__path == "https://gitlab.com"  # type: ignore[attr-defined]
    assert hdl._GitlabArtifactsFiles__project == 1  # type: ignore[attr-defined]
    assert hdl._GitlabArtifactsFiles__job == 3  # type: ignore[attr-defined]


def test_gitlab_artifacts_handler_resolves_project_to_numeric_id(
    requests_mock: requests_mock.Mocker,
) -> None:
    requests_mock.get(
        "https://gitlab.com/api/v4/projects/homegroup%2fdemo-project",
        json={"id": 1},
    )

    hdl = capellambse.get_filehandler(
        "glart://",
        project="homegroup/demo-project",
        branch="some-branch",
        token="my-access-token",
        job=3,
    )

    assert isinstance(hdl, gitlab_artifacts.GitlabArtifactsFiles)
    # pylint: disable=line-too-long
    assert hdl._GitlabArtifactsFiles__path == "https://gitlab.com"  # type: ignore[attr-defined]
    assert hdl._GitlabArtifactsFiles__project == 1  # type: ignore[attr-defined]
    assert hdl._GitlabArtifactsFiles__job == 3  # type: ignore[attr-defined]


def test_gitlab_artifacts_handler_looks_up_job_id_given_a_job_name(
    requests_mock: requests_mock.Mocker,
) -> None:
    requests_mock.get(
        "https://gitlab.com/api/v4/projects/1/jobs",
        json=[
            {
                "id": 3,
                "name": "make-stuff",
                "pipeline": {"ref": "somebranch"},
                "artifacts": [{"file_type": "archive"}],
            },
        ],
    )

    hdl = capellambse.get_filehandler(
        "glart://",
        project=1,
        branch="somebranch",
        token="my-access-token",
        job="make-stuff",
    )

    assert isinstance(hdl, gitlab_artifacts.GitlabArtifactsFiles)
    # pylint: disable=line-too-long
    assert hdl._GitlabArtifactsFiles__path == "https://gitlab.com"  # type: ignore[attr-defined]
    assert hdl._GitlabArtifactsFiles__project == 1  # type: ignore[attr-defined]
    assert hdl._GitlabArtifactsFiles__job == 3  # type: ignore[attr-defined]


def test_gitlab_artifacts_handler_errors_if_no_job_with_artifacts_was_found(
    requests_mock: requests_mock.Mocker,
) -> None:
    requests_mock.get(
        "https://gitlab.com/api/v4/projects/1/jobs",
        json=[],
    )

    with pytest.raises(RuntimeError, match="recent successful"):
        capellambse.get_filehandler(
            "glart://",
            project=1,
            branch="somebranch",
            token="my-access-token",
            job="make-stuff",
        )


def test_gitlab_artifacts_handler_handles_pagination_when_searching_for_jobs(
    requests_mock: requests_mock.Mocker,
) -> None:
    requests_mock.get(
        "https://gitlab.com/api/v4/projects/1/jobs",
        headers={
            "Link": (
                "<https://gitlab.com/api/v4/projects/1/jobs/page/2>;"
                ' rel="next"'
            )
        },
        json=[
            {
                "id": 2,
                "name": "make-stuff",
                "pipeline": {"ref": "otherbranch"},
                "artifacts": [],
            },
        ],
    )
    requests_mock.get(
        "https://gitlab.com/api/v4/projects/1/jobs/page/2",
        json=[
            {
                "id": 3,
                "name": "make-stuff",
                "pipeline": {"ref": "somebranch"},
                "artifacts": [{"file_type": "archive"}],
            },
        ],
    )

    hdl = capellambse.get_filehandler(
        "glart://",
        project=1,
        branch="somebranch",
        token="my-access-token",
        job="make-stuff",
    )

    assert isinstance(hdl, gitlab_artifacts.GitlabArtifactsFiles)
    # pylint: disable=line-too-long
    assert hdl._GitlabArtifactsFiles__path == "https://gitlab.com"  # type: ignore[attr-defined]
    assert hdl._GitlabArtifactsFiles__project == 1  # type: ignore[attr-defined]
    assert hdl._GitlabArtifactsFiles__job == 3  # type: ignore[attr-defined]


@pytest.fixture
def model_path_with_patched_version(
    request: pytest.FixtureRequest, tmp_path: pathlib.Path
) -> pathlib.Path:
    """Indirect parametrized fixture for version patched model.

    Parameters
    ----------
    request
        Special pytest fixture for access to test context, exposing the
        ``param`` attribute on indirect parametrization.
    tmp_path
        Pytest fixture giving a temporary path.

    Returns
    -------
    aird_path
        Path to Capella ``.aird`` file.
    """
    tmp_dest = tmp_path / "model"
    ignored = shutil.ignore_patterns("*.license")
    shutil.copytree(TEST_MODEL_5_0.parent, tmp_dest, ignore=ignored)
    request_param: str | tuple[str, str] = request.param
    for suffix in (".aird", ".capella"):
        model_file = (tmp_dest / TEST_MODEL).with_suffix(suffix)
        if isinstance(request_param, tuple):
            re_params = request_param
        else:
            re_params = (r"5\.0\.0", request_param)

        patched = re.sub(*re_params, model_file.read_text(encoding="utf-8"))
        model_file.write_text(patched, encoding="utf-8")
    return model_file.with_suffix(".aird")


@pytest.mark.parametrize(
    "model_path_with_patched_version",
    ["1.3.0", "1.4.2", "6.1.0"],
    indirect=True,
)
def test_loading_model_with_unsupported_version_fails(
    model_path_with_patched_version: pathlib.Path,
) -> None:
    with pytest.raises(capellambse.UnsupportedPluginVersionError):
        capellambse.MelodyModel(model_path_with_patched_version)


@pytest.mark.parametrize(
    "model_path_with_patched_version",
    [("http://www.eclipse.org/sirius/1.1.0", "Unknown")],
    indirect=True,
)
def test_loading_model_with_unsupported_plugin_fails(
    model_path_with_patched_version: pathlib.Path,
) -> None:
    with pytest.raises(capellambse.UnsupportedPluginError):
        capellambse.MelodyModel(model_path_with_patched_version)


def test_model_info_contains_viewpoints_and_capella_version() -> None:
    loader = capellambse.loader.MelodyLoader(TEST_MODEL_5_0)

    info = loader.get_model_info()

    assert hasattr(info, "viewpoints")
    assert info.viewpoints["org.polarsys.capella.core.viewpoint"] == "5.0.0"
    assert info.capella_version == "5.0.0"
