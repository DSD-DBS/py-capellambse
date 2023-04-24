# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Collection of tools for collection of statistical data from a model.

Objects of interest are those that we see people working on most. We
think that counting those may help us with model complexity evaluation -
for example identify if a model is big or small or see where the
modeling focus is (problem space / solution space / balanced)
"""

from __future__ import annotations

__all__ = [
    "BinCountResults",
    "get_compliance_score",
    "get_passed_and_total",
    "get_total_objects",
    "quantify_model_layers",
]

import collections.abc as cabc
from itertools import chain

import capellambse
from capellambse.extensions import validation as v

COMMON_OBJECTS = [
    "Requirement",
    "Class",
    "StateMachine",
    "PhysicalLink",
    "FunctionalExchange",
    "ComponentExchange",
    "ExchangeItem",
]
OBJECTS_OF_INTEREST = [
    [  # Operational Analysis
        "OperationalCapability",
        "OperationalActivity",
        "Entity",
    ]
    + COMMON_OBJECTS,
    ["SystemFunction", "SystemComponent"] + COMMON_OBJECTS,  # System Analysis
    [  # Logical Architecture
        "LogicalFunction",
        "LogicalComponent",
    ]
    + COMMON_OBJECTS,
    [  # Physical Architecture
        "PhysicalFunction",
        "PhysicalComponent",
    ]
    + COMMON_OBJECTS,
]


def quantify_model_layers(
    model: capellambse.MelodyModel,
) -> tuple[list[int], list[int]]:
    """Count objects of interest and diagrams on model layers.

    Returns
    -------
    list
        The number of interesting objects per model layer
    list
        The number of diagrams per model layer

    Notes
    -----
    The order of numbers in a list corresponds to the order of model
    layers - OA, SA, LA, PA.
    """
    objects = []
    diagrams = []
    for layer, object_types in zip(
        [model.oa, model.sa, model.la, model.pa], OBJECTS_OF_INTEREST
    ):
        layer_objects = len(model.search(*object_types, below=layer))
        objects.append(layer_objects)
        diagrams.append(len(layer.diagrams))
    return objects, diagrams


def get_passed_and_total(
    result_container: v.Results | dict[v.Rule, v.Result], /
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
        total += 1
        passed += result.value
    return passed, total


def get_compliance_score(
    numerator: int | float, denominator: int | float
) -> float:
    """Return the fraction in percentage."""
    return numerator / denominator * 100


def get_total_objects(
    types: cabc.Iterable[str], all_results: v.Results
) -> BinCountResults:
    results = v.Results({})
    for type in types:
        results.update(all_results.by_type(type))

    return BinCountResults(results, types)


class BinCountResults:
    def __init__(self, results: v.Results, types: cabc.Iterable[str]) -> None:
        self.results = results
        self.types = set(types)

    @property
    def amount(self) -> int:
        _, total = get_passed_and_total(self.results)
        return total

    def by_category(self, category: str) -> tuple[int, int]:
        results = self.results.by_category(category)
        return get_passed_and_total(results)
