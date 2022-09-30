# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import capellambse

# pylint: disable=pointless-statement


def test_AttributeAuditor_tracks_uuids_of_accessed_ModelElements(
    model: capellambse.MelodyModel,
):
    comp, comp1, comp2 = model.la.all_components[:3]
    expected = {comp.uuid, comp2.uuid}
    with capellambse.AttributeAuditor(
        model, {"name", "description"}
    ) as recorded_ids:
        comp.name
        comp1.uuid
        comp2.description

    assert expected == recorded_ids


def test_AttributeAuditor_handles_recursive_uuid(
    model: capellambse.MelodyModel,
):
    comp = model.la.all_components[0]
    with capellambse.AttributeAuditor(model, {"uuid"}) as recorded_ids:
        comp.uuid

    assert {comp.uuid} == recorded_ids


def test_AttributeAuditor_destroys_model_reference_when_detach(
    model: capellambse.MelodyModel,
):
    auditor = capellambse.AttributeAuditor(model, {"name"})

    auditor.detach()

    assert auditor.model is None
