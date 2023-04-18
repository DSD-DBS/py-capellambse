# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import logging
import pathlib
import sys
import typing as t

import capellambse

from . import _validate

try:
    import click
    import jinja2
except ImportError:

    def _main() -> None:
        """Display a dependency error."""
        print(
            "Missing dependency 'capellambse[cli]' or 'jinja2'",
            file=sys.stderr,
        )
        raise SystemExit(1)

else:

    @click.command()
    @click.option("-m", "--model", required=True, type=capellambse.ModelCLI())
    @click.option(
        "-o",
        "--output",
        type=click.File("w"),
        required=True,
        help="Output file to render the template into.",
    )
    @click.option(
        "-t", "--template", help="An optional custom template to render."
    )
    def _main(
        model: capellambse.MelodyModel,
        template: str | None,
        output: t.IO[str],
    ) -> None:
        logging.basicConfig()

        loader: jinja2.BaseLoader
        if template is None:
            loader = jinja2.FileSystemLoader(pathlib.Path(__file__).parent)
            template = "default-template.html.jinja"
        else:
            loader = jinja2.FileSystemLoader(".")
        env = jinja2.Environment(loader=loader)

        tpl = env.get_template(template)

        rendered = tpl.render(
            model=model, get_passed_and_total=_validate.get_passed_and_total
        )
        with output:
            output.write(rendered)


if __name__ == "__main__":
    _main()
