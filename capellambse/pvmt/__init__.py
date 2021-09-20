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
"""Provides easy access to the Polarsys Capella PVMT extension.

The public API of this submodule uses raw LXML elements.  For a more
object oriented and user friendly way to access property values in a
model, see the :class:`capellambse.MelodyModel` class.
"""

from .exceptions import ScopeError
from .model import PVMTExtension, load_pvmt_from_model
