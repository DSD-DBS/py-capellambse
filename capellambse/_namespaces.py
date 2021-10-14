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

from __future__ import annotations

import collections.abc as cabc
import dataclasses
import re
import typing as t

PLUGIN_PATTERN = re.compile(r"(.*?)(\d\.\d\.\d)?$")


@dataclasses.dataclass
class Version:
    """Capella xml-element/plugin version info about name and version."""

    plugin: str
    version: str | None = None

    @property
    def values(self) -> cabc.Iterator[str | None]:
        yield self.plugin
        yield self.version

    def __le__(self, other: float | int | str | Version) -> t.Any:
        if self.version is None:
            return False

        if isinstance(other, str):
            other = _tofloat(other)
        return other <= _tofloat(self.version)


def _tofloat(other: str) -> float:
    """Change 1.x.y...str into 1.x float."""
    version = other.split(".")
    if len(version) > 1:
        version = version[:2]

    return float(".".join(version))


def yield_key_and_version_from_namespaces_by_plugin(
    plugin: str,
) -> cabc.Iterator[tuple[str, Version]]:
    """Yield namespace key and :class:`Version` tuple for plugin str.

    Parameters
    ----------
    plugin
        ``xsi:type`` string of xml-element/plugin

    Yields
    ------
    tuple
        If plugin in namespace values yield key value and Version
    """
    match = PLUGIN_PATTERN.match(plugin)
    version = None
    if match is not None:
        plugin = match.group(1)
        if match.group(2) is not None:
            version = match.group(2)

    for k, v in NAMESPACES.get_items():
        if v.plugin == plugin:
            yield k, Version(plugin, version)


def check_plugin_version(plugin: str, version: Version) -> bool:
    """Check if the plugin with given version is supported."""
    if plugin not in NAMESPACES:
        return False

    if version.version is None:  # Versionless plugin
        return True

    return version <= NAMESPACES.get_version(plugin)


class Namespace(dict):
    """Namespace dictionary to hold xml-element namespace data and versions."""

    def __getitem__(self, key: str) -> str:
        version = super().__getitem__(key)
        return "".join(
            attr for attr in version.values if isinstance(attr, str)
        )

    def items(self) -> cabc.ItemsView[str, str]:
        """Get original dictionary itemsview."""
        return {k: self.__getitem__(k) for k in super().keys()}.items()

    def get_items(self) -> cabc.ItemsView[str, Version]:
        """Get dictionary itemsview of name and version."""
        return super().items()

    def get_version(self, key: str) -> Version:
        """Get original namespace value."""
        return super().__getitem__(key)


#: These XML namespaces are defined in every ``.aird`` document
NAMESPACES = Namespace(
    {
        "CapellaRequirements": Version(
            "http://www.polarsys.org/capella/requirements"
        ),
        "Requirements": Version(
            "http://www.polarsys.org/kitalpha/requirements"
        ),
        "concern": Version(
            "http://www.eclipse.org/sirius/diagram/description/concern/",
            "1.1.0",
        ),
        "description": Version(
            "http://www.eclipse.org/sirius/description/", "1.1.0"
        ),
        "description_1": Version(
            "http://www.eclipse.org/sirius/diagram/description/", "1.1.0"
        ),
        "description_2": Version(
            "http://www.eclipse.org/sirius/table/description/", "1.1.0"
        ),
        "description_3": Version(
            "http://www.eclipse.org/sirius/diagram/sequence/description/",
            "2.0.0",
        ),
        "diagram": Version("http://www.eclipse.org/sirius/diagram/", "1.1.0"),
        "diagramstyler": Version("http://thalesgroup.com/mde/melody/ordering"),
        "ecore": Version("http://www.eclipse.org/emf/2002/Ecore"),
        "filter": Version(
            "http://www.eclipse.org/sirius/diagram/description/filter/",
            "1.1.0",
        ),
        "libraries": Version(
            "http://www.polarsys.org/capella/common/libraries/", "5.0.0"
        ),
        "metadata": Version(
            "http://www.polarsys.org/kitalpha/ad/metadata/", "1.0.0"
        ),
        "notation": Version(
            "http://www.eclipse.org/gmf/runtime/1.0.2/notation"
        ),
        "org.polarsys.capella.core.data.capellacommon": Version(
            "http://www.polarsys.org/capella/core/common/", "5.0.0"
        ),
        "org.polarsys.capella.core.data.capellacore": Version(
            "http://www.polarsys.org/capella/core/core/", "5.0.0"
        ),
        "org.polarsys.capella.core.data.capellamodeller": Version(
            "http://www.polarsys.org/capella/core/modeller/", "5.0.0"
        ),
        "org.polarsys.capella.core.data.cs": Version(
            "http://www.polarsys.org/capella/core/cs/", "5.0.0"
        ),
        "org.polarsys.capella.core.data.ctx": Version(
            "http://www.polarsys.org/capella/core/ctx/", "5.0.0"
        ),
        "org.polarsys.capella.core.data.epbs": Version(
            "http://www.polarsys.org/capella/core/epbs/", "5.0.0"
        ),
        "org.polarsys.capella.core.data.fa": Version(
            "http://www.polarsys.org/capella/core/fa/", "5.0.0"
        ),
        "org.polarsys.capella.core.data.information": Version(
            "http://www.polarsys.org/capella/core/information/", "5.0.0"
        ),
        "org.polarsys.capella.core.data.information.datatype": Version(
            "http://www.polarsys.org/capella/core/information/datatype/",
            "5.0.0",
        ),
        "org.polarsys.capella.core.data.information.datavalue": Version(
            "http://www.polarsys.org/capella/core/information/datavalue/",
            "5.0.0",
        ),
        "org.polarsys.capella.core.data.interaction": Version(
            "http://www.polarsys.org/capella/core/interaction/", "5.0.0"
        ),
        "org.polarsys.capella.core.data.la": Version(
            "http://www.polarsys.org/capella/core/la/", "5.0.0"
        ),
        "org.polarsys.capella.core.data.oa": Version(
            "http://www.polarsys.org/capella/core/oa/", "5.0.0"
        ),
        "org.polarsys.capella.core.data.pa": Version(
            "http://www.polarsys.org/capella/core/pa/", "5.0.0"
        ),
        "re": Version("http://www.polarsys.org/capella/common/re/", "1.3.0"),
        "sequence": Version(
            "http://www.eclipse.org/sirius/diagram/sequence/", "2.0.0"
        ),
        "style": Version(
            "http://www.eclipse.org/sirius/diagram/description/style/", "1.1.0"
        ),
        "table": Version("http://www.eclipse.org/sirius/table/", "1.1.0"),
        "viewpoint": Version("http://www.eclipse.org/sirius/", "1.1.0"),
        "xmi": Version("http://www.omg.org/XMI"),
        "xsi": Version("http://www.w3.org/2001/XMLSchema-instance"),
    }
)
