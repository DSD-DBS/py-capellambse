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
"""The AIRD parser and various other diagramming related tools.

This module is used to enumerate, access and export the diagrams from
Capella projects.  The JSON output it produces can be fed for example
into the :mod:`capellambse.svg` module for conversion to SVG.
"""
from .vector2d import *  # isort: skip
from .capstyle import *
from .diagram import *
from .json_enc import *
from .parser import *
