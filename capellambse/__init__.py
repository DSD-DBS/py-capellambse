# SPDX-FileCopyrightText: Copyright DB InfraGO AG
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
from .cli_helpers import *
from .filehandler import *
from .model import MelodyModel as MelodyModel
from .model import ModelObject as ModelObject
from .model import NewObject as NewObject

_has_loaded_extensions = False


def load_model_extensions() -> None:
    """Load all model extensions.

    This function loads all entry points in the group
    ``capellambse.model_extensions`` and executes them.

    It is automatically called when loading a model. Calling it more
    than once has no effect, so it is safe (although not necessary) to
    explicitly call this function before loading a model.
    """
    # Reduce namespace pollution
    import importlib.metadata as imm
    import logging

    global _has_loaded_extensions
    if _has_loaded_extensions:
        return
    _has_loaded_extensions = True

    for entrypoint in imm.entry_points(group="capellambse.model_extensions"):
        try:
            initfunc = entrypoint.load()
            initfunc()
        except Exception:
            logging.getLogger(__name__).exception(
                "Cannot load model extension %r from %r",
                entrypoint.name,
                entrypoint.value,
            )
