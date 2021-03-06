# Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""The Python capellambse package."""
import platformdirs


def migrate_cache_dir():
    """Migrate the cache directory from the old name to the new, shorter one.

    After some period of time to allow all active installations to
    migrate, this functionality should be removed again.

    Note that this function must be the first thing that happens in the
    top-level ``__init__.py``, so that submodules and external modules
    that use it will use the new name with migrated data.
    """
    # pylint: disable=import-outside-toplevel  # Reduce namespace pollution
    import pathlib
    import sys

    olddirs = platformdirs.PlatformDirs("python-capella-mbse")
    oldcachedir = pathlib.Path(olddirs.user_cache_dir)
    newcachedir = pathlib.Path(dirs.user_cache_dir)
    if not newcachedir.exists() and oldcachedir.exists():
        try:
            oldcachedir.rename(newcachedir)
        except OSError as err:
            print(
                f"Warning: Cannot migrate cache directory to {newcachedir}:",
                f"Exception occurred: {type(err).__name__}: {err}",
                f"Please delete the old directory manually: {oldcachedir}",
                file=sys.stderr,
                sep="\n",
            )


dirs = platformdirs.PlatformDirs("capellambse")
migrate_cache_dir()
del platformdirs, migrate_cache_dir

from ._version import get_versions

__version__ = get_versions()["version"]
del get_versions


from ._namespaces import (
    NAMESPACES,
    check_plugin_version,
    yield_key_and_version_from_namespaces_by_plugin,
)
from .auditing import AttributeAuditor
from .loader.filehandler import FileHandler, get_filehandler
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
    import importlib.metadata as imm
    import logging

    global _has_loaded_extensions
    if _has_loaded_extensions:
        return
    _has_loaded_extensions = True

    try:
        entrypoints = imm.entry_points()["capellambse.model_extensions"]
    except KeyError:
        return

    for entrypoint in entrypoints:
        try:
            initfunc = entrypoint.load()
            initfunc()
        except Exception:
            logging.getLogger(__name__).exception(
                "Cannot load model extension %r from %r",
                entrypoint,
                entrypoint.value,
            )
