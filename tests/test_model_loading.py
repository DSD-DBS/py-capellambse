# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import base64
import os
import pathlib
import re
import shutil
import subprocess
import sys
from importlib import metadata

import pytest
import requests_mock

import capellambse
from capellambse.filehandler import gitlab_artifacts

from .conftest import TEST_MODEL, TEST_ROOT  # type: ignore[import-untyped]

TEST_MODEL_5_0 = TEST_ROOT / "5_0" / TEST_MODEL

DUMMY_SVG = b'<svg xmlns="http://www.w3.org/2000/svg"/>'
DUMMY_PNG = base64.standard_b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGMAAQAABQABDQott"
    "AAAAABJRU5ErkJggg=="
)


@pytest.fixture(autouse=True)
def _glart_clear_env(monkeypatch):
    for i in list(os.environ):
        if i.startswith("CI_"):
            monkeypatch.delenv(i)


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(str(TEST_MODEL_5_0), id="From string"),
        pytest.param(TEST_MODEL_5_0, id="From path"),
    ],
)
def test_model_loading_via_LocalFileHandler(path: str | pathlib.Path):
    capellambse.MelodyModel(path)


@pytest.mark.parametrize("suffix", [".afm", ".capella"])
def test_model_loading_with_invalid_entrypoint_fails(suffix: str):
    with pytest.raises(ValueError, match="(?i)invalid entrypoint"):
        capellambse.MelodyModel(TEST_MODEL_5_0.with_suffix(suffix))


def test_model_loading_via_GitFileHandler():
    path = "git+" + pathlib.Path.cwd().as_uri()

    capellambse.MelodyModel(
        path, entrypoint="tests/data/melodymodel/5_0/Melody Model Test.aird"
    )

    lockfile = pathlib.Path.cwd().joinpath("capellambse.lock")
    assert not lockfile.exists()


def test_model_loading_via_GitFileHandler_invalid_uri():
    path = "git+not-a-valid-uri"
    with pytest.raises(subprocess.CalledProcessError):
        capellambse.MelodyModel(
            path,
            entrypoint="tests/data/melodymodel/5_0/Melody Model Test.aird",
        )
    assert path


def test_model_loading_from_badpath_raises_FileNotFoundError():
    badpath = TEST_ROOT / "Missing.aird"
    with pytest.raises(FileNotFoundError):
        capellambse.MelodyModel(badpath)


def test_split_protocol_returns_path_objects_unchanged():
    expected = pathlib.Path.cwd()

    handler, actual = capellambse.filehandler.split_protocol(expected)

    assert handler == "file"
    assert actual == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    (
        [
            ("/path/to/file", pathlib.Path("/path/to/file")),
            ("file:///path/to/file", pathlib.Path("/path/to/file")),
            ("file://localhost/path/to/file", pathlib.Path("/path/to/file")),
        ]
        if not sys.platform.startswith("win")
        else [
            ("C:/path/to/file", pathlib.Path("C:/path/to/file")),
            (r"C:\path\to\file", pathlib.Path(r"C:\path\to\file")),
            ("file:///C:/path/to/file", pathlib.Path("C:/path/to/file")),
            (
                "file://localhost/C:/path/to/file",
                pathlib.Path("C:/path/to/file"),
            ),
        ]
    ),
)
def test_split_protocol_converts_file_urls_to_paths(url, expected):
    handler, actual = capellambse.filehandler.split_protocol(url)

    assert handler == "file"
    assert actual == expected


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
def test_split_protocol_recognizes_scp_style_uris_as_git(url: str):
    handler, actual = capellambse.filehandler.split_protocol(url)

    assert handler == "git"
    assert actual == url


@pytest.mark.parametrize(
    "url",
    [
        pytest.param("http://domain.invalid/path", id="http"),
        pytest.param("https://domain.invalid/path", id="https"),
        pytest.param("ftp://domain.invalid/path", id="ftp"),
        pytest.param("ftps://domain.invalid/path", id="ftps"),
        pytest.param("sftp://domain.invalid/path", id="sftp"),
        pytest.param("ssh://domain.invalid/path", id="ssh"),
    ],
)
def test_split_protocol_does_not_change_simple_urls(url: str):
    handler, actual = capellambse.filehandler.split_protocol(url)

    assert handler == url.split(":", 1)[0]
    assert actual == url


class FakeEntrypoint:
    def __init__(self, expected_name: str, expected_url: str):
        self._expected_name = expected_name
        self._expected_url = expected_url

    @property
    def name(self):
        class AlwaysEqual:
            def __eq__(_, name):
                nonlocal self
                assert name == self._expected_name
                return True

        return AlwaysEqual()

    def load(self):
        def filehandler(url: str | pathlib.Path):
            if isinstance(url, pathlib.Path):
                assert url == pathlib.Path(self._expected_url)
            else:
                assert str(url) == self._expected_url

        return filehandler

    @classmethod
    def patch(cls, monkeypatch, expected_name, expected_url) -> None:
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
    (
        [
            "/data/model/model.aird",
        ]
        if not sys.platform.startswith("win")
        else [
            r"S:\model\model.aird",
            r"S:/model/model.aird",
            r"\\?\S:\model\model.aird",
            r"\\modelserver\model\model.aird",
        ]
    ),
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
        "xtype MelodyModelTest.aird#00000000-0000-4000-0000-000000000000",
        "MelodyModelTest.aird#00000000-0000-4000-0000-000000000000",
        "#00000000-0000-4000-0000-000000000000",
        "xtype MelodyModel%20Test.aird#00000000-0000-4000-0000-000000000000",
        "MelodyModel%20Test.aird#00000000-0000-4000-0000-000000000000",
    ],
)
def test_MelodyLoader_follow_link_finds_target(link: str):
    loader = capellambse.loader.MelodyLoader(TEST_MODEL_5_0)

    with pytest.raises(KeyError):
        loader.follow_link(None, link)


