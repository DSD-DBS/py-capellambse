# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Tools for statistical evaluation of model contents."""

import capellambse

from . import composer
from .collector import *


def get_summary_badge(model: capellambse.MelodyModel) -> str:
    """Provide visual summary of model contents."""
    objects, diagrams = quantify_model_layers(model)
    return composer.draw_summary_badge(objects, diagrams)
