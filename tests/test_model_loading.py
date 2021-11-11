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
import subprocess
from importlib import metadata

import pytest

import capellambse

from . import TEST_MODEL, TEST_ROOT


def has_git_lfs():
    proc = subprocess.run(
        ["git", "lfs"],
    )
    return proc.returncode == 0


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(str(TEST_ROOT / "5_0" / TEST_MODEL), id="From string"),
        pytest.param(TEST_ROOT / "5_0" / TEST_MODEL, id="From path"),
    ],
)
def test_model_loading_via_LocalFileHandler(path: str | pathlib.Path):
    capellambse.MelodyModel(path)


@pytest.mark.skipif(
    not has_git_lfs(),
    reason="This test requires git-lfs to be present on the system",
)
def test_model_loading_via_GitFileHandler():
    path = "git+" + pathlib.Path.cwd().as_uri()
    capellambse.MelodyModel(
        path, entrypoint="tests/data/melodymodel/5_0/MelodyModelTest.aird"
    )


def test_model_loading_from_badpath_raises_FileNotFoundError():
    badpath = TEST_ROOT / "TestFile.airdfragment"
    with pytest.raises(FileNotFoundError):
        capellambse.MelodyModel(badpath)


class FakeEntrypoint:
    @property
    def name(self):
        class AlwaysEqual:
            def __eq__(self, other):
                return True

        return AlwaysEqual()

    def load(self):
        def filehandler(url):
            assert url.startswith("testproto:")

        return filehandler

    @classmethod
    def patch(cls, monkeypatch):
        fake_entrypoints = {"capellambse.filehandler": (cls(),)}
        monkeypatch.setattr(metadata, "entry_points", lambda: fake_entrypoints)


def test_a_single_protocol_is_not_swallowed_by_get_filehandler(
    monkeypatch,
):
    FakeEntrypoint.patch(monkeypatch)

    capellambse.loader.filehandler.get_filehandler("testproto://url")


def test_a_wrapping_protocol_separated_by_plus_is_stripped(monkeypatch):
    FakeEntrypoint.patch(monkeypatch)

    capellambse.loader.filehandler.get_filehandler("removeme+testproto://url")
