# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""The AIRD parser and various other diagramming related tools.

This module is used to enumerate, access and export the diagrams from
Capella projects.  The JSON output it produces can be fed for example
into the :mod:`capellambse.svg` module for conversion to SVG.
"""
# isort: off
from .vector2d import *

from .capstyle import *
from .diagram import *
from .json_enc import *
from .parser import *
