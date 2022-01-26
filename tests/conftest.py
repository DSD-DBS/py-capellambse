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
"""Global fixtures for pytest"""
import io
import sys

import pytest

import capellambse

from . import TEST_MODEL, TEST_ROOT


@pytest.fixture
def model(monkeypatch) -> capellambse.MelodyModel:
    """Return test model"""
    monkeypatch.setattr(sys, "stderr", io.StringIO)
    return capellambse.MelodyModel(TEST_ROOT / "5_0" / TEST_MODEL)


@pytest.fixture
def model_5_1(monkeypatch) -> capellambse.MelodyModel:
    """Return test model"""
    monkeypatch.setattr(sys, "stderr", io.StringIO)
    return capellambse.MelodyModel(TEST_ROOT / "5_1" / TEST_MODEL)


@pytest.fixture
def model_5_2(monkeypatch) -> capellambse.MelodyModel:
    """Return test model"""
    monkeypatch.setattr(sys, "stderr", io.StringIO)
    return capellambse.MelodyModel(TEST_ROOT / "5_2" / TEST_MODEL)
