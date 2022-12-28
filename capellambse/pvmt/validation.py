# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Validation functions for PVMT."""

import logging
import operator
import re

import capellambse._namespaces as _n
from capellambse import helpers

from . import exceptions

LOGGER = logging.getLogger(__name__)

SCOPE_RE = re.compile(r"^\[([A-Z]+)\](.*)\[/\1\]$")
SCOPE_ARCH_MAP = {
    "OPERATIONAL": "org.polarsys.capella.core.data.oa:OperationalAnalysis",
    "SYSTEM": "org.polarsys.capella.core.data.ctx:SystemAnalysis",
    "LOGICAL": "org.polarsys.capella.core.data.la:LogicalArchitecture",
    "PHYSICAL": "org.polarsys.capella.core.data.pa:PhysicalArchitecture",
    "EPBS": "org.polarsys.capella.core.data.epbs:EPBSArchitecture",
}
SCOPE_CLASS_RE = re.compile(r"^(.*)/([^/]+)$")
SCOPE_PROP_OPERATORS = {
    "=": operator.eq,
    "!": operator.ne,
    "?": operator.contains,
    "&": lambda a, b: a.startswith(b),
    "#": lambda a, b: a.endswith(b),
    "<": operator.lt,
    ">": operator.gt,
    "%": operator.le,
    ":": operator.ge,
}
SCOPE_PROP_RE = re.compile(
    r"^(?P<group>[^.]+\.[^.]+)\.(?P<prop>[^.]+)"
    f'(?P<op>[{"".join(SCOPE_PROP_OPERATORS)}])'
    "(?P<val>.*)"
)


def validate_group_scope(pvmt_ext, groupdef, xml_element):
    """Verify that the ``groupdef``'s scope applies to the given element."""
    for scopeline in groupdef.scope.splitlines():
        scope = SCOPE_RE.match(scopeline)
        if scope is None:
            LOGGER.warning("Malformed scope description: %r", scopeline)
            continue

        try:
            func = VALIDATION_FUNCTIONS[scope.group(1)]
        except KeyError:
            LOGGER.warning("Unknown scope tag %r", scope.group(1))
            continue

        try:
            inscope = func(pvmt_ext, scope.group(2), xml_element)
        except AssertionError:
            LOGGER.warning(
                "Failed to parse [%s] scope %r", scope.group(1), scope.group(2)
            )
            continue

        if not inscope:
            raise exceptions.ScopeError(
                f"Element {xml_element!r} is out of scope for PV group "
                f"{groupdef.parent.name}.{groupdef.name}"
            )


def _validate_group_scope_arch(pvmt_ext, scopedesc, xml_element):
    arch_candidates = {
        helpers.xtype_of(i) for i in pvmt_ext.model.iterancestors(xml_element)
    }
    return bool(
        arch_candidates & set(SCOPE_ARCH_MAP[a] for a in scopedesc.split(";"))
    )


def _validate_group_scope_class(pvmt_ext, scopedesc, xml_element):
    del pvmt_ext
    match = SCOPE_CLASS_RE.match(scopedesc)
    assert match is not None

    ns = match.group(1)
    nskey, plugin = _n.get_keys_and_plugins_from_namespaces_by_url(ns)
    _n.check_plugin(nskey, plugin)
    return (
        xml_element.get(f"{{{_n.NAMESPACES['xsi']}}}type", "")
        == f"{nskey}:{match.group(2)}"
    )


def _validate_group_scope_prop(pvmt_ext, scopedesc, xml_element):
    match = SCOPE_PROP_RE.match(scopedesc)
    assert match is not None

    try:
        prop = pvmt_ext.get_element_pv(
            xml_element, match.group("group"), create=False
        )
        proptype = prop.get_definition(match.group("prop"))
        propval = prop[match.group("prop")]
    except (KeyError, ValueError):
        return False

    try:
        compare = SCOPE_PROP_OPERATORS[match.group("op")]
    except KeyError:
        raise NotImplementedError(
            f"Comparison operator {proptype!r} is not implemented"
        ) from None

    return compare(
        proptype.serialize(propval), proptype.serialize(match.group("val"))
    )


VALIDATION_FUNCTIONS = {
    "ARCHITECTURE": _validate_group_scope_arch,
    "CLASS": _validate_group_scope_class,
    "PROPERTY": _validate_group_scope_prop,
}
