# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

import click

import capellambse
from capellambse import cli_helpers


@click.command()
def main() -> None:
    """Show information about known models."""
    print("User-defined 'known models' are searched in:")
    print()
    print(f"   {capellambse.dirs.user_config_path / 'known_models'}")
    print()
    print("The following models are currently known:")
    for file in cli_helpers.enumerate_known_models():
        name, _, _ = file.name.rpartition(".")
        print(f"  - {name}")
