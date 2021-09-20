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
"""Utility classes that are used across all layers.

.. diagram:: [CDB] BaseLayer ORM
"""
from .. import common as c
from . import cs, information


class BaseArchitectureLayer(c.GenericElement):
    """A template architecture layer."""

    _xmltag = "ownedArchitectures"

    data_package = c.ProxyAccessor(information.DataPkg)
    interface_package = c.ProxyAccessor(cs.InterfacePkg)

    all_classes = c.ProxyAccessor(
        information.Class, deep=True, aslist=c.ElementList
    )
    all_interfaces = c.ProxyAccessor(
        cs.Interface, deep=True, aslist=c.ElementList
    )
