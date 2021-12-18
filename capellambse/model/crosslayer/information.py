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

from capellambse.loader import xmltools

from .. import common as c
from .. import modeltypes
from . import capellacommon


def _allocated_exchange_items(
    obj: c.GenericElement,
) -> c.ElementList[c.GenericElement]:
    try:
        return obj.exchange_items
    except AttributeError:
        pass

    try:
        return obj.allocated_exchange_items
    except AttributeError:
        pass

    raise TypeError(
        f"Unhandled exchange type: {type(obj).__name__}"
    )  # pragma: no cover


def _search_all_exchanges(
    obj: c.GenericElement,
) -> c.ElementList[c.GenericElement]:
    from . import fa

    return obj._model.search(fa.ComponentExchange, fa.FunctionalExchange)


@c.xtype_handler(None)
class Class(c.GenericElement):
    """A Class."""

    _xmltag = "ownedClasses"

    sub = c.Accessor
    super = c.Accessor
    state_machines = c.ProxyAccessor(
        capellacommon.StateMachine, aslist=c.ElementList
    )


@c.xtype_handler(None)
class Union(c.GenericElement):
    """A Union."""

    _xmltag = "ownedClasses"

    state_machines = c.ProxyAccessor(
        capellacommon.StateMachine, aslist=c.ElementList
    )


@c.xtype_handler(None)
class Collection(c.GenericElement):
    """A Collection."""

    _xmltag = "ownedCollections"

    state_machines = c.ProxyAccessor(
        capellacommon.StateMachine, aslist=c.ElementList
    )


@c.xtype_handler(
    None, "org.polarsys.capella.core.data.information.datavalue:ComplexValue"
)
class ComplexValue(c.GenericElement):
    """A Complex Value."""

    _xmltag = "ownedDataValues"
    type = c.AttrProxyAccessor(c.GenericElement, "abstractType")


@c.xtype_handler(
    None,
    "org.polarsys.capella.core.data.information.datavalue:EnumerationLiteral",
)
class EnumerationLiteral(c.GenericElement):
    """An EnuemrationLiteral (proxy link)."""

    _xmltag = "ownedLiterals"

    owner: c.Accessor


@c.xtype_handler(
    None, "org.polarsys.capella.core.data.information.datatype:Enumeration"
)
class Enumeration(c.GenericElement):
    """An Enumeration."""

    _xmltag = "ownedDataTypes"

    sub = c.Accessor
    super: Enumeration = c.Accessor  # type: ignore
    own_literals = c.ProxyAccessor(
        EnumerationLiteral,
        "org.polarsys.capella.core.data.information.datavalue:EnumerationLiteral",
        aslist=c.ElementList,
        follow_abstract=False,
    )

    @property
    def literals(self) -> c.ElementList[EnumerationLiteral]:
        """Return all owned and inherited literals."""
        return (
            self.own_literals + self.super.literals
            if isinstance(self.super, Enumeration)
            else self.own_literals
        )


@c.xtype_handler(None)
class DataPkg(c.GenericElement):
    """A data package that can hold classes."""

    classes = c.ProxyAccessor(Class, aslist=c.ElementList)
    unions = c.ProxyAccessor(Union, aslist=c.ElementList)
    collections = c.ProxyAccessor(Collection, aslist=c.ElementList)
    enumerations = c.ProxyAccessor(
        Enumeration,
        "org.polarsys.capella.core.data.information.datatype:Enumeration",
        aslist=c.ElementList,
    )
    datavalues = c.ProxyAccessor(
        ComplexValue,
        "org.polarsys.capella.core.data.information.datavalue:ComplexValue",
        aslist=c.ElementList,
        follow_abstract=False,
    )
    packages: c.Accessor


@c.xtype_handler(None)
class ExchangeItemElement(c.GenericElement):
    """An ExchangeItemElement (proxy link)."""

    _xmltag = "ownedElements"

    abstract_type = c.AttrProxyAccessor(c.GenericElement, "abstractType")
    owner: c.Accessor


@c.xtype_handler(None)
class ExchangeItem(c.GenericElement):
    """An item that can be exchanged on an Exchange."""

    _xmltag = "ownedExchangeItems"

    type = xmltools.EnumAttributeProperty(
        "_element",
        "exchangeMechanism",
        modeltypes.ExchangeItemType,
        default="UNSET",
    )
    elements = c.ProxyAccessor(
        ExchangeItemElement,
        aslist=c.ElementList,
        follow_abstract=False,
    )
    exchanges = c.CustomAccessor(
        c.GenericElement,
        _search_all_exchanges,
        matchtransform=_allocated_exchange_items,
        aslist=c.ElementList,
    )


c.set_accessor(
    Class,
    "super",
    c.ProxyAccessor(
        Class,
        "org.polarsys.capella.core.data.capellacore:Generalization",
        follow="super",
        follow_abstract=False,
    ),
)
c.set_accessor(
    Class,
    "sub",
    c.ReferenceSearchingAccessor(Class, "super", aslist=c.ElementList),
)
c.set_accessor(
    Enumeration,
    "super",
    c.ProxyAccessor(
        Enumeration,
        "org.polarsys.capella.core.data.capellacore:Generalization",
        follow="super",
        follow_abstract=False,
    ),
)
c.set_accessor(
    Enumeration,
    "sub",
    c.ReferenceSearchingAccessor(Enumeration, "super", aslist=c.ElementList),
)
c.set_accessor(EnumerationLiteral, "owner", c.ParentAccessor(Enumeration))
c.set_accessor(
    DataPkg, "packages", c.ProxyAccessor(DataPkg, aslist=c.ElementList)
)
c.set_accessor(ExchangeItemElement, "owner", c.ParentAccessor(ExchangeItem))
