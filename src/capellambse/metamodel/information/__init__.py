# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Objects and relations for information capture and data modelling.

Information objects inheritance tree (taxonomy):

.. diagram:: [CDB] Information [Taxonomy]

Information object-relations map (ontology):

.. diagram:: [CDB] Information [Ontology]
"""

from __future__ import annotations

import capellambse.model as m

from .. import capellacommon, capellacore, modellingcore, modeltypes
from . import datatype, datavalue


@m.xtype_handler(None)
class Unit(m.ModelElement):
    """Unit."""

    _xmltag = "ownedUnits"


@m.xtype_handler(None)
class Association(m.ModelElement):
    """An Association."""

    _xmltag = "ownedAssociations"

    members: m.Accessor[Property]
    navigable_members: m.Accessor[Property]

    @property
    def roles(self) -> m.ElementList[Property]:
        assert isinstance(self.members, m.ElementList)
        assert isinstance(self.navigable_members, m.ElementList)
        roles = [i._element for i in self.members + self.navigable_members]
        return m.ElementList(self._model, roles, Property)


@m.xtype_handler(None)
class PortAllocation(modellingcore.TraceableElement):
    """An exchange between a ComponentPort and FunctionalPort."""

    _xmltag = "ownedPortAllocations"


@m.xtype_handler(None)
class Property(m.ModelElement):
    """A Property of a Class."""

    _xmltag = "ownedFeatures"

    is_ordered = m.BoolPOD("ordered")
    """Indicates if property is ordered."""
    is_unique = m.BoolPOD("unique")
    """Indicates if property is unique."""
    is_abstract = m.BoolPOD("isAbstract")
    """Indicates if property is abstract."""
    is_static = m.BoolPOD("isStatic")
    """Indicates if property is static."""
    is_part_of_key = m.BoolPOD("isPartOfKey")
    """Indicates if property is part of key."""
    is_derived = m.BoolPOD("isDerived")
    """Indicates if property is abstract."""
    is_read_only = m.BoolPOD("isReadOnly")
    """Indicates if property is read-only."""
    visibility = m.EnumPOD(
        "visibility", modeltypes.VisibilityKind, default="UNSET"
    )
    kind = m.EnumPOD(
        "aggregationKind", modeltypes.AggregationKind, default="UNSET"
    )
    type = m.Association(m.ModelElement, "abstractType")
    default_value = m.Containment("ownedDefaultValue")
    min_value = m.Containment("ownedMinValue")
    max_value = m.Containment("ownedMaxValue")
    null_value = m.Containment("ownedNullValue")
    min_card = m.Containment("ownedMinCard")
    max_card = m.Containment("ownedMaxCard")
    association = m.Backref(Association, "roles")


@m.xtype_handler(None)
class Class(m.ModelElement):
    """A Class."""

    _xmltag = "ownedClasses"

    sub: m.Accessor
    super: m.Accessor[Class]
    is_abstract = m.BoolPOD("abstract")
    """Indicates if class is abstract."""
    is_final = m.BoolPOD("final")
    """Indicates if class is final."""
    is_primitive = m.BoolPOD("isPrimitive")
    """Indicates if class is primitive."""
    visibility = m.EnumPOD(
        "visibility", modeltypes.VisibilityKind, default="UNSET"
    )
    state_machines = m.DirectProxyAccessor(
        capellacommon.StateMachine, aslist=m.ElementList
    )
    owned_properties = m.DirectProxyAccessor(Property, aslist=m.ElementList)
    generalizations = m.DirectProxyAccessor(
        capellacore.Generalization, aslist=m.ElementList
    )

    @property
    def properties(self) -> m.ElementList[Property]:
        """Return all owned and inherited properties."""
        return (
            self.owned_properties + self.super.properties
            if self.super is not None
            else self.owned_properties
        )


@m.xtype_handler(None)
class InformationRealization(modellingcore.TraceableElement):
    """A realization for a Class."""

    _xmltag = "ownedInformationRealizations"


@m.xtype_handler(None)
class Union(Class):
    """A Union."""

    _xmltag = "ownedClasses"

    kind = m.EnumPOD("kind", modeltypes.UnionKind, default="UNION")


@m.xtype_handler(None)
class Collection(m.ModelElement):
    """A Collection."""

    _xmltag = "ownedCollections"

    kind = m.EnumPOD("kind", modeltypes.CollectionKind, default="ARRAY")

    sub: m.Accessor
    super: m.Accessor[Collection]


@m.xtype_handler(None)
class DataPkg(m.ModelElement):
    """A data package that can hold classes."""

    _xmltag = "ownedDataPkgs"

    owned_associations = m.DirectProxyAccessor(
        Association, aslist=m.ElementList
    )
    classes = m.DirectProxyAccessor(Class, aslist=m.ElementList)
    unions = m.DirectProxyAccessor(Union, aslist=m.ElementList)
    collections = m.DirectProxyAccessor(Collection, aslist=m.ElementList)
    enumerations = m.DirectProxyAccessor(
        datatype.Enumeration, aslist=m.ElementList
    )
    datatypes = m.DirectProxyAccessor(
        m.ModelElement,
        (
            datatype.BooleanType,
            datatype.Enumeration,
            datatype.StringType,
            datatype.NumericType,
            datatype.PhysicalQuantity,
        ),
        aslist=m.MixedElementList,
    )
    complex_values = m.DirectProxyAccessor(
        datavalue.ComplexValue, aslist=m.ElementList
    )
    packages: m.Accessor


@m.xtype_handler(None)
class ExchangeItemElement(m.ModelElement):
    """An ExchangeItemElement (proxy link)."""

    _xmltag = "ownedElements"

    abstract_type = m.Association(m.ModelElement, "abstractType")
    owner = m.ParentAccessor["ExchangeItem"]()

    min_card = m.Containment("ownedMinCard")
    max_card = m.Containment("ownedMaxCard")


@m.xtype_handler(None)
class ExchangeItem(m.ModelElement):
    """An item that can be exchanged on an Exchange."""

    _xmltag = "ownedExchangeItems"

    type = m.EnumPOD(
        "exchangeMechanism", modeltypes.ExchangeMechanism, default="UNSET"
    )
    elements = m.DirectProxyAccessor(ExchangeItemElement, aslist=m.ElementList)
    exchanges: m.Accessor[m.ModelElement]
    instances: m.Containment


@m.xtype_handler(None)
class ExchangeItemInstance(Property):
    pass


m.set_accessor(
    capellacore.Generalization, "super", m.Association(None, "super")
)
for cls in [Class, Union, datatype.Enumeration, Collection]:
    m.set_accessor(
        cls,
        "super",
        m.Allocation(
            "ownedGeneralizations",
            capellacore.Generalization,
            attr="super",
            backattr="sub",
        ),
    )
    m.set_accessor(
        cls,
        "sub",
        m.Backref(cls, "super", aslist=m.MixedElementList),
    )

m.set_accessor(
    DataPkg, "packages", m.DirectProxyAccessor(DataPkg, aslist=m.ElementList)
)
m.set_accessor(
    Association,
    "members",
    m.Containment("ownedMembers", aslist=m.ElementList),
)
m.set_accessor(
    Association,
    "navigable_members",
    m.Association(Property, "navigableMembers", aslist=m.ElementList),
)
m.set_accessor(
    Class,
    "realized_classes",
    m.Allocation[Class](
        "ownedInformationRealizations",
        InformationRealization,
        aslist=m.ElementList,
        attr="targetElement",
    ),
)
m.set_accessor(
    Class,
    "realizations",
    m.DirectProxyAccessor(InformationRealization, aslist=m.ElementList),
)
m.set_accessor(
    Class,
    "realized_by",
    m.Backref(Class, "realized_classes", aslist=m.ElementList),
)
m.set_accessor(
    ExchangeItem,
    "instances",
    m.Containment(
        "ownedExchangeItemInstances",
        ExchangeItemInstance,
        aslist=m.ElementList,
    ),
)
