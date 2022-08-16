# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

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
