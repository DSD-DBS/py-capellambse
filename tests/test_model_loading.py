# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pathlib
from importlib import metadata

import pytest

import capellambse

from . import TEST_MODEL, TEST_ROOT

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


def test_model_loading_via_GitFileHandler():
    path = "git+" + pathlib.Path.cwd().as_uri()
    capellambse.MelodyModel(
        path, entrypoint="tests/data/melodymodel/5_0/Melody Model Test.aird"
    )


def test_model_loading_from_badpath_raises_FileNotFoundError():
    badpath = TEST_ROOT / "TestFile.airdfragment"
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

    @classmethod
    def patch(cls, monkeypatch, expected_name, expected_url):
        fake_entrypoints = {
            "capellambse.filehandler": (cls(expected_name, expected_url),)
        }
        monkeypatch.setattr(metadata, "entry_points", lambda: fake_entrypoints)


def test_a_single_protocol_is_not_swallowed_by_get_filehandler(
    monkeypatch,
):
    FakeEntrypoint.patch(monkeypatch, "testproto", "testproto://url")

    capellambse.loader.filehandler.get_filehandler("testproto://url")


def test_a_wrapping_protocol_separated_by_plus_is_stripped(monkeypatch):
    FakeEntrypoint.patch(monkeypatch, "realproto", "wrappedproto://url")

    capellambse.loader.filehandler.get_filehandler(
        "realproto+wrappedproto://url"
    )


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

    capellambse.loader.filehandler.get_filehandler(path)


@pytest.mark.parametrize(
    "url", ["myhost:myrepo.git", "git@host:repo.git", "git@host:path/to/repo"]
)
def test_the_scp_short_form_is_recognized_as_git_protocol(monkeypatch, url):
    FakeEntrypoint.patch(monkeypatch, "git", url)

    capellambse.loader.filehandler.get_filehandler(url)


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
