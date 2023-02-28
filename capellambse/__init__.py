# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""The capellambse package."""
import platformdirs

dirs = platformdirs.PlatformDirs("capellambse")
del platformdirs

from importlib import metadata

try:
    __version__ = metadata.version("capellambse")
except metadata.PackageNotFoundError:
    __version__ = "0.0.0+unknown"
del metadata

from ._namespaces import *
from .auditing import *
from .cli_helpers import *
from .filehandler import *
from .model import MelodyModel
from .model.common import ModelObject

_has_loaded_extensions = False


def load_model_extensions() -> None:
    """Load all model extensions.

    This function loads all entry points in the group
    ``capellambse.model_extensions`` and executes them.

    Note that this function must be placed at the end of the top-level
    ``__init__.py``, in order to ensure that all submodules were
    initialized before loading any extensions.
    """
    # pylint: disable=import-outside-toplevel  # Reduce namespace pollution
    import importlib.metadata as imm  # pylint: disable=reimported

    # pylint: disable=redefined-outer-name  # false-positive
    import logging
    import sys

    global _has_loaded_extensions
    if _has_loaded_extensions:
        return
    _has_loaded_extensions = True

    if sys.version_info < (3, 10):
        try:
            entrypoints = imm.entry_points()["capellambse.model_extensions"]
        except KeyError:
            return
    else:
        entrypoints = imm.entry_points(group="capellambse.model_extensions")

    for entrypoint in entrypoints:
        try:
            initfunc = entrypoint.load()
            initfunc()
        except Exception:
            logging.getLogger(__name__).exception(
                "Cannot load model extension %r from %r",
                entrypoint.name,
                entrypoint.value,
            )
