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

import os
import pathlib
import sys

import pytest

import capellambse

from . import TEST_MODEL, TEST_ROOT


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(str(TEST_ROOT / "5_0" / TEST_MODEL), id="From string"),
        pytest.param(
            str(TEST_ROOT / "5_0" / TEST_MODEL).encode(
                sys.getfilesystemencoding()
            ),
            id="From filesystemencoded string",
        ),
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
