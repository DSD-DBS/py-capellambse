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

import collections.abc as cabc

from capellambse.loader import xmltools

from .. import common as c
from .. import modeltypes
from . import information

XT_COMP_EX_FNC_EX_ALLOC = "org.polarsys.capella.core.data.fa:ComponentExchangeFunctionalExchangeAllocation"
XT_FCALLOC = "org.polarsys.capella.core.data.fa:ComponentFunctionalAllocation"
XT_FCI: cabc.Set[str] = frozenset(
    {
        "org.polarsys.capella.core.data.fa:FunctionalChainInvolvementFunction",
        "org.polarsys.capella.core.data.fa:FunctionalChainInvolvementLink",
    }
)


@c.xtype_handler(None)
class FunctionRealization(c.GenericElement):
    """A realization that links to a function."""

    _xmltag = "ownedFunctionRealizations"


class AbstractExchange(c.GenericElement):
    """Common code for Exchanges."""

    source_port = c.AttrProxyAccessor(c.GenericElement, "source")
    target_port = c.AttrProxyAccessor(c.GenericElement, "target")


@c.xtype_handler(None)
class FunctionInputPort(c.GenericElement):
    """A function input port."""

    _xmltag = "inputs"

    owner = c.ParentAccessor(c.GenericElement)

    exchanges: c.Accessor


@c.xtype_handler(None)
class FunctionOutputPort(c.GenericElement):
    """A function output port."""

    _xmltag = "outputs"

    owner = c.ParentAccessor(c.GenericElement)

    exchanges: c.Accessor


@c.xtype_handler(None)
class FunctionalExchange(AbstractExchange):
    """A functional exchange."""

    _xmltag = "ownedFunctionalExchanges"

    exchange_items = c.AttrProxyAccessor(
        information.ExchangeItem, "exchangedItems", aslist=c.ElementList
    )


@c.xtype_handler(None)
class FunctionalChain(c.GenericElement):
    """A functional chain."""


@c.xtype_handler(None)
class ComponentPort(c.GenericElement):
    """A component port."""

    _xmltag = "ownedFeatures"

    direction = xmltools.EnumAttributeProperty(
        "_element", "orientation", modeltypes.FPortDir, writable=False
    )
    owner = c.ParentAccessor(c.GenericElement)
    exchanges: c.Accessor


@c.xtype_handler(None)
class ComponentExchange(AbstractExchange):
    """A functional component exchange."""

    _xmltag = "ownedComponentExchanges"

    func_exchanges = c.ProxyAccessor(
        FunctionalExchange,
        XT_COMP_EX_FNC_EX_ALLOC,
        aslist=c.ElementList,
        follow="targetElement",
    )
    allocated_exchange_items = c.AttrProxyAccessor(
        information.ExchangeItem,
        "convoyedInformations",
        aslist=c.ElementList,
    )

    @property
    def exchange_items(
        self,
    ) -> c.ElementList[information.ExchangeItem]:
        items = self.allocated_exchange_items
        func_exchanges = self.func_exchanges
        assert isinstance(func_exchanges, cabc.Iterable)
        for exchange in func_exchanges:
            items += exchange.exchange_items
        return items


for _port, _exchange in [
    (ComponentPort, ComponentExchange),
    (FunctionInputPort, FunctionalExchange),
    (FunctionOutputPort, FunctionalExchange),
]:
    c.set_accessor(
        _port,
        "exchanges",
        c.ReferenceSearchingAccessor(
            _exchange,
            "source_port",
            "target_port",
            aslist=c.ElementList,
        ),
    )
del _port, _exchange
