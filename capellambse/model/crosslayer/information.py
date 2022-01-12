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
"""Implementation of objects and relations for Information capture and data modelling

Information objects inheritance tree (taxonomy):

.. diagram:: [CDB] Information [Taxonomy]

Information object-relations map (ontology):

.. diagram:: [CDB] Information [Ontology]
"""

from __future__ import annotations

from capellambse.loader import xmltools

from .. import common as c
from .. import modeltypes
from . import capellacommon

XT_LITERAL_NUM_VAL = (
    "org.polarsys.capella.core.data.information.datavalue:LiteralNumericValue"
)
XT_LITERAL_STR_VAL = (
    "org.polarsys.capella.core.data.information.datavalue:LiteralStringValue"
)
XT_ENUM_REF = (
    "org.polarsys.capella.core.data.information.datavalue:EnumerationReference"
)


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
class Unit(c.GenericElement):
    """Unit"""

    _xmltag = "ownedUnits"


class LiteralValue(c.GenericElement):
    is_abstract = xmltools.BooleanAttributeProperty(
        "_element",
        "abstract",
        __doc__="Boolean flag, indicates if property is abstract",
    )
    value = xmltools.AttributeProperty(
        "_element", "value", optional=True, returntype=str
    )
    type = c.AttrProxyAccessor(c.GenericElement, "abstractType")


@c.xtype_handler(None, XT_LITERAL_NUM_VAL)
class LiteralNumericValue(LiteralValue):
    value = xmltools.AttributeProperty(
        "_element", "value", optional=True, returntype=float
    )
    unit = c.AttrProxyAccessor(c.GenericElement, "unit")


@c.xtype_handler(None, XT_LITERAL_STR_VAL)
class LiteralStringValue(LiteralValue):
    pass


@c.xtype_handler(None)
class Property(c.GenericElement):
    """A Property of a Class."""

    _xmltag = "ownedFeatures"

    is_ordered = xmltools.BooleanAttributeProperty(
        "_element",
        "ordered",
        __doc__="Boolean flag, indicates if property is ordered",
    )
    is_unique = xmltools.BooleanAttributeProperty(
        "_element",
        "unique",
        __doc__="Boolean flag, indicates if property is unique",
    )
    is_abstract = xmltools.BooleanAttributeProperty(
        "_element",
        "isAbstract",
        __doc__="Boolean flag, indicates if property is abstract",
    )
    is_static = xmltools.BooleanAttributeProperty(
        "_element",
        "isStatic",
        __doc__="Boolean flag, indicates if property is static",
    )
    is_part_of_key = xmltools.BooleanAttributeProperty(
        "_element",
        "isPartOfKey",
        __doc__="Boolean flag, indicates if property is part of key",
    )
    is_derived = xmltools.BooleanAttributeProperty(
        "_element",
        "isDerived",
        __doc__="Boolean flag, indicates if property is abstract",
    )
    is_read_only = xmltools.BooleanAttributeProperty(
        "_element",
        "isReadOnly",
        __doc__="Boolean flag, indicates if property is read-only",
    )
    visibility = xmltools.EnumAttributeProperty(
        "_element", "visibility", modeltypes.VisibilityKind, default="UNSET"
    )
    type = c.AttrProxyAccessor(c.GenericElement, "abstractType")
    default_value = c.RoleTagAccessor("ownedDefaultValue")
    min = c.RoleTagAccessor("ownedMinValue")
    max = c.RoleTagAccessor("ownedMaxValue")
    null_value = c.RoleTagAccessor("ownedNullValue")
    min_card = c.RoleTagAccessor("ownedMinCard")
    max_card = c.RoleTagAccessor("ownedMaxCard")


@c.xtype_handler(None)
class Class(c.GenericElement):
    """A Class."""

    _xmltag = "ownedClasses"

    sub: c.Accessor
    super: c.Accessor[Class]
    is_abstract = xmltools.BooleanAttributeProperty(
        "_element",
        "abstract",
        __doc__="Boolean flag, indicates if class is abstract",
    )
    is_final = xmltools.BooleanAttributeProperty(
        "_element",
        "final",
        __doc__="Boolean flag, indicates if class is final",
    )
    is_primitive = xmltools.BooleanAttributeProperty(
        "_element",
        "isPrimitive",
        __doc__="Boolean flag, indicates if class is primitive",
    )
    visibility = xmltools.EnumAttributeProperty(
        "_element", "visibility", modeltypes.VisibilityKind, default="UNSET"
    )
    state_machines = c.ProxyAccessor(
        capellacommon.StateMachine, aslist=c.ElementList
    )
    owned_properties = c.ProxyAccessor(
        Property, aslist=c.ElementList, follow_abstract=False
    )

    @property
    def properties(self) -> c.ElementList[Property]:
        """Return all owned and inherited properties."""
        return (
            self.owned_properties + self.super.properties
            if self.super is not None
            else self.owned_properties
        )


