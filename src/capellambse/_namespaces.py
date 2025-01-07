# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

__all__ = ["UnsupportedPluginError", "UnsupportedPluginVersionError"]

import collections.abc as cabc
import dataclasses
import re
import typing as t


class UnsupportedPluginError(ValueError):
    """Raised when a plugin is unknown."""


class UnsupportedPluginVersionError(ValueError):
    """Raised when the plugin's version is unsupported."""

    def __str__(self) -> str:
        if len(self.args) != 2:
            return super().__str__()
        plugin, ns_plugin = self.args
        assert isinstance(plugin, Plugin)
        assert isinstance(ns_plugin, Plugin)
        return (
            f"Plugin '{plugin.name}' with unsupported version encountered: "
            f"{plugin.version!r} does not match {ns_plugin.version!r}."
        )


@dataclasses.dataclass(frozen=True)
class Plugin:
    """Capella xml-element/plugin with info about name and version."""

    name: str
    version: str | tuple[str, str] | None = None
    viewpoint: str | None = None

    version_precision: int = 1
    """Number of significant parts in the version number for namespaces.

    When generating a versioned namespace URL from a Plugin, only this
    many digits will be taken from the activated viewpoint. This allows
    reusing the same namespace across subsequent minor plugin releases.

    Example: A version of "1.2.3" with precision set to 2 will result in
    the namespace version "1.2.0" being used.

    Note that the used version number will always be padded with zeroes
    to as many parts as there are in the original version number.
    """

    def __post_init__(self) -> None:
        if self.version is not None and self.viewpoint is None:
            raise TypeError("Versioned plugins require a viewpoint")

    @property
    def min_version(self) -> str | None:
        if isinstance(self.version, str):
            return self.version
        if isinstance(self.version, tuple):
            return self.version[0]
        return None

    @property
    def max_version(self) -> str | None:
        if isinstance(self.version, str):
            return self.version
        if isinstance(self.version, tuple):
            return self.version[1]
        return None

    def __le__(self, other: Plugin) -> bool:
        if self.version is None:
            raise AttributeError(f"Plugin '{self.name}' has no version")

        if isinstance(other.version, tuple):
            assert all(isinstance(o, str) for o in other.version)
            vmin, vmax = tuple(map(_tofloat, other.version))
            if isinstance(self.version, tuple):
                vsmin, vsmax = tuple(map(_tofloat, self.version))
                return vsmin <= vmin <= vmax <= vsmax
            return vmin <= _tofloat(self.version) <= vmax

        assert other.version is not None
        oversion = _tofloat(other.version)
        if isinstance(self.version, tuple):
            vsmin, vsmax = tuple(map(_tofloat, self.version))
            return vsmin <= oversion <= vsmax

        return oversion <= _tofloat(self.version)

    def __str__(self) -> str:
        if suffix := self.min_version:
            return self.name + suffix
        return self.name

    def matches_version(self, value: str | None) -> bool:
        """Check whether a version number is supported by this plugin."""
        if value is None:
            return self.version is None
        if self.version is None:
            return True
        if isinstance(self.version, str):
            return self.version == value

        for mymin, mymax, their in zip(
            self.version[0].split("."),
            self.version[1].split("."),
            value.split("."),
            strict=False,
        ):
            if not int(mymin) <= int(their) <= int(mymax):
                return False
        return True


def _tofloat(other: str) -> float:
    """Change 1.x.y...str into 1.x float."""
    version = other.split(".")
    if len(version) > 1:
        version = version[:2]

    return float(".".join(version))


def get_namespace_prefix(url: str) -> str:
    """Map a namespace URL to its symbolic name (the "prefix").

    Parameters
    ----------
    url
        A namespace URL.

    Raises
    ------
    UnsupportedPluginError
        If the given URL does not match any known plugin.
    UnsupportedPluginVersionError
        If the URL matches a known plugin, but the version indicated by
        the URL is outside of the supported range.

    Returns
    -------
    str
        The symbolic name of the namespace matching the URI.
    """
    match = re.match(r"(.*/)((?:\d+\.)*\d+)$", url)
    if match:
        plugin_name, version = match.groups()
    else:
        plugin_name, version = url, None

    matched_plugins = [
        (nskey, nsplugin)
        for nskey, nsplugin in NAMESPACES_PLUGINS.items()
        if nsplugin.name in (plugin_name, url)
    ]
    if not matched_plugins:
        raise UnsupportedPluginError(url)
    if len(matched_plugins) != 1:
        raise RuntimeError(f"Ambiguous namespace {url!r}: {matched_plugins}")
    prefix, plugin = matched_plugins[0]

    if not plugin.matches_version(version):
        raise UnsupportedPluginVersionError(plugin_name, version)

    return prefix


