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
from capellambse.loader import xmltools

from .. import common as c
from . import capellacommon, information


class Component(c.GenericElement):
    """A template class for components."""

    is_abstract = xmltools.BooleanAttributeProperty(
        "_element",
        "abstract",
        __doc__="Boolean flag for an abstract Component",
    )
    is_human = xmltools.BooleanAttributeProperty(
        "_element", "human", __doc__="Boolean flag for a human Component"
    )
    is_actor = xmltools.BooleanAttributeProperty(
        "_element", "actor", __doc__="Boolean flag for an actor Component"
    )

    owner = c.ParentAccessor(c.GenericElement)
    state_machines = c.ProxyAccessor(
        capellacommon.StateMachine, aslist=c.ElementList
    )

    parts: c.Accessor


@c.xtype_handler(None)
class Part(c.GenericElement):
    type = c.AttrProxyAccessor(c.GenericElement, "abstractType")


@c.xtype_handler(None)
class Interface(c.GenericElement):
    """An interface."""


@c.xtype_handler(None)
class InterfacePkg(c.GenericElement):
    """A package that can hold interfaces and exchange items."""

    exchange_items = c.ProxyAccessor(
        information.ExchangeItem,
        aslist=c.ElementList,
    )
    interfaces = c.ProxyAccessor(Interface, aslist=c.ElementList)
    packages: c.Accessor


@c.xtype_handler(None)
class PhysicalPort(c.GenericElement):
    """A physical port."""

    _xmltag = "ownedFeatures"

    owner = c.ParentAccessor(c.GenericElement)


@c.xtype_handler(None)
class PhysicalLink(PhysicalPort):
    """A physical link."""

    linkEnds = c.AttrProxyAccessor(
        PhysicalPort, "linkEnds", aslist=c.ElementList
    )


@c.xtype_handler(None)
class ComponentRealization(c.GenericElement):
    """A realization that links to a component."""

    _xmltag = "ownedComponentRealizations"


c.set_accessor(
    Component,
    "parts",
    c.ReferenceSearchingAccessor(Part, "type", aslist=c.ElementList),
)
c.set_accessor(
    InterfacePkg,
    "packages",
    c.ProxyAccessor(InterfacePkg, aslist=c.ElementList),
)
