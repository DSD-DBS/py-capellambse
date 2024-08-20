# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Model-level PVMT configuration."""

from __future__ import annotations

__all__ = [
    "ManagedDomain",
    "ManagedGroup",
    "PVMTConfiguration",
    "PVMTDescriptionProperty",
    "ScopeError",
    "SelectorRules",
]

import collections.abc as cabc
import dataclasses
import logging
import operator
import re
import typing as t

import markupsafe
import typing_extensions as te
from lxml import etree

import capellambse
import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers

LOGGER = logging.getLogger(__name__)

PVMT_SCHEMA_VERSION = "1.0.0"

_PROP_OPS: dict[str, cabc.Callable[[t.Any, t.Any], bool]] = {
    "=": operator.eq,
    "!": operator.ne,
    "?": operator.contains,
    "&": str.startswith,
    "#": str.endswith,
    "<": operator.lt,
    ">": operator.gt,
    "%": operator.le,
    ":": operator.ge,
}
_PROP_OPS_RE = "|".join(re.escape(op) for op in _PROP_OPS)
_PROP_RE = re.compile(
    rf"^(?P<prop>[^.]+\.[^.]+\.[^.]+)(?P<op>{_PROP_OPS_RE})(?P<val>.*)"
)
_RULES_RE = re.compile(
    r"(?m)\[(?P<key>\w+)\]\s*(?P<value>.+?)\s*\[/(?P=key)\]"
)


class ScopeError(m.InvalidModificationError):
    """Raised when trying to apply a PVMT group to an out-of-scope element."""

    @property
    def group(self) -> ManagedGroup:
        return self.args[0]

    @property
    def obj(self) -> m.ModelObject:
        return self.args[1]

    def __str__(self) -> str:
        groupname = f"{self.group.parent.name}.{self.group.name}"
        objrepr = getattr(self.obj, "_short_repr_", lambda: repr(self.obj))()
        return f"PVMT group {groupname!r} does not apply to {objrepr}"


def _matchprops(
    obj: m.ModelObject,
    props: tuple[tuple[str, str, str], ...],
) -> bool:
    for prop, op, wanted in props:
        group, prop = prop.rsplit(".", 1)
        try:
            actual = obj.property_value_groups[group][prop]  # type: ignore
        except (AttributeError, KeyError):
            return False

        cmp = _PROP_OPS[op]
        if isinstance(actual, float | int | str):
            ismatch = cmp(actual, type(actual)(wanted))
        elif isinstance(actual, bool):
            ismatch = cmp(actual, wanted == "true")
        elif isinstance(actual, mm.capellacore.EnumerationPropertyLiteral):
            ismatch = cmp(actual.name, wanted)
        else:
            raise TypeError(
                f"Unhandled property value type: {type(actual).__name__}"
            )

        if not ismatch:
            return False

    return True


@dataclasses.dataclass(frozen=True)
class SelectorRules:
    raw: str

    @property
    def classes(self) -> tuple[type[m.ModelObject], ...]:
        classes = []
        for match in _RULES_RE.finditer(self.raw):
            if match.group("key") != "CLASS":
                continue
            uri = match.group("value")
            _, clsname = uri.rsplit("/", 1)
            (cls,) = m.find_wrapper(clsname)
            classes.append(cls)

        return tuple(classes)

    @property
    def layers(self) -> tuple[type[mm.cs.ComponentArchitecture], ...]:
        classes: list[type[mm.cs.ComponentArchitecture]] = []
        for match in _RULES_RE.finditer(self.raw):
            if match.group("key") != "ARCHITECTURE":
                continue

            for arch in match.group("value").split(";"):
                if arch == "OPERATIONAL":
                    classes.append(mm.oa.OperationalAnalysis)
                elif arch == "SYSTEM":
                    classes.append(mm.sa.SystemAnalysis)
                elif arch == "LOGICAL":
                    classes.append(mm.la.LogicalArchitecture)
                elif arch == "PHYSICAL":
                    classes.append(mm.pa.PhysicalArchitecture)
                else:
                    LOGGER.debug("Unknown ARCHITECTURE, ignoring: %r", arch)

        return tuple(classes)

    @property
    def properties(self) -> tuple[tuple[str, str, str], ...]:
        propdefs = []
        for rule in _RULES_RE.finditer(self.raw):
            if rule.group("key") != "PROPERTY":
                continue

            value = rule.group("value")
            match = _PROP_RE.fullmatch(value)
            if not match:
                raise RuntimeError(f"Invalid property spec: {value!r}")
            propdefs.append(match.group("prop", "op", "val"))
        return tuple(t.cast("list[tuple[str, str, str]]", propdefs))


class PVMTDescriptionProperty(m.BasePOD[SelectorRules]):
    def __init__(self, attribute: str) -> None:
        super().__init__(attribute, default=SelectorRules(""), writable=True)
        self.__doc__ = "The element selector rules for this group."

    def _from_xml(self, data: str, /) -> SelectorRules:
        return SelectorRules(data)

    def _to_xml(self, value: SelectorRules | str, /) -> str:
        if isinstance(value, SelectorRules):
            value = value.raw
        elif not isinstance(value, str):
            raise TypeError(
                "Unsupported type, must be str or SelectorRules:"
                f" {type(value).__name__}"
            )

        # TODO implement validation
        return value


