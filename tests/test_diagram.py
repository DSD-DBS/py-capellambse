# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

import capellambse

HIDDEN_UUID = "957c5799-1d4a-4ac0-b5de-33a65bf1519c"


def test_diagram_nodes_only_include_visible_elements(
    session_shared_model: capellambse.MelodyModel,
):
    diagram = session_shared_model.diagrams.by_name(
        "[LAB] Hidden Wizzard Education"
    )

    assert HIDDEN_UUID not in diagram.nodes.by_uuid
