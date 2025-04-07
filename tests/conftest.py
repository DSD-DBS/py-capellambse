# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Global fixtures for pytest."""

import importlib.metadata as imm
import pathlib

import pytest

import capellambse

INSTALLED_PACKAGE = pathlib.Path(capellambse.__file__).parent
TEST_DATA = pathlib.Path(__file__).parent / "data"

capellambse.load_model_extensions()

if not any(
    i.module.startswith("capellambse.extensions.")
    for i in imm.entry_points(group="capellambse.model_extensions")
):
    raise RuntimeError(
        "Built-in model extensions are not loaded,"
        " is capellambse installed properly?"
    )


@pytest.fixture(scope="session")
def session_shared_model() -> capellambse.MelodyModel:
    """Load the standard test model.

    Unlike the ``model`` fixture, this fixture is shared across the
    entire test session. As such, the test functions using this fixture
    are expected to not modify it.

    This fixture exists as a speed optimization for tests that only read
    from the model.
    """
    return capellambse.MelodyModel(TEST_DATA.joinpath("models", "7.0"))


@pytest.fixture
def model() -> capellambse.MelodyModel:
    """Load the Capella 7.0 test model."""
    return capellambse.MelodyModel(TEST_DATA.joinpath("models", "7.0"))


@pytest.fixture
def empty_model() -> capellambse.MelodyModel:
    """Load the empty test model."""
    return capellambse.MelodyModel(TEST_DATA.joinpath("models", "empty"))
