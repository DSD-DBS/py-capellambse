# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

import collections.abc as cabc
import contextlib
import logging
import pathlib
import shutil

import click

import capellambse
import capellambse.model as m
from capellambse import _native, cli_helpers, helpers
from capellambse.extensions import filtering

_LOGGER = logging.getLogger(__name__)


@click.command()
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
    type=click.Path(file_okay=False, dir_okay=True, path_type=pathlib.Path),
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
def main(
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

    The native Capella installation (options ``--exe`` or ``--docker``)
    may contain the placeholder '{VERSION}', which will be replaced by
    the Capella version number that the model was created with (e.g.
    "6.0.0"). If you have docker installed, a good default value is:

    \b
    --docker ghcr.io/dbinfrago/capella-dockerimages/capella/base:{VERSION}-selected-dropins-main

    Exactly one of ``--exe`` or ``--docker`` must be specified.
    """  # noqa: D301
    if exe and docker:
        raise click.UsageError("--exe and --docker are mutually exclusive")
    if not exe and not docker:
        raise click.UsageError("Exactly one of --exe or --docker is required")

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
) -> cabc.Sequence[filtering.AbstractFilteringResult]:
    all_results: m.ElementList[filtering.AbstractFilteringResult]
    all_results = loaded_model.search(filtering.AbstractFilteringResult)
    if not result_strings:
        return all_results

    wanted: list[filtering.AbstractFilteringResult] = []
    obj: m.ModelElement
    for result in result_strings:
        if helpers.is_uuid_string(result):
            try:
                obj = loaded_model.by_uuid(result)
            except KeyError:
                pass
            else:
                if not isinstance(obj, filtering.AbstractFilteringResult):
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
        assert isinstance(obj, filtering.AbstractFilteringResult)
        wanted.append(obj)
    return wanted
