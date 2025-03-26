# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Global fixtures for pytest."""

import importlib.metadata as imm
import pathlib
import shutil

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


class Models:
    aird_parser = TEST_DATA.joinpath("models", "aird_parser")
    empty = TEST_DATA.joinpath("models", "empty")
    filtering = TEST_DATA.joinpath("models", "filtering")
    lib_proj = TEST_DATA.joinpath("models", "library_project")
    lib_test = TEST_DATA.joinpath("models", "library_test")
    pvmt = TEST_DATA.joinpath("models", "pvmt")
    test7_0 = TEST_DATA.joinpath("models", "test7_0")
    writemodel = TEST_DATA.joinpath("models", "writemodel")


@pytest.fixture(scope="session")
def session_shared_model() -> capellambse.MelodyModel:
    """Load the standard test model.

    Unlike the ``model`` fixture, this fixture is shared across the
    entire test session. As such, the test functions using this fixture
    are expected to not modify it.

    This fixture exists as a speed optimization for tests that only read
    from the model.
    """
    return capellambse.MelodyModel(Models.test7_0)


@pytest.fixture
def model() -> capellambse.MelodyModel:
    """Load the Capella 7.0 test model."""
    return capellambse.MelodyModel(Models.test7_0)


@pytest.fixture
def empty_model() -> capellambse.MelodyModel:
    """Load the empty test model."""
    return capellambse.MelodyModel(Models.empty)


@pytest.fixture
def tmp_model(tmp_path: pathlib.Path) -> pathlib.Path:
    """Copy the Capella 7.0 test model to a temporary directory."""
    path = tmp_path / "model"
    shutil.copytree(Models.test7_0, path)
    return path
