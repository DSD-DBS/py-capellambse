# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

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
