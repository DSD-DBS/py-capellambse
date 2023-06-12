# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import capellambse
from capellambse.extensions import metrics, validation


def test_get_summary_badge(model: capellambse.MelodyModel):
    badge = metrics.get_summary_badge(model)

    assert isinstance(badge, str)


def test_get_passed_and_total_results(model: capellambse.MelodyModel):
    assert isinstance(model.validation, validation.ModelValidation)
    assert model.validation.rules

    results = model.validate()
    passed, total = metrics.get_passed_and_total(results)

    assert isinstance(passed, int) and isinstance(total, int)


def test_get_compliance_score():
    score = metrics.get_compliance_score(8, 10)

    assert score == 80.0
