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
"""The MelodyLoader loads and provides access to a Capella model.

It is using LXML internally to efficiently parse and navigate through
the Capella-generated XML files.  For more information about LXML, see
the `LXML Documentation`_.

.. _LXML Documentation: https://lxml.de/
"""

from .core import MelodyLoader
from .filehandler import FileHandler, get_filehandler
from .modelinfo import ModelInfo
