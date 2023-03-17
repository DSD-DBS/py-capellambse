# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
"""Implements the Capella Filtering extension."""
from __future__ import annotations

import abc
import sys
import typing as t

import typing_extensions as te

import capellambse.model.common as c
from capellambse import model

VIEWPOINT: t.Final = "org.polarsys.capella.filtering"
NAMESPACE: t.Final = "http://www.polarsys.org/capella/filtering/6.0.0"
SYMBOLIC_NAME: t.Final = "filtering"

c.XTYPE_ANCHORS[__name__] = SYMBOLIC_NAME


@c.xtype_handler(None)
class FilteringCriterion(c.GenericElement):
    """A single filtering criterion."""

    _xmltag = "ownedFilteringCriteria"

    filtered_objects = c.ReferenceSearchingAccessor[c.GenericElement](
        (), "filtering_criteria", aslist=c.MixedElementList
    )


@c.xtype_handler(None)
class FilteringCriterionPkg(c.GenericElement):
    """A package containing multiple filtering criteria."""

    _xmltag = "ownedFilteringCriterionPkgs"

    criteria = c.DirectProxyAccessor(FilteringCriterion, aslist=c.ElementList)
    packages: c.Accessor[FilteringCriterionPkg]


@c.xtype_handler(None)
class FilteringModel(c.GenericElement):
    """A filtering model containing criteria to filter by."""

    criteria = c.DirectProxyAccessor(FilteringCriterion, aslist=c.ElementList)
    criterion_packages = c.DirectProxyAccessor(
        FilteringCriterionPkg, aslist=c.ElementList
    )


class AbstractFilteringResult(c.GenericElement, metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def filtered_objects(self) -> c.MixedElementList:
        ...


class FilteringResult(AbstractFilteringResult):
    """A simple filtering result."""


class AbstractResultSet(c.GenericElement):
    results = c.AttrProxyAccessor(
        FilteringResult, "filteringResults", aslist=c.ElementList
    )


@c.xtype_handler(None)
class UnionFilteringResultSet(AbstractResultSet):
    """Combines results with the union operation."""


@c.xtype_handler(None)
class IntersectionFilteringResultSet(AbstractResultSet):
    """Combines results with the intersection operation."""


@c.xtype_handler(None)
class ExclusionFilteringResultSet(AbstractResultSet):
    """Combines results with the exclusion operation."""


class ComposedFilteringResult(AbstractFilteringResult):
    """A result obtained from boolean operations of other results."""

    union = c.DirectProxyAccessor(UnionFilteringResultSet)
    intersection = c.DirectProxyAccessor(IntersectionFilteringResultSet)
    exclusion = c.DirectProxyAccessor(ExclusionFilteringResultSet)

    @property
    def filtered_objects(self) -> c.MixedElementList:
        ids = set[str]()

        for result in self.union.results:
            ids |= {i.uuid for i in result}

        for result in self.intersection.results:
            ids &= {i.uuid for i in result}

        for result in self.exclusion.results:
            ids -= {i.uuid for i in result}

        return c.MixedElementList(
            self._model,
            [self._model._loader[i] for i in ids],
        )


@c.xtype_handler(None)
class FilteringResults(c.GenericElement):
    """Container for the filtering result sets."""

    results = c.DirectProxyAccessor[AbstractFilteringResult](
        c.GenericElement,  # type: ignore[arg-type]
        (FilteringResult, ComposedFilteringResult),
        aslist=c.MixedElementList,
    )


class AssociatedCriteriaAccessor(
    c.accessors.PhysicalAccessor[FilteringCriterion]
):
    def __init__(self) -> None:
        super().__init__(FilteringCriterion, aslist=c.ElementList)

    @t.overload
    def __get__(self, obj: None, objtype: type[t.Any]) -> te.Self:
        ...

    @t.overload
    def __get__(
        self, obj: c.ModelObject, objtype: type[t.Any] | None = ...
    ) -> c.ElementList[c.T]:
        ...

    def __get__(
        self,
        obj: c.ModelObject | None,
        objtype: type[t.Any] | None = None,
    ) -> te.Self | c.ElementList[c.T]:
        del objtype
        if obj is None:  # pragma: no cover
            return self

        loader = obj._model._loader
        try:
            xt_critset = f"{SYMBOLIC_NAME}:AssociatedFilteringCriterionSet"
            critset = next(loader.iterchildren_xt(obj._element, xt_critset))
        except StopIteration:
            elems = []
        else:
            links = critset.get("filteringCriteria", "")
            elems = list(loader.follow_links(obj._element, links))

        rv = self._make_list(obj, elems)
        if obj._constructed:
            sys.audit("capellambse.read_attribute", obj, self.__name__, rv)
            sys.audit("capellambse.getattr", obj, self.__name__, rv)
        return rv


def init() -> None:
    c.set_accessor(
        model.MelodyModel,
        "filtering_model",
        c.DirectProxyAccessor(FilteringModel, rootelem=model.XT_SYSENG),
    )
    c.set_accessor(
        model.MelodyModel,
        "filtering_results",
        c.DirectProxyAccessor(FilteringResults, rootelem=model.XT_SYSENG),
    )
    c.set_accessor(
        c.GenericElement, "filtering_criteria", AssociatedCriteriaAccessor()
    )


c.set_self_references(
    (FilteringCriterionPkg, "packages"),
)