NAMESPACES_PLUGINS: t.Final[cabc.Mapping[str, Plugin]] = {
    "CapellaRequirements": Plugin(
        "http://www.polarsys.org/capella/requirements",
        None,
        "org.polarsys.capella.vp.requirements",
    ),
    "Requirements": Plugin(
        "http://www.polarsys.org/kitalpha/requirements",
        None,
        "org.polarsys.kitalpha.vp.requirements",
    ),
    "concern": Plugin(
        "http://www.eclipse.org/sirius/diagram/description/concern/1.1.0",
    ),
    "description": Plugin("http://www.eclipse.org/sirius/description/1.1.0"),
    "description_1": Plugin(
        "http://www.eclipse.org/sirius/diagram/description/1.1.0"
    ),
    "description_2": Plugin(
        "http://www.eclipse.org/sirius/table/description/1.1.0"
    ),
    "description_3": Plugin(
        "http://www.eclipse.org/sirius/diagram/sequence/description/2.0.0",
    ),
    "diagram": Plugin("http://www.eclipse.org/sirius/diagram/1.1.0"),
    "diagramstyler": Plugin("http://thalesgroup.com/mde/melody/ordering"),
    "ecore": Plugin("http://www.eclipse.org/emf/2002/Ecore"),
    "filter": Plugin(
        "http://www.eclipse.org/sirius/diagram/description/filter/1.1.0",
    ),
    "libraries": Plugin(
        "http://www.polarsys.org/capella/common/libraries/",
        ("5.0.0", "7.0.0"),
        "org.polarsys.capella.core.viewpoint",
    ),
    "metadata": Plugin("http://www.polarsys.org/kitalpha/ad/metadata/1.0.0"),
    "notation": Plugin("http://www.eclipse.org/gmf/runtime/1.0.2/notation"),
    "org.polarsys.capella.core.data.capellacommon": Plugin(
        "http://www.polarsys.org/capella/core/common/",
        ("5.0.0", "7.0.0"),
        "org.polarsys.capella.core.viewpoint",
    ),
    "org.polarsys.capella.core.data.capellacore": Plugin(
        "http://www.polarsys.org/capella/core/core/",
        ("5.0.0", "7.0.0"),
        "org.polarsys.capella.core.viewpoint",
    ),
    "org.polarsys.capella.core.data.capellamodeller": Plugin(
        "http://www.polarsys.org/capella/core/modeller/",
        ("5.0.0", "7.0.0"),
        "org.polarsys.capella.core.viewpoint",
    ),
    "org.polarsys.capella.core.data.cs": Plugin(
        "http://www.polarsys.org/capella/core/cs/",
        ("5.0.0", "7.0.0"),
        "org.polarsys.capella.core.viewpoint",
    ),
    "org.polarsys.capella.core.data.ctx": Plugin(
        "http://www.polarsys.org/capella/core/ctx/",
        ("5.0.0", "7.0.0"),
        "org.polarsys.capella.core.viewpoint",
    ),
    "org.polarsys.capella.core.data.epbs": Plugin(
        "http://www.polarsys.org/capella/core/epbs/",
        ("5.0.0", "7.0.0"),
        "org.polarsys.capella.core.viewpoint",
    ),
    "org.polarsys.capella.core.data.fa": Plugin(
        "http://www.polarsys.org/capella/core/fa/",
        ("5.0.0", "7.0.0"),
        "org.polarsys.capella.core.viewpoint",
    ),
    "org.polarsys.capella.core.data.information": Plugin(
        "http://www.polarsys.org/capella/core/information/",
        ("5.0.0", "7.0.0"),
        "org.polarsys.capella.core.viewpoint",
    ),
    "org.polarsys.capella.core.data.information.datatype": Plugin(
        "http://www.polarsys.org/capella/core/information/datatype/",
        ("5.0.0", "7.0.0"),
        "org.polarsys.capella.core.viewpoint",
    ),
    "org.polarsys.capella.core.data.information.datavalue": Plugin(
        "http://www.polarsys.org/capella/core/information/datavalue/",
        ("5.0.0", "7.0.0"),
        "org.polarsys.capella.core.viewpoint",
    ),
    "org.polarsys.capella.core.data.interaction": Plugin(
        "http://www.polarsys.org/capella/core/interaction/",
        ("5.0.0", "7.0.0"),
        "org.polarsys.capella.core.viewpoint",
    ),
    "org.polarsys.capella.core.data.la": Plugin(
        "http://www.polarsys.org/capella/core/la/",
        ("5.0.0", "7.0.0"),
        "org.polarsys.capella.core.viewpoint",
    ),
    "org.polarsys.capella.core.data.oa": Plugin(
        "http://www.polarsys.org/capella/core/oa/",
        ("5.0.0", "7.0.0"),
        "org.polarsys.capella.core.viewpoint",
    ),
    "org.polarsys.capella.core.data.pa": Plugin(
        "http://www.polarsys.org/capella/core/pa/",
        ("5.0.0", "7.0.0"),
        "org.polarsys.capella.core.viewpoint",
    ),
    "re": Plugin(
        "http://www.polarsys.org/capella/common/re/",
        ("5.0.0", "7.0.0"),
        "org.polarsys.capella.core.viewpoint",
    ),
    "sequence": Plugin("http://www.eclipse.org/sirius/diagram/sequence/2.0.0"),
    "style": Plugin(
        "http://www.eclipse.org/sirius/diagram/description/style/1.1.0"
    ),
    "table": Plugin("http://www.eclipse.org/sirius/table/1.1.0"),
    "viewpoint": Plugin("http://www.eclipse.org/sirius/1.1.0"),
    "xmi": Plugin("http://www.omg.org/XMI"),
    "xsi": Plugin("http://www.w3.org/2001/XMLSchema-instance"),
}
NAMESPACES: t.Final[cabc.Mapping[str, str]] = {
    nskey: str(plugin) for nskey, plugin in NAMESPACES_PLUGINS.items()
}
