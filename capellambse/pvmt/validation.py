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
"""Validation functions for PVMT."""

import logging
import operator
import re

import capellambse
from capellambse import (
    helpers,
    yield_key_and_version_from_namespaces_by_plugin,
)

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
                "Element {!r} is out of scope for PV group {}.{}".format(
                    xml_element, groupdef.parent.name, groupdef.name
                )
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

    nskey, version = next(
        yield_key_and_version_from_namespaces_by_plugin(match.group(1))
    )
    assert version <= capellambse.NAMESPACES.get_version(nskey)

    return (
        xml_element.get(f'{{{capellambse.NAMESPACES["xsi"]}}}type', "")
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
            "Comparison operator {!r} is not implemented".format(proptype)
        ) from None

    return compare(
        proptype.serialize(propval), proptype.serialize(match.group("val"))
    )


VALIDATION_FUNCTIONS = {
    "ARCHITECTURE": _validate_group_scope_arch,
    "CLASS": _validate_group_scope_class,
    "PROPERTY": _validate_group_scope_prop,
}
