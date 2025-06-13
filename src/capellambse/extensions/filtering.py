# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Implements the Capella Filtering extension."""

from __future__ import annotations

import collections.abc as cabc
import contextlib
import logging
import operator
import pathlib
import shutil
import sys
import typing as t

import typing_extensions as te

import capellambse
import capellambse.model as m
from capellambse import _native, helpers
from capellambse.metamodel import capellacore, capellamodeller

_LOGGER = logging.getLogger(__name__)

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
        (), "filtering_criteria", aslist=m.MixedElementList
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


class AssociatedCriteriaAccessor(m.PhysicalAccessor[FilteringCriterion]):
    def __init__(self) -> None:
        super().__init__(FilteringCriterion, aslist=m.ElementList)

    @t.overload
    def __get__(self, obj: None, objtype: type[t.Any]) -> te.Self: ...
    @t.overload
    def __get__(
        self, obj: m.ModelObject, objtype: type[t.Any] | None = ...
    ) -> m.ElementList[m.T]: ...
    def __get__(
        self,
        obj: m.ModelObject | None,
        objtype: type[t.Any] | None = None,
    ) -> te.Self | m.ElementList[m.T]:
        del objtype
        if obj is None:  # pragma: no cover
            return self

        loader = obj._model._loader
        try:
            xt_critset = f"{NS.alias}:AssociatedFilteringCriterionSet"
            critset = next(loader.iterchildren_xt(obj._element, xt_critset))
        except StopIteration:
            elems = []
        else:
            links = critset.get("filteringCriteria", "")
            elems = list(loader.follow_links(obj._element, links))

        return self._make_list(obj, elems)


def init() -> None:
    capellamodeller.SystemEngineering.filtering_model = m.DirectProxyAccessor(
        FilteringModel
    )
    m.MelodyModel.filtering_model = property(  # type: ignore[attr-defined]
        operator.attrgetter("project.model_root.filtering_model")
    )
    m.ModelElement.filtering_criteria = AssociatedCriteriaAccessor()


try:
    import click

    from capellambse import cli_helpers
except ImportError:

    def _main() -> None:
        """Display a dependency error."""
        print("Missing dependency 'capellambse[cli]'", file=sys.stderr)
        raise SystemExit(1)

else:

    @click.command()
    @click.argument("command")
    @click.option(
        "-m",
        "--model",
        "model_",
        type=cli_helpers.ModelCLI(),
        required=True,
        help="Source Capella model to derive from",
    )
    @click.option(
        "-r",
        "--result",
        "result_strings",
        multiple=True,
        help="A filtering result object, specified either by UUID or name.",
    )
    @click.option(
        "-o",
        "--output",
        type=click.Path(
            file_okay=False, dir_okay=True, path_type=pathlib.Path
        ),
        default=".",
        help="Directory to store the derived project(s) in.",
    )
    @click.option(
        "-p",
        "--name-pattern",
        default="{model.name}_derived_{result.name}",
        help=(
            "The 'str.format()' pattern for generating output project names."
            " Available format arguments are 'model' and the current 'result'."
        ),
    )
    @click.option("--exe", help="Name or path of the Capella executable")
    @click.option("--docker", help="Name of a Docker image containing Capella")
    def _main(
        command: str,
        model_: capellambse.MelodyModel,
        result_strings: list[str],
        output: pathlib.Path,
        name_pattern: str,
        exe: str | None,
        docker: str | None,
    ) -> None:
        """Manage filtered Capella projects.

        Currently the only supported COMMAND is "derive", which performs
        project derivation based on an existing filtering result.

        The native Capella installation (options ``--exe`` or
        ``--docker``) may contain the placeholder '{VERSION}', which
        will be replaced by the Capella version number that the model
        was created with (e.g. "6.0.0").

        Exactly one of ``--exe`` or ``--docker`` must be specified.
        """
        if command != "derive":
            click.echo(f"Unsupported command: {command}", err=True)
            raise SystemExit(1)

        results = _find_results(model_, result_strings)
        output.mkdir(exist_ok=True, parents=True)
        with (
            _native.native_capella(model_, exe=exe, docker=docker) as cli,
            click.progressbar(
                results, item_show_func=lambda i: getattr(i, "name", "")
            ) as progress,
        ):
            for result in progress:
                derived_name = name_pattern.format(model=model_, result=result)
                output_sub = output / derived_name
                with contextlib.suppress(FileNotFoundError):
                    shutil.rmtree(output_sub)
                proc = cli(
                    *_native.ARGS_CMDLINE,
                    "-appid",
                    "org.polarsys.capella.filtering.commandline",
                    "-input",
                    "main_model",
                    "-filteringresultid",
                    result.uuid,
                    "-derivationprojectname",
                    derived_name,
                )
                derived = cli.workspace / derived_name
                if not derived.exists():
                    _LOGGER.error(
                        "Failed to derive result %r (%s)\n\n%s",
                        result.name,
                        result.uuid,
                        proc.stdout,
                    )
                    raise RuntimeError(
                        "Output directory does not exist for derived result"
                        f" {result.name!r} ({result.uuid})"
                    )
                shutil.copytree(derived, output_sub)

    def _find_results(
        loaded_model: capellambse.MelodyModel, result_strings: list[str]
    ) -> cabc.Sequence[AbstractFilteringResult]:
        all_results: m.ElementList[AbstractFilteringResult]
        all_results = loaded_model.search(AbstractFilteringResult)
        if not result_strings:
            return all_results

        wanted: list[AbstractFilteringResult] = []
        obj: m.ModelElement
        for result in result_strings:
            if helpers.is_uuid_string(result):
                try:
                    obj = loaded_model.by_uuid(result)
                except KeyError:
                    pass
                else:
                    if not isinstance(obj, AbstractFilteringResult):
                        click.echo(
                            f"Error: Object {obj._short_repr_()} is of type"
                            f" {type(obj).__name__}, expected"
                            f" an AbstractFilteringResult",
                            err=True,
                        )
                        raise SystemExit(1)
                    wanted.append(obj)
                    continue

            obj = all_results.by_name(result, single=True)
            assert isinstance(obj, AbstractFilteringResult)
            wanted.append(obj)
        return wanted


if __name__ == "__main__":
    _main()
