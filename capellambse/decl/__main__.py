# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
"""CLI for applying a declarative modelling YAML file to a model."""
import sys
import typing as t

import capellambse
from capellambse.decl import _decl

try:
    import click
except ImportError:

    def _main() -> None:
        """Display a dependency error."""
        print("Error: Please install 'click' and retry", file=sys.stderr)
        raise SystemExit(1)

else:

    @click.command()
    @click.option("-m", "--model", type=capellambse.ModelCLI(), required=True)
    @click.argument("file", type=click.File("r"))
    def _main(model: capellambse.MelodyModel, file: t.IO[str]) -> None:
        """Apply a declarative modelling YAML file to a model."""
        _decl.apply(model, file)
        model.save()


if __name__ == "__main__":
    _main()
