# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""CLI for the diagram cache updating feature."""

from __future__ import annotations

import pathlib
import sys
import typing as t

import capellambse
from capellambse import _diagram_cache, cli_helpers
from capellambse._diagram_cache import IndexEntry as IndexEntry

try:
    import click
except ImportError:

    def _main() -> None:
        """Display a dependency error."""
        print("Missing dependency 'capellambse[cli]'", file=sys.stderr)
        raise SystemExit(1)

else:

    @click.command()
    @click.option(
        "-m",
        "--model",
        "modelinfo",
        type=cli_helpers.ModelInfoCLI(),
        required=True,
        help="Capella model to export diagrams from",
    )
    @click.option(
        "-o",
        "--output",
        type=click.Path(
            file_okay=False, dir_okay=True, path_type=pathlib.Path
        ),
        default="./diagrams",
        help="Directory to store the rendered diagrams in",
        show_default=True,
        envvar="DIAGRAM_CACHE_OUTPUT_DIR",
        show_envvar=True,
    )
    @click.option(
        "-f",
        "--format",
        type=click.Choice(sorted(_diagram_cache.VALID_FORMATS)),
        default="svg",
        help="Image output format",
        show_default=True,
        envvar="DIAGRAM_CACHE_OUTPUT_FORMAT",
        show_envvar=True,
    )
    @click.option(
        "--index/--no-index",
        default=True,
        help="Generate index.json and index.html files",
        show_default=True,
        envvar="DIAGRAM_CACHE_GENERATE_INDEX",
        show_envvar=True,
    )
    @click.option(
        "--refresh / --no-refresh",
        default=False,
        help=(
            "Refresh all diagrams before exporting them, to make sure their"
            " contents are up to date with the model. Recommended, but"
            " disabled by default because it may take a long time."
            " NOTE: This may temporarily open a Capella window (see above)."
        ),
        envvar="DIAGRAM_CACHE_REFRESH_DIAGRAMS",
        show_envvar=True,
    )
    @click.option("--exe", help="Name or path of the Capella executable")
    @click.option("--docker", help="Name of a Docker image containing Capella")
    @click.option(
        "--background/--no-background",
        help="Inserts a white background into the diagrams.",
        default=True,
        show_default=True,
        envvar="DIAGRAM_CACHE_INSERT_BACKGROUND",
        show_envvar=True,
    )
    def _main(
        modelinfo: dict[str, t.Any],
        output: pathlib.Path,
        format: str,
        index: bool,
        exe: str | None,
        docker: str | None,
        background: bool,
        refresh: bool,
    ) -> None:
        """Export diagrams from a Capella model.

        This tool can be used to easily populate a diagram cache for use
        with `capellambse.MelodyModel`.

        \b
        Refreshing representations
        --------------------------

        By default, Capella will only automatically refresh diagrams on
        an as-needed basis whenever a diagram is opened in the GUI. This
        can lead to out-of-date images being written by its
        "exportRepresentations" facility, which this tool uses.

        To avoid this problem, the '--refresh' switch can be used to
        automatically refresh all diagrams and make sure they are up to
        date with the model contents.

        Unfortunately, due to the way this refresh operation is
        implemented in Capella, this may cause a Capella window to be
        opened temporarily. It will automatically close once the
        operation is done.

        PLEASE DO NOT CLOSE THE WINDOW that Capella opens during this
        step, or the entire process will be aborted.

        Also be aware that using this option may lead to new objects
        being added in odd places, which may cause severe readability
        issues on the exported diagrams.

        Due to these issues, the automatic refresh is disabled by
        default.
        """  # noqa: D301
        modelinfo["diagram_cache"] = {"path": output}
        model_ = capellambse.MelodyModel(**modelinfo)

        if docker:
            capella = docker
            force = "docker"
        else:
            capella = exe or "capella{VERSION}"
            force = "exe"

        _diagram_cache.export(
            capella,
            model_,
            format=format,
            index=index,
            force=force,  # type: ignore
            background=background,
            refresh=refresh,
        )


if __name__ == "__main__":
    _main()
