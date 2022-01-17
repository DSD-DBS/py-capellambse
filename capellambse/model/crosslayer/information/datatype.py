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
from __future__ import annotations

from ... import common as c
from . import datavalue


@c.xtype_handler(None)
class Enumeration(c.GenericElement):
    """An Enumeration."""

    _xmltag = "ownedDataTypes"

    owned_literals = c.ProxyAccessor(
        datavalue.EnumerationLiteral,
        aslist=c.ElementList,
        follow_abstract=False,
    )

    sub: c.Accessor
    super: c.Accessor[Enumeration]

    @property
    def literals(self) -> c.ElementList[datavalue.EnumerationLiteral]:
        """Return all owned and inherited literals."""
        return (
            self.owned_literals + self.super.literals
            if isinstance(self.super, Enumeration)
            else self.owned_literals
        )
