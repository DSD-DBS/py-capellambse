# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Collection of tools for collection of statistical data from a model.

Objects of interest are those that we see people working on most. We
think that counting those may help us with model complexity evaluation -
for example identify if a model is big or small or see where the
modeling focus is (problem space / solution space / balanced)
"""

import capellambse

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
