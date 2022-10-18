# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

__all__ = ["UnsupportedPluginError", "UnsupportedPluginVersionError"]

import collections.abc as cabc
import dataclasses
import re
import types
import typing as t

PLUGIN_PATTERN = re.compile(r"(.*?)(\d\.\d\.\d)?$")


class UnsupportedPluginError(ValueError):
    """Raised when a plugin is unknown."""


class UnsupportedPluginVersionError(ValueError):
    """Raised when the plugin's version is unsupported."""

    def __str__(self) -> str:
        plugin, ns_plugin = self.args
        assert isinstance(plugin, Plugin) and isinstance(ns_plugin, Plugin)
        return (
            f"Plugin '{plugin.name}' with unsupported version encountered: "
            f"{plugin.version!r} does not match {ns_plugin.version!r}."
        )


@dataclasses.dataclass(frozen=True)
class Plugin:
    """Capella xml-element/plugin with info about name and version."""

    name: str
    version: str | tuple[str, str] | None = None

    @property
    def _values(self) -> cabc.Iterator[str | None]:
        yield self.name
        if isinstance(self.version, tuple):
            min_supported_version, max_supported_version = self.version
            yield min_supported_version
            yield max_supported_version
        else:
            yield self.version

    @property
    def has_version(self) -> bool:
        return self.version is not None

    def __le__(self, other: Plugin) -> bool:
        if self.version is None:
            raise AttributeError(f"Plugin '{self.name}' has no version")

        if isinstance(other.version, tuple):
            assert all((isinstance(o, str) for o in other.version))
            vmin, vmax = tuple(map(_tofloat, other.version))
            if isinstance(self.version, tuple):
                vsmin, vsmax = tuple(map(_tofloat, self.version))
                return vsmin <= vmin <= vmax <= vsmax
            else:
                return vmin <= _tofloat(self.version) <= vmax

        assert other.version is not None
        oversion = _tofloat(other.version)
        if isinstance(self.version, tuple):
            vsmin, vsmax = tuple(map(_tofloat, self.version))
            return vsmin <= oversion <= vsmax

        return oversion <= _tofloat(self.version)

    def __str__(self) -> str:
        if isinstance(suffix := list(self._values)[1], str):
            return self.name + suffix
        return self.name

    def __repr__(self) -> str:
        if len(_values := list(self._values)) > 2:
            name, minv, maxv = _values
            values = [name, f"[{minv}|{maxv}]"]
        else:
            name, version = _values
            values = [name]
            if version is not None:
                values.append(version)
        return "".join(values)  # type: ignore[arg-type]


def _tofloat(other: str) -> float:
    """Change 1.x.y...str into 1.x float."""
    version = other.split(".")
    if len(version) > 1:
        version = version[:2]

    return float(".".join(version))


def get_keys_and_plugins_from_namespaces_by_url(
    url: str,
) -> tuple[str, Plugin]:
    """Return key and :class:`Plugin` pair matching from ``NAMESPACES``.

    Parameters
    ----------
    url
        An ``xsi:type``-ish string of an xml-element/plugin

    Raises
    ------
    UnsupportedPluginError
        If requested ``url`` is not found in :class:`NAMESPACES`.

    Returns
    -------
    nskey, plugin
        A namespace-key string and a Plugin
    """
    match = PLUGIN_PATTERN.match(url)
    version = None
    if match is not None:
        plugin_name = match.group(1)
        if match.group(2) is not None:
            version = match.group(2)

    matched_plugins = [
        (nskey, Plugin(plugin_name, version))
        for nskey, nsplugin in NAMESPACES_PLUGINS.items()
        if plugin_name == nsplugin.name
    ]
    if not matched_plugins:
        plugin = Plugin(plugin_name, version)
        raise UnsupportedPluginError(f"{plugin}")
    assert (
        len(matched_plugins) == 1
    ), f"Ambiguous namespace {url!r}: {matched_plugins}"
    return matched_plugins[0]


def check_plugin(nskey: str, plugin: Plugin) -> None:
    r"""Check if the given ``plugin`` is supported.

    It is assumed that ``plugin`` is known by
    :class:`NAMESPACES_PLUGINS` from the ``nskey``. This can be ensured
    by a previous execution of
    :func:`get_keys_and_plugins_from_namespaces_by_url`.

    Parameters
    ----------
    nskey
        A key corresponding to given ``plugin`` to find a similiar
        plugin in :class:`NAMESPACES_PLUGINS`
    plugin
        A plugin for which a similiar plugin can be found in
        :class:`NAMESPACES_PLUGINS` from the given ``nskey``

    Raises
    ------
    UnsupportedPluginError
        If given ``plugin`` is unknown. This is the case when either:
          * It is not in :class:`NAMESPACES_PLUGINS`'s ``values`` or
          * an unknown ``nskey`` requested a plugin, i.e. ``nskey`` is
            not in :class:`NAMESPACES_PLUGINS`'s keys.
    UnsupportedPluginVersionError
        If given plugin is versioned and one of the following conditions
        is met:
          * If given ``plugin``'s version is singular and exceeds plugin
            version from :class:`NAMESPACES_PLUGINS` or
          * if ``plugin``\ s version is a range and is not contained in
            plugin version range from :class:`NAMESPACES_PLUGINS`.
    """
    try:
        my_plugin = NAMESPACES_PLUGINS[nskey]
    except KeyError as err:
        raise UnsupportedPluginError(str(plugin)) from err

    if plugin.has_version and not plugin <= my_plugin:
        raise UnsupportedPluginVersionError(plugin, my_plugin)


