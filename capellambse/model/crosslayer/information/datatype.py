# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from ... import common as c
from . import datavalue


@c.xtype_handler(None)
class Enumeration(c.GenericElement):
    """An Enumeration."""

    _xmltag = "ownedDataTypes"

    owned_literals = c.DirectProxyAccessor(
        datavalue.EnumerationLiteral, aslist=c.ElementList
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
