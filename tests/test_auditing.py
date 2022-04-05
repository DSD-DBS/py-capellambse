# Copyright 2021 DB Netz AG
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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


def test_AttributeAuditor_destroys_model_when_detach(
    model: capellambse.MelodyModel,
):
    model_mid = id(model)
    auditor = auditing.AttributeAuditor(model, {"name"})

    auditor.detach()

    assert auditor.model is None
    assert id(auditor.model) != model_mid
