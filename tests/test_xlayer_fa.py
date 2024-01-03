# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from capellambse import MelodyModel


def test_function_port_has_state_machines(model: MelodyModel):
    port = model.by_uuid("226878bc-3e4b-4236-ba72-996fc1d988c0")
    stm = model.by_uuid("06cefb2b-534e-4453-9aba-fe53329197ad")
    assert stm in port.state_machines
