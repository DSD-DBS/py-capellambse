# Copyright 2021 DB Netz AG
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""The python-capella-mbse package."""
import platformdirs

dirs = platformdirs.PlatformDirs("python-capella-mbse")
del platformdirs

from ._version import get_versions

__version__ = get_versions()["version"]
del get_versions


from ._namespaces import (
    NAMESPACES,
    check_plugin_version,
    yield_key_and_version_from_namespaces_by_plugin,
)
from .model import MelodyModel


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


load_model_extensions()
del load_model_extensions
