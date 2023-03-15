# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Objects and relations for information capture and data modelling.

Information objects inheritance tree (taxonomy):

.. diagram:: [CDB] Information [Taxonomy]

Information object-relations map (ontology):

.. diagram:: [CDB] Information [Ontology]
"""

from __future__ import annotations

from ... import common as c
from ... import modeltypes
from .. import capellacommon, capellacore, modellingcore
from . import datatype, datavalue


@c.xtype_handler(None)
class Unit(c.GenericElement):
    """Unit."""

    _xmltag = "ownedUnits"


@c.xtype_handler(None)
class Association(c.GenericElement):
    """An Association."""

    _xmltag = "ownedAssociations"

    members: c.Accessor[Property]
    navigable_members: c.Accessor[Property]
    source_role: c.Accessor[Property]

    @property
    def roles(self) -> c.ElementList[Property]:
        roles = []
        if self.source_role:
            assert isinstance(self.source_role, c.GenericElement)
            roles.append(self.source_role._element)

        assert isinstance(self.navigable_members, c.ElementList)
        roles.extend(prop._element for prop in self.navigable_members)
        return c.ElementList(self._model, roles, Property)


@c.xtype_handler(None)
class PortAllocation(modellingcore.TraceableElement):
    """An exchange between a ComponentPort and FunctionalPort."""

    _xmltag = "ownedPortAllocations"


@c.xtype_handler(None)
class Property(c.GenericElement):
    """A Property of a Class."""

    _xmltag = "ownedFeatures"

    is_ordered = c.BooleanAttributeProperty(
        "ordered", __doc__="Indicates if property is ordered"
    )
    is_unique = c.BooleanAttributeProperty(
        "unique", __doc__="Indicates if property is unique"
    )
    is_abstract = c.BooleanAttributeProperty(
        "isAbstract", __doc__="Indicates if property is abstract"
    )
    is_static = c.BooleanAttributeProperty(
        "isStatic", __doc__="Indicates if property is static"
    )
    is_part_of_key = c.BooleanAttributeProperty(
        "isPartOfKey", __doc__="Indicates if property is part of key"
    )
    is_derived = c.BooleanAttributeProperty(
        "isDerived", __doc__="Indicates if property is abstract"
    )
    is_read_only = c.BooleanAttributeProperty(
        "isReadOnly", __doc__="Indicates if property is read-only"
    )
    visibility = c.EnumAttributeProperty(
        "visibility", modeltypes.VisibilityKind, default="UNSET"
    )
    kind = c.EnumAttributeProperty(
        "aggregationKind", modeltypes.AggregationKind, default="UNSET"
    )
    type = c.AttrProxyAccessor(c.GenericElement, "abstractType")
    default_value = c.RoleTagAccessor("ownedDefaultValue")
    min = c.RoleTagAccessor("ownedMinValue")
    max = c.RoleTagAccessor("ownedMaxValue")
    null_value = c.RoleTagAccessor("ownedNullValue")
    min_card = c.RoleTagAccessor("ownedMinCard")
    max_card = c.RoleTagAccessor("ownedMaxCard")
    association = c.ReferenceSearchingAccessor(Association, "roles")


@c.xtype_handler(None)
class Class(c.GenericElement):
    """A Class."""

    _xmltag = "ownedClasses"

    sub: c.Accessor
    super: c.Accessor[Class]
    is_abstract = c.BooleanAttributeProperty(
        "abstract", __doc__="Indicates if class is abstract"
    )
    is_final = c.BooleanAttributeProperty(
        "final", __doc__="Indicates if class is final"
    )
    is_primitive = c.BooleanAttributeProperty(
        "isPrimitive", __doc__="Indicates if class is primitive"
    )
    visibility = c.EnumAttributeProperty(
        "visibility", modeltypes.VisibilityKind, default="UNSET"
    )
    state_machines = c.DirectProxyAccessor(
        capellacommon.StateMachine, aslist=c.ElementList
    )
    owned_properties = c.DirectProxyAccessor(Property, aslist=c.ElementList)

    @property
    def properties(self) -> c.ElementList[Property]:
        """Return all owned and inherited properties."""
        return (
            self.owned_properties + self.super.properties
            if self.super is not None
            else self.owned_properties
        )


@c.xtype_handler(None)
class InformationRealization(modellingcore.TraceableElement):
    """A realization for a Class."""

    _xmltag = "ownedInformationRealizations"


@c.xtype_handler(None)
class Union(Class):
    """A Union."""

    _xmltag = "ownedClasses"

    kind = c.EnumAttributeProperty(
        "kind", modeltypes.UnionKind, default="UNION"
    )


@c.xtype_handler(None)
class Collection(c.GenericElement):
    """A Collection."""

    _xmltag = "ownedCollections"

    kind = c.EnumAttributeProperty(
        "kind", modeltypes.CollectionKind, default="ARRAY"
    )

    sub: c.Accessor
    super: c.Accessor[Collection]


@c.xtype_handler(None)
class DataPkg(c.GenericElement):
    """A data package that can hold classes."""

    classes = c.DirectProxyAccessor(Class, aslist=c.ElementList)
    unions = c.DirectProxyAccessor(Union, aslist=c.ElementList)
    collections = c.DirectProxyAccessor(Collection, aslist=c.ElementList)
    enumerations = c.DirectProxyAccessor(
        datatype.Enumeration, aslist=c.ElementList
    )
    complex_values = c.DirectProxyAccessor(
        datavalue.ComplexValue, aslist=c.ElementList
    )
    packages: c.Accessor


@c.xtype_handler(None)
class ExchangeItemElement(c.GenericElement):
    """An ExchangeItemElement (proxy link)."""

    _xmltag = "ownedElements"

    abstract_type = c.AttrProxyAccessor(c.GenericElement, "abstractType")
    owner: c.Accessor

    min_card = c.RoleTagAccessor("ownedMinCard")
    max_card = c.RoleTagAccessor("ownedMaxCard")


@c.xtype_handler(None)
class ExchangeItem(c.GenericElement):
    """An item that can be exchanged on an Exchange."""

    _xmltag = "ownedExchangeItems"

    type = c.EnumAttributeProperty(
        "exchangeMechanism", modeltypes.ExchangeItemType, default="UNSET"
    )
    elements = c.DirectProxyAccessor(ExchangeItemElement, aslist=c.ElementList)
    exchanges: c.Accessor[c.GenericElement]


for cls in [Class, Union, datatype.Enumeration, Collection]:
    c.set_accessor(
        cls,
        "super",
        c.LinkAccessor(
            "ownedGeneralizations", capellacore.Generalization, attr="super"
        ),
    )
    c.set_accessor(
        cls,
        "sub",
        c.ReferenceSearchingAccessor(cls, "super", aslist=c.MixedElementList),
    )

c.set_accessor(
    datavalue.EnumerationLiteral,
    "owner",
    c.ParentAccessor(datatype.Enumeration),
)
c.set_accessor(
    DataPkg, "packages", c.DirectProxyAccessor(DataPkg, aslist=c.ElementList)
)
c.set_accessor(ExchangeItemElement, "owner", c.ParentAccessor(ExchangeItem))
c.set_accessor(
    Association,
    "members",
    c.DirectProxyAccessor(Property, aslist=c.ElementList),
)
c.set_accessor(
    Association,
    "navigable_members",
    c.AttrProxyAccessor(Property, "navigableMembers", aslist=c.ElementList),
)
c.set_accessor(Association, "source_role", c.DirectProxyAccessor(Property))
c.set_accessor(
    Class,
    "realized_classes",
    c.LinkAccessor[Class](
        "ownedInformationRealizations",
        InformationRealization,
        aslist=c.ElementList,
        attr="targetElement",
    ),
)
c.set_accessor(
    Class,
    "realizations",
    c.DirectProxyAccessor(InformationRealization, aslist=c.ElementList),
)
c.set_accessor(
    Class,
    "realized_by",
    c.ReferenceSearchingAccessor(
        Class, "realized_classes", aslist=c.ElementList
    ),
)
