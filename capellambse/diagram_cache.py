# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
"""CLI for the diagram cache updating feature."""
from __future__ import annotations

import pathlib
import sys

import capellambse
from capellambse import _diagram_cache, cli_helpers

# pylint: disable=unused-import
from capellambse._diagram_cache import IndexEntry

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
        "model_",
        type=cli_helpers.ModelCLI(),
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
    )
    @click.option(
        "-f",
        "--format",
        type=click.Choice(sorted(_diagram_cache.VALID_FORMATS)),
        default="svg",
        help="Image output format",
        show_default=True,
    )
    @click.option(
        "--index/--no-index",
        default=True,
        help="Generate index.json and index.html files",
        show_default=True,
    )
    @click.option("--exe", help="Name or path of the Capella executable")
    @click.option("--docker", help="Name of a Docker image containing Capella")
    @click.option(
        "--background/--no-background",
        help="Inserts a white background into the diagrams.",
        default=True,
        show_default=True,
    )
    def _main(
        model_: capellambse.MelodyModel,
        output: pathlib.Path,
        format: str,
        index: bool,
        exe: str | None,
        docker: str | None,
        background: bool,
    ) -> None:
        model_._diagram_cache = capellambse.get_filehandler(output)
        model_._diagram_cache_subdir = pathlib.PurePosixPath(".")

        if docker:
            _diagram_cache.export(
                docker,
                model_,
                format=format,
                index=index,
                force="docker",
                background=background,
            )
        else:
            exe = exe or "capella{VERSION}"
            _diagram_cache.export(
                exe,
                model_,
                format=format,
                index=index,
                force="exe",
                background=background,
            )


if __name__ == "__main__":
    _main()
