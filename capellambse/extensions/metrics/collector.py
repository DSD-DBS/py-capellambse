# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Collection of tools for collection of statistical data from a model.

Objects of interest are those that we see people working on most. We
think that counting those may help us with model complexity evaluation -
for example identify if a model is big or small or see where the
modeling focus is (problem space / solution space / balanced)
"""

import capellambse
import capellambse.metamodel as mm
import capellambse.model as m
from capellambse.extensions import reqif

COMMON_OBJECTS = [
    mm.capellacommon.StateMachine,
    mm.cs.PhysicalLink,
    mm.fa.ComponentExchange,
    mm.fa.FunctionalExchange,
    mm.information.Class,
    mm.information.ExchangeItem,
    reqif.Requirement,
]

OBJECTS_OF_INTEREST: dict[str, list[type[m.ModelElement]]] = {
    "oa": [
        *COMMON_OBJECTS,
        mm.oa.OperationalCapability,
        mm.oa.OperationalActivity,
        mm.oa.Entity,
    ],
    "sa": [
        *COMMON_OBJECTS,
        mm.sa.SystemFunction,
        mm.sa.SystemComponent,
    ],
    "la": [
        *COMMON_OBJECTS,
        mm.la.LogicalFunction,
        mm.la.LogicalComponent,
    ],
    "pa": [
        *COMMON_OBJECTS,
        mm.pa.PhysicalFunction,
        mm.pa.PhysicalComponent,
    ],
}


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
    model_root = model.project.model_root
    for layer, object_types in OBJECTS_OF_INTEREST.items():
        if layer_obj := getattr(model_root, layer, None):
            layer_objects = len(model.search(*object_types, below=layer_obj))
            layer_diagrams = len(layer_obj.diagrams)
        else:
            layer_objects = 0
            layer_diagrams = 0
        objects.append(layer_objects)
        diagrams.append(layer_diagrams)
    return objects, diagrams