class ManagedGroup(m.ModelElement):
    """A managed group of property values."""

    _required_attrs = frozenset({"name"})

    selector = PVMTDescriptionProperty("description")
    description = m.Alias("selector", dirhide=True)  # type: ignore[assignment]

    @property
    def fullname(self) -> str:
        return f"{self.parent.name}.{self.name}"

    def applies_to(self, obj: m.ModelObject) -> bool:
        """Determine whether this group applies to a model element."""
        classes = self.selector.classes
        if classes and type(obj) not in classes:
            return False
        layers = self.selector.layers
        if layers and type(getattr(obj, "layer", None)) not in layers:
            return False

        if props := self.selector.properties:
            return _matchprops(obj, props)
        return True

    def find_applicable(self) -> m.ElementList:
        """Find all elements in the model that this group applies to."""
        objs = self._model.search(*self.selector.classes)
        if layers := self.selector.layers:
            objs = objs.filter(
                lambda i: isinstance(getattr(i, "layer", None), layers)
            )
        if props := self.selector.properties:
            objs = objs.filter(lambda i: _matchprops(i, props))
        return objs

    def apply(self, obj: m.ModelObject) -> mm.capellacore.PropertyValueGroup:
        """Apply this group to the model element, and return the applied group.

        If the group is not applicable to the passed element, a
        :class:ScopeError will be raised.

        If the group was already applied earlier, that group instance
        will be returned instead. This makes it safe to always use this
        method when working with PVMT-managed property value groups.
        """
        if not self.applies_to(obj):
            raise ScopeError(self, obj)

        objrepr = getattr(obj, "_short_repr_", lambda: repr(obj))
        if not hasattr(obj, "property_value_groups"):
            raise TypeError(f"Object cannot own PV groups: {objrepr()}")
        if not hasattr(obj, "applied_property_value_groups"):
            raise TypeError(f"Cannot apply PV groups to {objrepr()}")

        groupname = f"{self.parent.name}.{self.name}"
        try:
            return obj.property_value_groups.by_name(groupname, single=True)
        except KeyError:
            pass

        groupobj = obj.property_value_groups.create(
            name=groupname,
            applied_property_value_groups=[self],
        )
        for propdef in self.property_values:
            groupobj.property_values.create(
                m.build_xtype(type(propdef)),
                name=propdef.name,
                applied_property_values=[propdef],
                value=propdef.value,
            )
        assert hasattr(obj, "applied_property_value_groups")
        obj.applied_property_value_groups.append(groupobj)
        return groupobj

    def _short_html_(self) -> markupsafe.Markup:
        return helpers.make_short_html(
            type(self).__name__,
            self.uuid,
            self.fullname,
        )


class ManagedDomain(m.ModelElement):
    """A "domain" in the property value management extension."""

    _required_attrs = frozenset({"name"})

    version = property(
        lambda self: self.property_values.by_name("version").value
    )
    types = m.RoleTagAccessor(
        "ownedEnumerationPropertyTypes",
        mm.capellacore.EnumerationPropertyType,
    )
    groups = m.RoleTagAccessor(
        "ownedPropertyValueGroups",
        mm.capellacore.PropertyValueGroup,
        aslist=m.ElementList,
        mapkey="name",
        alternate=ManagedGroup,
    )
    enumeration_property_types = m.RoleTagAccessor(
        "ownedEnumerationPropertyTypes",
        mm.capellacore.EnumerationPropertyType,
        aslist=m.ElementList,
    )

    def __init__(
        self,
        model: capellambse.MelodyModel,
        parent: etree._Element,
        xmltag: str | None = None,
        /,
        **kw: t.Any,
    ) -> None:
        super().__init__(model, parent, xmltag, **kw)
        self.property_values.create(name="version", value=PVMT_SCHEMA_VERSION)

    @classmethod
    def from_model(
        cls, model: capellambse.MelodyModel, element: etree._Element
    ) -> te.Self:
        self = super().from_model(model, element)
        try:
            version = self.property_values.by_name("version").value
        except Exception:
            self.property_values.create(
                name="version", value=PVMT_SCHEMA_VERSION
            )
        else:
            if version != PVMT_SCHEMA_VERSION:
                raise RuntimeError(
                    f"Unsupported schema version {version!r}"
                    f" on PVMT element {self._short_repr_()}"
                )
        return self


class PVMTConfiguration(m.ModelElement):
    """Provides access to the model-wide PVMT configuration."""

    def __init__(self, *_args, **_kw) -> None:
        raise TypeError("Use 'model.pvmt' to access PVMT configuration")

    domains = m.RoleTagAccessor(
        "ownedPropertyValuePkgs",
        mm.capellacore.PropertyValuePkg,
        aslist=m.ElementList,
        mapkey="name",
        alternate=ManagedDomain,
    )