@c.xtype_handler(None)
class Union(Class):
    """A Union."""

    _xmltag = "ownedClasses"

    kind = xmltools.EnumAttributeProperty(
        "_element", "kind", modeltypes.UnionKind, default="UNION"
    )


@c.xtype_handler(None)
class Collection(c.GenericElement):
    """A Collection."""

    _xmltag = "ownedCollections"

    kind = xmltools.EnumAttributeProperty(
        "_element", "kind", modeltypes.CollectionKind, default="ARRAY"
    )

    sub: c.Accessor
    super: c.Accessor[Collection]


@c.xtype_handler(
    None, "org.polarsys.capella.core.data.information.datavalue:ValuePart"
)
class ValuePart(c.GenericElement):
    """A Value Part of a Complex Value."""

    _xmltag = "ownedParts"
    referenced_property = c.AttrProxyAccessor(
        c.GenericElement, "referencedProperty"
    )
    value = c.RoleTagAccessor("ownedValue")


@c.xtype_handler(
    None, "org.polarsys.capella.core.data.information.datavalue:ComplexValue"
)
class ComplexValue(c.GenericElement):
    """A Complex Value."""

    _xmltag = "ownedDataValues"
    type = c.AttrProxyAccessor(c.GenericElement, "abstractType")
    value_parts = c.ProxyAccessor(
        ValuePart,
        "org.polarsys.capella.core.data.information.datavalue:ValuePart",
        aslist=c.ElementList,
    )


@c.xtype_handler(
    None,
    "org.polarsys.capella.core.data.information.datavalue:EnumerationLiteral",
)
class EnumerationLiteral(c.GenericElement):
    """An EnumerationLiteral (proxy link)."""

    _xmltag = "ownedLiterals"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.name == other
        return super().__eq__(other)

    name = xmltools.AttributeProperty("_element", "name", returntype=str)
    owner: c.Accessor


@c.xtype_handler(None, XT_ENUM_REF)
class EnumerationReference(c.GenericElement):
    name = xmltools.AttributeProperty("_element", "name", returntype=str)
    type = c.AttrProxyAccessor(c.GenericElement, "abstractType")
    value = c.AttrProxyAccessor(c.GenericElement, "referencedValue")


@c.xtype_handler(
    None, "org.polarsys.capella.core.data.information.datatype:Enumeration"
)
class Enumeration(c.GenericElement):
    """An Enumeration."""

    _xmltag = "ownedDataTypes"

    sub: c.Accessor
    super: c.Accessor[Enumeration]
    owned_literals = c.ProxyAccessor(
        EnumerationLiteral,
        "org.polarsys.capella.core.data.information.datavalue:EnumerationLiteral",
        aslist=c.ElementList,
        follow_abstract=False,
    )

    @property
    def literals(self) -> c.ElementList[EnumerationLiteral]:
        """Return all owned and inherited literals."""
        return (
            self.owned_literals + self.super.literals
            if isinstance(self.super, Enumeration)
            else self.owned_literals
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
    complex_values = c.ProxyAccessor(
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


for cls in [Class, Union, Enumeration, Collection]:
    c.set_accessor(
        cls,
        "super",
        c.ProxyAccessor(
            cls,
            "org.polarsys.capella.core.data.capellacore:Generalization",
            follow="super",
            follow_abstract=False,
        ),
    )
    c.set_accessor(
        cls,
        "sub",
        c.ReferenceSearchingAccessor(cls, "super", aslist=c.MixedElementList),
    )

c.set_accessor(EnumerationLiteral, "owner", c.ParentAccessor(Enumeration))
c.set_accessor(
    DataPkg, "packages", c.ProxyAccessor(DataPkg, aslist=c.ElementList)
)
c.set_accessor(ExchangeItemElement, "owner", c.ParentAccessor(ExchangeItem))
