# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Implements the Capella Filtering extension."""

from __future__ import annotations

import operator
import subprocess
import sys
import typing as t
import warnings

import capellambse.model as m
from capellambse.metamodel import capellacore, capellamodeller

NS = m.Namespace(
    "http://www.polarsys.org/capella/filtering/{VERSION}",
    "filtering",
    "org.polarsys.capella.filtering",
    "7.0.0",
)

VIEWPOINT: t.Final = NS.viewpoint
NAMESPACE: t.Final = NS.uri.format(VERSION="6.0.0")
SYMBOLIC_NAME: t.Final = NS.alias


class FilteringModel(capellacore.NamedElement):
    criteria = m.Containment["FilteringCriterion"](
        "ownedFilteringCriteria", (NS, "FilteringCriterion")
    )
    criterion_pkgs = m.Containment["FilteringCriterionPkg"](
        "ownedFilteringCriterionPkgs", (NS, "FilteringCriterionPkg")
    )
    variability_features = m.Containment["FilteringCriterion"](
        "ownedVariabilityFeatures", (NS, "FilteringCriterion")
    )

    if not t.TYPE_CHECKING:
        criterion_packages = m.DeprecatedAccessor("criterion_pkgs")


class FilteringCriterion(capellacore.NamedElement):
    _xmltag = "ownedFilteringCriteria"

    filtered_objects = m.Backref[m.ModelElement](
        (), "filtering_criteria", legacy_by_type=True
    )


class FilteringCriterionSet(capellacore.NamedElement, abstract=True):
    criteria = m.Association["FilteringCriterion"](
        (NS, "FilteringCriterion"), "filteringCriteria"
    )
    variability_features = m.Association["FilteringCriterion"](
        (NS, "FilteringCriterion"), "variabilityFeatures"
    )


class FilteringResults(capellacore.NamedElement):
    results = m.Containment["AbstractFilteringResult"](
        "filteringResults", (NS, "AbstractFilteringResult")
    )
    result_pkgs = m.Containment["FilteringResultPkg"](
        "ownedFilteringResultPkgs", (NS, "FilteringResultPkg")
    )
    configurations = m.Containment["FilteringResult"](
        "configurations", (NS, "FilteringResult")
    )


class AbstractFilteringResult(capellacore.NamedElement, abstract=True):
    pass


class FilteringResult(FilteringCriterionSet, AbstractFilteringResult):
    """A filtering result."""


class AssociatedFilteringCriterionSet(FilteringCriterionSet):
    pass


class CreationDefaultFilteringCriterionSet(FilteringCriterionSet):
    pass


class FilteringResultPkg(capellacore.Namespace):
    results = m.Containment["AbstractFilteringResult"](
        "ownedFilteringResults", (NS, "AbstractFilteringResult")
    )
    packages = m.Containment["FilteringResultPkg"](
        "ownedFilteringResultPkgs", (NS, "FilteringResultPkg")
    )
    result_pkgs = m.Alias["m.ElementList[FilteringResultPkg]"]("packages")


class FilteringCriterionPkg(capellacore.Namespace):
    """A package containing multiple filtering criteria."""

    _xmltag = "ownedFilteringCriterionPkgs"

    criteria = m.Containment["FilteringCriterion"](
        "ownedFilteringCriteria", (NS, "FilteringCriterion")
    )
    packages = m.Containment["FilteringCriterionPkg"](
        "ownedFilteringCriterionPkgs", (NS, "FilteringCriterionPkg")
    )


class ComposedFilteringResult(AbstractFilteringResult):
    """A result obtained from boolean operations of other results."""

    union = m.Containment["UnionFilteringResultSet"](
        "UnionFilteringResultSet", (NS, "UnionFilteringResultSet")
    )
    intersection = m.Containment["IntersectionFilteringResultSet"](
        "IntersectionFilteringResultSet",
        (NS, "IntersectionFilteringResultSet"),
    )
    exclusion = m.Containment["ExclusionFilteringResultSet"](
        "ExclusionFilteringResultSet", (NS, "ExclusionFilteringResultSet")
    )


class FilteringResultSet(capellacore.NamedElement):
    results = m.Association["AbstractFilteringResult"](
        (NS, "AbstractFilteringResult"), "filteringResults"
    )


class UnionFilteringResultSet(FilteringResultSet):
    pass


class ExclusionFilteringResultSet(FilteringResultSet):
    pass


class IntersectionFilteringResultSet(FilteringResultSet):
    pass


def init() -> None:
    capellamodeller.SystemEngineering.filtering_model = m.Single(
        m.Filter("extensions", (NS, "FilteringModel"))
    )
    m.MelodyModel.filtering_model = property(  # type: ignore[attr-defined]
        operator.attrgetter("project.model_root.filtering_model")
    )
    m.ModelElement.filtering_criteria = property(
        lambda obj: obj.extensions.by_class(
            AssociatedFilteringCriterionSet
        ).map("criteria")
    )


def _main() -> None:
    if len(sys.argv) < 2:
        args = ["--help"]
    elif sys.argv[1] != "derive":
        print(f"Unsupported command: {sys.argv[1]}", file=sys.stderr)
        raise SystemExit(1)
    else:
        args = sys.argv[2:]

    warnings.warn(
        "This CLI entry point is deprecated, use 'capellambse filter-derive' instead",
        FutureWarning,
        stacklevel=2,
    )

    cmd = [sys.executable, "-mcapellambse", "filter-derive", *args]
    raise SystemExit(subprocess.run(cmd, check=False).returncode)


if __name__ == "__main__":
    _main()