@pytest.mark.parametrize(
    ("path", "subdir", "req_url"),
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
        (
            "https://example.com/?dir=%d&file=%n&type=%e",
            "/",
            "https://example.com/?dir=demo&file=my%20model&type=aird",
        ),
    ],
)
def test_http_file_handler_replaces_percent_escapes(
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
        f"{username}:{password}".encode()
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
    requests_mock: requests_mock.Mocker,
) -> None:
    del requests_mock

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
    assert hdl._GitlabArtifactsFiles__path == "https://gitlab.com"  # type: ignore[attr-defined]
    assert hdl._GitlabArtifactsFiles__project == 1  # type: ignore[attr-defined]
    assert hdl._GitlabArtifactsFiles__job == 3  # type: ignore[attr-defined]


def test_gitlab_artifacts_handler_parses_info_from_url(
    requests_mock: requests_mock.Mocker,
) -> None:
    requests_mock.get(
        "https://gitlab.com/api/v4/projects/group%2fsubgroup%2fproject",
        json={"id": 1},
    )
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

    path = (
        "glart://gitlab.com/group/subgroup/project/-/subdir/subdir2"
        "#branch=somebranch&job=make-stuff"
    )
    hdl = capellambse.get_filehandler(path, token="my-access-token")

    assert hdl._GitlabArtifactsFiles__path == "https://gitlab.com"  # type: ignore[attr-defined]
    assert hdl._GitlabArtifactsFiles__project == 1  # type: ignore[attr-defined]
    assert hdl._GitlabArtifactsFiles__job == 3  # type: ignore[attr-defined]


def test_gitlab_artifacts_handler_assembles_url_for_display(
    requests_mock: requests_mock.Mocker,
) -> None:
    requests_mock.get(
        "https://gitlab.com/api/v4/projects/group%2fsubgroup%2fproject",
        json={"id": 1},
    )
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
    expected = (
        "glart+https://gitlab.com/group/subgroup/project/-/subdir/subdir2"
        "#branch=somebranch&job=make-stuff"
    )

    hdl = capellambse.get_filehandler(
        "glart://",
        project="group/subgroup/project",
        branch="somebranch",
        job="make-stuff",
        subdir="subdir/subdir2",
        token="my-access-token",
    )

    assert hdl.path == expected


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


@pytest.mark.parametrize(
    ("format", "content"),
    [
        pytest.param("svg", DUMMY_SVG, id="svg"),
        pytest.param("png", DUMMY_PNG, id="png"),
    ],
)
def test_model_loads_diagrams_from_cache_by_uuid(
    tmp_path: pathlib.Path, format: str, content: bytes
):
    model = capellambse.MelodyModel(TEST_MODEL_5_0, diagram_cache=tmp_path)
    dg = model.diagrams[0]
    tmp_path.joinpath(f"{dg.uuid}.{format}").write_bytes(content)

    rendered = dg.render(format)
    if isinstance(rendered, str):
        rendered = rendered.encode("utf-8")

    assert rendered == content


def test_model_will_refuse_to_render_diagrams_if_diagram_cache_was_given(
    tmp_path: pathlib.Path,
):
    model = capellambse.MelodyModel(TEST_MODEL_5_0, diagram_cache=tmp_path)

    with pytest.raises(RuntimeError, match="not in cache"):
        model.diagrams[0].render("svg")


def test_model_will_fall_back_to_rendering_internally_despite_the_cache_if_told_to(
    tmp_path: pathlib.Path,
):
    model = capellambse.MelodyModel(
        TEST_MODEL_5_0,
        diagram_cache=tmp_path,
        fallback_render_aird=True,
    )

    assert model.diagrams[0].render("svg")


def test_model_diagram_visible_nodes_can_be_accessed_when_a_cache_was_specified(
    tmp_path: pathlib.Path,
):
    model = capellambse.MelodyModel(TEST_MODEL_5_0, diagram_cache=tmp_path)

    assert model.diagrams[0].nodes


def test_updated_namespaces_use_rounded_versions(
    model_5_2: capellambse.MelodyModel,
):
    model_5_2._loader.update_namespaces()

    assert model_5_2.info.capella_version == "5.2.0"
    ns = "org.polarsys.capella.core.data.capellacommon"
    nsver = model_5_2.project._element.nsmap[ns].rsplit("/", 1)[-1]
    assert nsver == "5.0.0"
