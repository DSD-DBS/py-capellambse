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

import pathlib
from importlib import metadata

import pytest

import capellambse

from . import TEST_MODEL, TEST_ROOT


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(str(TEST_ROOT / "5_0" / TEST_MODEL), id="From string"),
        pytest.param(TEST_ROOT / "5_0" / TEST_MODEL, id="From path"),
    ],
)
def test_model_loading_via_LocalFileHandler(path: str | pathlib.Path):
    capellambse.MelodyModel(path)


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(
            "git+" + pathlib.Path.cwd().as_uri(), id="From local repo"
        ),
    ],
)
def test_model_loading_via_GitFileHandler(path: str):
    capellambse.MelodyModel(
        path, entrypoint="tests/data/melodymodel/5_0/MelodyModelTest.aird"
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
