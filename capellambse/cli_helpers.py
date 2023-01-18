# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Helpers for working with models in CLI scripts."""
from __future__ import annotations

__all__ = ["ModelCLI", "enumerate_known_models", "loadcli"]

import collections.abc as cabc
import importlib.abc
import importlib.resources as imr
import json
import os
import typing as t

import capellambse

try:
    import click

    class ModelCLI(click.ParamType):
        """Declare an option that loads a model.

        Use instances of this class for the ``type=`` argument to
        ``@click.option`` etc.

        Examples
        --------
        .. code-block:: python

           @click.command()
           @click.option("-m", "--model", type=capellambse.ModelCLI())
           def main(model: capellambse.MelodyModel) -> None:
               ...
        """

        name = "CAPELLA_MODEL"

        def convert(self, value: t.Any, param, ctx) -> capellambse.MelodyModel:
            if isinstance(value, capellambse.MelodyModel):
                return value

            try:
                return loadcli(value)
            except ValueError as err:
                self.fail(err.args[0], param, ctx)
                assert False

except ImportError:

    def ModelCLI(*__, **_):  # type: ignore[no-redef]
        """Raise a dependency error."""
        raise RuntimeError("click is not installed")


def enumerate_known_models() -> cabc.Iterator[importlib.abc.Traversable]:
    """Enumerate the models that are found in the ``known_models`` folder.

    In order to make a custom model known, place a JSON file in the
    ``known_models`` folder below the  installed ``capellambse`` package.
    It should contain a dictionary with the keyword arguments to
    :class:`capellambse.MelodyModel` - specifically it needs a ``path``,
    an ``entrypoint``, and any additional arguments that the underlying
    :class:`capellambse.filehandler.FileHandler` might need to gain
    access to the model.

    Be aware that relative paths in the JSON will be interpreted
    relative to the current working directory.
    """
    for i in imr.files(capellambse).joinpath("known_models").iterdir():
        if i.name.endswith(".json") and i.is_file():
            yield i


def loadcli(value: str | os.PathLike[str]) -> capellambse.MelodyModel:
    """Load a model from a file or JSON string.

    This function tries to load a model from the following inputs:

    - A str or PathLike pointing to an ``.aird`` file
    - A str or PathLike pointing to a ``.json`` file, which contains the
      arguments to instantiate a :class:`capellambse.MelodyModel`
    - The contents of such a JSON file (as string)

    See Also
    --------
    capellambse.cli_helpers.CLIModel :
        This function wrapped as a ``click.ParamType``
    """
    if isinstance(value, str):
        if value.endswith((".aird", ".json")):
            return _load_from_file(value)
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            return _load_from_file(value)
        return capellambse.MelodyModel(**data)

    if isinstance(value, os.PathLike):
        value = os.fspath(value)
        if isinstance(value, str):
            return _load_from_file(value)

    raise TypeError("value must be a str or PathLike returning str")


def _load_from_file(value: str) -> capellambse.MelodyModel:
    if value.endswith(".aird"):
        return capellambse.MelodyModel(value)

    if value.endswith(".json"):
        with open(value, encoding="utf-8") as file:
            data = json.load(file)
    else:
        value = value + ".json"
        for known in enumerate_known_models():
            if value == known.name:
                data = json.loads(known.read_text(encoding="utf-8"))
                break
        else:
            try:
                data = json.loads(value)
            except json.JSONDecodeError:
                raise ValueError(
                    "value is not a known model nor contains valid JSON"
                ) from None
    return capellambse.MelodyModel(**data)
