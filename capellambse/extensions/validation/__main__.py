# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import logging
import typing as t

import click
import jinja2

import capellambse


@click.command()
@click.option("-m", "--model", required=True, type=capellambse.ModelCLI())
@click.option(
    "-o",
    "--output",
    type=click.File("w", atomic=True),
    required=True,
    help="Output file to render the template into",
)
@click.option("-t", "--template", help="An optional custom template to render")
def _main(
    model: capellambse.MelodyModel,
    template: str | None,
    output: t.IO[str],
) -> None:
    logging.basicConfig()

    loader: jinja2.BaseLoader
    if template is None:
        loader = jinja2.PackageLoader("capellambse", "extensions/validation")
        template = "report-template.html.jinja"
    else:
        loader = jinja2.FileSystemLoader(".")
    env = jinja2.Environment(loader=loader)

    with output:
        env.get_template(template).stream(
            model=model,
            results=model.validation.validate(),
        ).dump(output)


if __name__ == "__main__":
    _main()
