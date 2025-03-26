# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

import pytest

import capellambse

from .conftest import INSTALLED_PACKAGE, Models  # type: ignore

(MODEL_PATH,) = Models.test7_0.glob("*.aird")
JSON_PATH = INSTALLED_PACKAGE.joinpath("known_models", "test-7.0.json")


def test_enumerate_known_models_contains_known_test_models():
    expected = {"test-7.0.json", "test-lib.json"}

    actual = {i.name for i in capellambse.enumerate_known_models()}

    assert actual >= expected


def test_climodel_is_idempotent(
    session_shared_model: capellambse.MelodyModel,
) -> None:
    paramtype = capellambse.ModelCLI()

    converted = paramtype.convert(session_shared_model, None, None)

    assert converted is session_shared_model


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(JSON_PATH.stem, id="str-known"),
        pytest.param(str(MODEL_PATH), id="str-aird"),
        pytest.param(MODEL_PATH, id="path-aird"),
        pytest.param(str(JSON_PATH), id="str-jsonfile"),
        pytest.param(JSON_PATH, id="path-jsonfile"),
        pytest.param(JSON_PATH.read_text(), id="json"),
    ],
)
def test_climodel_loads_model(value):
    paramtype = capellambse.ModelCLI()

    converted = paramtype.convert(value, None, None)

    assert isinstance(converted, capellambse.MelodyModel)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(JSON_PATH.stem, id="str-known"),
        pytest.param(str(MODEL_PATH), id="str-aird"),
        pytest.param(MODEL_PATH, id="path-aird"),
        pytest.param(str(JSON_PATH), id="str-jsonfile"),
        pytest.param(JSON_PATH, id="path-jsonfile"),
        pytest.param(JSON_PATH.read_text(), id="json"),
    ],
)
def test_loadcli_loads_model(value):
    model = capellambse.loadcli(value)

    assert isinstance(model, capellambse.MelodyModel)
