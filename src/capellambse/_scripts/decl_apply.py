# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

import typing as t

import click

import capellambse
from capellambse import decl


@click.command()
@click.option("-m", "--model", type=capellambse.ModelCLI(), required=True)
@click.option("-s", "--strict/--relaxed", is_flag=True, default=False)
@click.argument("file", type=click.File("r"))
def main(
    model: capellambse.MelodyModel,
    file: t.IO[str],
    strict: bool,
) -> None:
    """Apply a declarative modelling YAML file to a model."""
    decl.apply(model, file, strict=strict)
    model.save()