#: These XML namespaces are defined in every ``.aird`` document
NAMESPACES_PLUGINS: t.Final[
    cabc.Mapping[str, Plugin]
] = types.MappingProxyType(
    {
        "CapellaRequirements": Plugin(
            "http://www.polarsys.org/capella/requirements"
        ),
        "Requirements": Plugin(
            "http://www.polarsys.org/kitalpha/requirements"
        ),
        "concern": Plugin(
            "http://www.eclipse.org/sirius/diagram/description/concern/",
            "1.1.0",
        ),
        "description": Plugin(
            "http://www.eclipse.org/sirius/description/", "1.1.0"
        ),
        "description_1": Plugin(
            "http://www.eclipse.org/sirius/diagram/description/", "1.1.0"
        ),
        "description_2": Plugin(
            "http://www.eclipse.org/sirius/table/description/", "1.1.0"
        ),
        "description_3": Plugin(
            "http://www.eclipse.org/sirius/diagram/sequence/description/",
            "2.0.0",
        ),
        "diagram": Plugin("http://www.eclipse.org/sirius/diagram/", "1.1.0"),
        "diagramstyler": Plugin("http://thalesgroup.com/mde/melody/ordering"),
        "ecore": Plugin("http://www.eclipse.org/emf/2002/Ecore"),
        "filter": Plugin(
            "http://www.eclipse.org/sirius/diagram/description/filter/",
            "1.1.0",
        ),
        "libraries": Plugin(
            "http://www.polarsys.org/capella/common/libraries/",
            ("5.0.0", "6.0.0"),
        ),
        "metadata": Plugin(
            "http://www.polarsys.org/kitalpha/ad/metadata/", "1.0.0"
        ),
        "notation": Plugin(
            "http://www.eclipse.org/gmf/runtime/1.0.2/notation"
        ),
        "org.polarsys.capella.core.data.capellacommon": Plugin(
            "http://www.polarsys.org/capella/core/common/", ("5.0.0", "6.0.0")
        ),
        "org.polarsys.capella.core.data.capellacore": Plugin(
            "http://www.polarsys.org/capella/core/core/", ("5.0.0", "6.0.0")
        ),
        "org.polarsys.capella.core.data.capellamodeller": Plugin(
            "http://www.polarsys.org/capella/core/modeller/",
            ("5.0.0", "6.0.0"),
        ),
        "org.polarsys.capella.core.data.cs": Plugin(
            "http://www.polarsys.org/capella/core/cs/", ("5.0.0", "6.0.0")
        ),
        "org.polarsys.capella.core.data.ctx": Plugin(
            "http://www.polarsys.org/capella/core/ctx/", ("5.0.0", "6.0.0")
        ),
        "org.polarsys.capella.core.data.epbs": Plugin(
            "http://www.polarsys.org/capella/core/epbs/", ("5.0.0", "6.0.0")
        ),
        "org.polarsys.capella.core.data.fa": Plugin(
            "http://www.polarsys.org/capella/core/fa/", ("5.0.0", "6.0.0")
        ),
        "org.polarsys.capella.core.data.information": Plugin(
            "http://www.polarsys.org/capella/core/information/",
            ("5.0.0", "6.0.0"),
        ),
        "org.polarsys.capella.core.data.information.datatype": Plugin(
            "http://www.polarsys.org/capella/core/information/datatype/",
            ("5.0.0", "6.0.0"),
        ),
        "org.polarsys.capella.core.data.information.datavalue": Plugin(
            "http://www.polarsys.org/capella/core/information/datavalue/",
            ("5.0.0", "6.0.0"),
        ),
        "org.polarsys.capella.core.data.interaction": Plugin(
            "http://www.polarsys.org/capella/core/interaction/",
            ("5.0.0", "6.0.0"),
        ),
        "org.polarsys.capella.core.data.la": Plugin(
            "http://www.polarsys.org/capella/core/la/", ("5.0.0", "6.0.0")
        ),
        "org.polarsys.capella.core.data.oa": Plugin(
            "http://www.polarsys.org/capella/core/oa/", ("5.0.0", "6.0.0")
        ),
        "org.polarsys.capella.core.data.pa": Plugin(
            "http://www.polarsys.org/capella/core/pa/", ("5.0.0", "6.0.0")
        ),
        "re": Plugin("http://www.polarsys.org/capella/common/re/", "1.3.0"),
        "sequence": Plugin(
            "http://www.eclipse.org/sirius/diagram/sequence/", "2.0.0"
        ),
        "style": Plugin(
            "http://www.eclipse.org/sirius/diagram/description/style/", "1.1.0"
        ),
        "table": Plugin("http://www.eclipse.org/sirius/table/", "1.1.0"),
        "viewpoint": Plugin("http://www.eclipse.org/sirius/", "1.1.0"),
        "xmi": Plugin("http://www.omg.org/XMI"),
        "xsi": Plugin("http://www.w3.org/2001/XMLSchema-instance"),
    }
)
NAMESPACES: t.Final[cabc.Mapping[str, str]] = {
    nskey: str(plugin) for nskey, plugin in NAMESPACES_PLUGINS.items()
}
