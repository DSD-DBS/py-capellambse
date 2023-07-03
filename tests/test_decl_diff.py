# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import io
import pathlib
import sys
import typing as t

import pytest

import capellambse
from capellambse import decl, helpers

# pylint: disable-next=relative-beyond-top-level, useless-suppression
from .conftest import TEST_MODEL, TEST_ROOT  # type: ignore[import]

SYS_ENG_ROOT_UUID = helpers.UUIDString("b8619b46-0c12-4f85-befe-358d00a3886b")
PARENT_UUID = helpers.UUIDString("474e84b1-3485-4012-86ba-c638767cb529")
HOGWARTS_UUID = helpers.UUIDString("0d2edb8f-fa34-4e73-89ec-fb9a63001440")
CAMPUS_UUID = helpers.UUIDString("6583b560-6d2f-4190-baa2-94eef179c8ea")
PORT_UUID = helpers.UUIDString("d7e0cc4d-eef6-4173-9a21-1bd933a5d9f0")
LITERAL_NUMERIC_VALUE_UUID = helpers.UUIDString(
    "303c2a4d-0eff-41e6-b7e8-0e500cfa38f7"
)
ASSOC_UUID = helpers.UUIDString("3d738685-83e8-45f9-ade2-d5bcc6de1a0c")
PROP_UUID = helpers.UUIDString("e849a8a1-e6eb-4b6e-ab79-81c3e59469e0")

TEST_EMPTY_ROOT = pathlib.Path(__file__).parent / "data" / "decl"
TEST_MODEL_NAME = "empty_project_52.aird"
TEST_EMPTY = TEST_EMPTY_ROOT / "empty_project_52" / "empty_project_52.aird"


@pytest.fixture
def left(monkeypatch: pytest.MonkeyPatch) -> capellambse.MelodyModel:
    monkeypatch.setattr(sys, "stderr", io.StringIO)
    return capellambse.MelodyModel(TEST_ROOT / TEST_EMPTY)


# pylint: disable=redefined-outer-name  # false-positive
def test_decl_diff_same_models_produce_empty_diff(
    left: capellambse.MelodyModel,
):
    right = capellambse.MelodyModel(TEST_ROOT / TEST_EMPTY)
    diff = decl.diff(left, right)

    assert not diff


@pytest.mark.parametrize(
    "expected",
    [
        pytest.param(
            {
                "parent": decl.UUIDReference(HOGWARTS_UUID),
                "modify": {"name": "Coffee Machine"},
            },
            id="String attribute",
        ),
        pytest.param(
            {
                "parent": decl.UUIDReference(CAMPUS_UUID),
                "modify": {"is_actor": True},
            },
            id="Boolean attribute",
        ),
    ],
)
def test_decl_diff_simple_attribute_modification(
    model_5_2: capellambse.MelodyModel, expected: dict[str, t.Any]
):
    right = capellambse.MelodyModel(TEST_ROOT / "5_2" / TEST_MODEL)
    instructions = io.StringIO(decl.dump([expected]))
    decl.apply(right, instructions)

    diff = decl.diff(model_5_2, right)

    assert diff == [expected]


@pytest.mark.parametrize(
    "parent,extensions",
    [
        pytest.param(
            decl.UUIDReference(HOGWARTS_UUID),
            {
                "exchanges": [
                    {
                        "name": "magic",
                        "source": decl.UUIDReference(
                            helpers.UUIDString(
                                "fcbf6881-720c-421f-9fe9-12fc3dfefe9c"
                            )
                        ),
                        "target": decl.UUIDReference(
                            helpers.UUIDString(
                                "42c60b17-b503-46d6-8b0c-f1ff0fd4b8ac"
                            )
                        ),
                    }
                ],
            },
            id="Component Exchange",
        ),
        pytest.param(
            decl.UUIDReference(HOGWARTS_UUID),
            {
                "components": [
                    {
                        "name": "User",
                        "is_actor": True,
                        "is_human": True,
                        "ports": [{"name": "cm", "direction": "INOUT"}],
                    }
                ]
            },
            id="Component and ComponentPort",
        ),
    ],
)
def test_decl_diff_model_extension(
    model_5_2: capellambse.MelodyModel,
    parent: decl.UUIDReference,
    extensions: dict[str, t.Any],
):
    right = capellambse.MelodyModel(TEST_ROOT / "5_2" / TEST_MODEL)
    expected = {"parent": parent, "extend": extensions}
    instructions = io.StringIO(decl.dump([expected]))
    decl.apply(right, instructions)

    diff = decl.diff(model_5_2, right)

    assert diff == [expected]


@pytest.mark.parametrize(
    "parent,target",
    [
        pytest.param(
            decl.UUIDReference(HOGWARTS_UUID),
            {
                "exchanges": [
                    decl.UUIDReference(
                        helpers.UUIDString(
                            "a900a6e0-c994-42e8-ae94-2b61a7fabc18"
                        )
                    )
                ]
            },
            id="DirectProxyAccessor",
        ),
        pytest.param(
            decl.UUIDReference(ASSOC_UUID),
            {
                "navigable_members": [
                    decl.UUIDReference(
                        helpers.UUIDString(
                            "424efd65-eaa9-4220-b61b-fb3340dbc19a"
                        )
                    )
                ]
            },
            id="AttrProxyAccessor",
        ),
    ],
)
def test_decl_diff_model_deletion(
    model_5_2: capellambse.MelodyModel,
    parent: decl.UUIDReference,
    target: decl.UUIDReference,
):
    right = capellambse.MelodyModel(TEST_ROOT / "5_2" / TEST_MODEL)
    expected = {"parent": parent, "delete": target}
    instructions = io.StringIO(decl.dump([expected]))
    decl.apply(right, instructions)

    diff = decl.diff(model_5_2, right)

    assert diff == [expected]


@pytest.mark.parametrize(
    "parent,modification",
    [
        pytest.param(
            decl.UUIDReference(HOGWARTS_UUID),
            {"description": "<p>Changed</p>"},
            id="HTMLAttributeProperty",
        ),
        pytest.param(
            decl.UUIDReference(HOGWARTS_UUID),
            {"name": "Hoggywoggy Hogwarts"},
            id="AttributeProperty",
        ),
        pytest.param(
            decl.UUIDReference(LITERAL_NUMERIC_VALUE_UUID),
            {"value": 2},
            id="NumericAttributeProperty",
        ),
        pytest.param(
            decl.UUIDReference(ASSOC_UUID),
            {"navigable_members": [decl.UUIDReference(PROP_UUID)]},
            id="AttrProxyAccessor",
        ),
    ],
)
def test_decl_diff_model_modification(
    model_5_2: capellambse.MelodyModel,
    parent: decl.UUIDReference,
    modification: dict[str, t.Any],
):
    right = capellambse.MelodyModel(TEST_ROOT / "5_2" / TEST_MODEL)
    expected = {"parent": parent, "modify": modification}
    instructions = io.StringIO(decl.dump([expected]))
    decl.apply(right, instructions)

    diff = decl.diff(model_5_2, right)

    assert diff == [expected]
