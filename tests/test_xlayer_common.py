# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

import collections.abc as cabc

import pytest

import capellambse


def test_state_realized_states(model: capellambse.MelodyModel) -> None:
    state = model.by_uuid("43932114-8ad4-4074-b2a9-b0d55b8d027b")
    real = model.by_uuid("461de288-fa3f-45bd-9975-8ebe1aec85d9")
    real1 = model.by_uuid("757c825f-f522-4d90-b3af-071a4cec3f06")

    assert state.realized_states[0].realizing_states[0] == state
    assert state.realized_states == [real, real1]


def test_state_realizing_states(model: capellambse.MelodyModel) -> None:
    state = model.by_uuid("461de288-fa3f-45bd-9975-8ebe1aec85d9")
    real = model.by_uuid("43932114-8ad4-4074-b2a9-b0d55b8d027b")

    assert state.realizing_states == [real]


@pytest.mark.parametrize(
    "attr,uuids",
    [
        ("entries", ("0e0164c3-076e-42c1-8f82-7a43ab84385c",)),
        ("do_activity", ("8bcb11e6-443b-4b92-bec2-ff1d87a224e7",)),
        (
            "exits",
            (
                "ab016025-d456-4c2d-8359-d50cf9de3825",
                "f33bd79c-fa90-4c09-942b-581dc7f07d84",
                "04babdbf-6cf6-4846-a207-bf27cfc8eb32",
            ),
        ),
    ],
)
def test_state_attributes(
    model_5_2: capellambse.MelodyModel, attr: str, uuids: cabc.Iterable[str]
) -> None:
    state = model_5_2.by_uuid("6c48b9c5-0d43-4a43-9e9d-9559cb52c83e")
    expected_functions = [model_5_2.by_uuid(uuid) for uuid in uuids]

    functions = getattr(state, attr)

    assert functions == expected_functions
