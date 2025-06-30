# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Global fixtures for pytest."""

import importlib.metadata as imm
import io
import pathlib
import sys

import pytest

import capellambse

INSTALLED_PACKAGE = pathlib.Path(capellambse.__file__).parent

TEST_ROOT = pathlib.Path(__file__).parent / "data" / "melodymodel"
TEST_MODEL = "Melody Model Test.aird"

capellambse.load_model_extensions()

if not any(
    i.module.startswith("capellambse.extensions.")
    for i in imm.entry_points(group="capellambse.model_extensions")
):
    raise RuntimeError(
        "Built-in model extensions are not loaded,"
        " is capellambse installed properly?"
    )


MODEL_PARAMS = ({"loader_backend": "lxml"},)


@pytest.fixture(scope="session", params=MODEL_PARAMS)
def session_shared_model(
    request: pytest.FixtureRequest,
) -> capellambse.MelodyModel:
    """Load the standard test model.

    Unlike the ``model`` fixture, this fixture is shared across the
    entire test session. As such, the test functions using this fixture
    are expected to not modify it.

    This fixture exists as a speed optimization for tests that only read
    from the model.
    """
    return capellambse.MelodyModel(
        TEST_ROOT / "5_0" / TEST_MODEL,
        **request.param,
    )


@pytest.fixture(params=MODEL_PARAMS)
def model(
    monkeypatch,
    request: pytest.FixtureRequest,
) -> capellambse.MelodyModel:
    """Return the Capella 5.0 test model."""
    monkeypatch.setattr(sys, "stderr", io.StringIO)
    return capellambse.MelodyModel(
        TEST_ROOT / "5_0" / TEST_MODEL,
        **request.param,
    )


@pytest.fixture(params=MODEL_PARAMS)
def model_5_2(
    monkeypatch,
    request: pytest.FixtureRequest,
) -> capellambse.MelodyModel:
    """Return the Capella 5.2 test model."""
    monkeypatch.setattr(sys, "stderr", io.StringIO)
    return capellambse.MelodyModel(
        TEST_ROOT / "5_2" / TEST_MODEL,
        **request.param,
    )


@pytest.fixture(params=MODEL_PARAMS)
def model_6_0(
    monkeypatch,
    request: pytest.FixtureRequest,
) -> capellambse.MelodyModel:
    """Return the Capella 6.0 test model."""
    monkeypatch.setattr(sys, "stderr", io.StringIO)
    return capellambse.MelodyModel(
        TEST_ROOT / "6_0" / TEST_MODEL,
        **request.param,
    )
