# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Tools for statistical evaluation of model contents."""

from __future__ import annotations

import collections.abc as cabc
from itertools import chain

import capellambse
from capellambse.extensions import validation as v

from .collector import quantify_model_layers
from .composer import draw_summary_badge


def get_summary_badge(model: capellambse.MelodyModel) -> str:
    """Provide visual summary of model contents."""
    objects, diagrams = quantify_model_layers(model)
    return draw_summary_badge(objects, diagrams)


def get_passed_and_total(
    result_container: v.Results | dict[v.Rule, v.Result],
    type: str | None = None,
) -> tuple[int, int]:
    """Return the number of passed and total validation rules."""
    results: cabc.Iterable[v.Result]
    if isinstance(result_container, v.Results):
        results = chain.from_iterable(
            (result.values() for result in result_container.values())
        )
    else:
        results = result_container.values()

    total, passed = 0, 0
    for result in results:
        if type and type != result.object.__class__.__name__:
            continue

        total += 1
        passed += result.value
    return passed, total


def get_compliance_score(
    numerator: int | float, denominator: int | float
) -> float:
    """Return the fraction in percentage."""
    return numerator / denominator * 100
