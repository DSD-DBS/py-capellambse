# Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import capellambse
from capellambse import auditing

# pylint: disable=pointless-statement


def test_AttributeAuditor_tracks_uuids_of_accessed_ModelElements(
    model: capellambse.MelodyModel,
):
    comp, comp1, comp2 = model.la.all_components[:3]
    expected = {comp.uuid, comp2.uuid}
    with auditing.AttributeAuditor(model, {"name", "description"}) as auditor:
        comp.name
        comp1.uuid
        comp2.description

    assert expected == auditor.recorded_ids


def test_AttributeAuditor_handles_recursive_uuid(
    model: capellambse.MelodyModel,
):
    comp = model.la.all_components[0]
    with auditing.AttributeAuditor(model, {"uuid"}) as auditor:
        comp.uuid

    assert {comp.uuid} == auditor.recorded_ids


def test_AttributeAuditor_destroys_model_reference_when_detach(
    model: capellambse.MelodyModel,
):
    auditor = auditing.AttributeAuditor(model, {"name"})

    auditor.detach()

    assert auditor.model is None
