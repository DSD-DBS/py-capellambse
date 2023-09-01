# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
"""Helpers for working with models in CLI scripts."""
from __future__ import annotations

__all__ = ["ModelCLI", "enumerate_known_models", "loadcli", "loadinfo"]

import collections.abc as cabc
import importlib.abc
import importlib.resources as imr
import json
import logging
import os
import typing as t

import capellambse

LOGGER = logging.getLogger(__name__)

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

    class ModelInfoCLI(click.ParamType):
        """Declare an option that loads model information.

        This is similar to :class:`ModelCLI`, but it returns a
        dict with information on how to load the model, rather than
        the model itself. This is useful for commands that need to
        alter the way a model is loaded.

        Use instances of this class for the ``type=`` argument to
        ``@click.option`` etc.

        Examples
        --------
        .. code-block:: python

           @click.command()
           @click.open("-m", "modelinfo", type=capellambse.ModelInfoCLI())
           def main(modelinfo: dict[str, t.Any]) -> None:
               # change any options, for example:
               modelinfo["diagram_cache"] = "/tmp/diagrams"
               # load the model:
               model = capellambse.MelodyModel(**modelinfo)
               ...
        """

        name = "CAPELLA_MODEL"

        def convert(self, value: t.Any, param, ctx) -> dict[str, t.Any]:
            if isinstance(value, dict):
                return value

            try:
                return loadinfo(value)
            except ValueError as err:
                self.fail(err.args[0], param, ctx)
                assert False

except ImportError:
    if not t.TYPE_CHECKING:

        def ModelCLI(*__, **_):
            """Raise a dependency error."""
            raise RuntimeError("click is not installed")

        def ModelInfoCLI(*__, **_):
            """Raise a dependency error."""
            raise RuntimeError("click is not installed")


def enumerate_known_models() -> cabc.Iterator[importlib.abc.Traversable]:
    """Enumerate the models that are found in the ``known_models`` folders.

    Two places are searched for models: The *known_models* folder in the
    user's configuration directory, and the *known_models* folder in the
    installed ``capellambse`` package.

    In order to make a custom model known, place a JSON file in one of
    these *known_models* folders. It should contain a dictionary with
    the keyword arguments to :class:`capellambse.MelodyModel` -
    specifically it needs a ``path``, an ``entrypoint``, and any
    additional arguments that the underlying
    :class:`capellambse.filehandler.FileHandler` might need to gain
    access to the model.

    Files in the user's configuration directory take precedence over
    files in the package directory. If a file with the same name exists
    in both places, the one in the user's configuration directory will
    be used.

    Be aware that relative paths in the JSON will be interpreted
    relative to the current working directory.
    """
    names = set[str]()
    userdir = capellambse.dirs.user_config_path.joinpath("known_models")
    configdir = imr.files(capellambse).joinpath("known_models")
    i: importlib.abc.Traversable
    try:
        for i in userdir.iterdir():
            if i.name.endswith(".json") and i.is_file():
                names.add(i.name)
                yield i
    except FileNotFoundError:
        pass
    for i in configdir.iterdir():
        if i.name.endswith(".json") and i.is_file() and i.name not in names:
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
    modelinfo = loadinfo(value)
    LOGGER.info("Loading model from %s", modelinfo["path"])
    return capellambse.MelodyModel(**modelinfo)


def loadinfo(value: str | os.PathLike[str]) -> dict[str, t.Any]:
    if isinstance(value, str):
        if value.endswith((".aird", ".json")):
            return _load_from_file(value)
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return _load_from_file(value)

    if isinstance(value, os.PathLike):
        value = os.fspath(value)
        if isinstance(value, str):
            return _load_from_file(value)

    raise TypeError("value must be a str or PathLike returning str")


def _load_from_file(value: str) -> dict[str, t.Any]:
    if value.endswith(".aird"):
        return {"path": value}

    if value.endswith(".json"):
        with open(value, encoding="utf-8") as file:
            return json.load(file)

    name = value + ".json"
    for known in enumerate_known_models():
        if known.name == name:
            return json.loads(known.read_text(encoding="utf-8"))

    if os.path.exists(value):
        return {"path": value}

    raise ValueError(
        "value is not a known model nor contains valid JSON"
    ) from None
