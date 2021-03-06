# Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=no-self-use
import typing as t

import pytest

import capellambse.model.common as c
from capellambse import MelodyModel


def test_function_port_has_state_machines(model: MelodyModel):
    port = model.by_uuid("226878bc-3e4b-4236-ba72-996fc1d988c0")
    stm = model.by_uuid("06cefb2b-534e-4453-9aba-fe53329197ad")
    assert stm in port.state_machines
