# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Global fixtures for pytest."""
import collections.abc as cabc
import io
import pathlib
import sys

import pytest

import capellambse

INSTALLED_PACKAGE = pathlib.Path(capellambse.__file__).parent

TEST_ROOT = pathlib.Path(__file__).parent / "data" / "melodymodel"
TEST_MODEL = "Melody Model Test.aird"

capellambse.load_model_extensions()


@pytest.fixture(scope="session")
def session_shared_model() -> cabc.Iterator[capellambse.MelodyModel]:
    """Load the standard test model.

    Unlike the ``model`` fixture, this fixture is shared across the
    entire test session. As such, the test functions using this fixture
    are expected to not modify it.

    This fixture exists as a speed optimization for tests that only read
    from the model.
    """
    loaded = capellambse.MelodyModel(TEST_ROOT / "5_0" / TEST_MODEL)
    with capellambse.WriteProtector(loaded):
        yield loaded


@pytest.fixture
def model(monkeypatch) -> capellambse.MelodyModel:
    """Return the Capella 5.0 test model."""
    monkeypatch.setattr(sys, "stderr", io.StringIO)
    return capellambse.MelodyModel(TEST_ROOT / "5_0" / TEST_MODEL)


@pytest.fixture
def model_5_2(monkeypatch) -> capellambse.MelodyModel:
    """Return the Capella 5.2 test model."""
    monkeypatch.setattr(sys, "stderr", io.StringIO)
    return capellambse.MelodyModel(TEST_ROOT / "5_2" / TEST_MODEL)
