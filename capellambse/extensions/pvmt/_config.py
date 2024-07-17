# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Model-level PVMT configuration."""
from __future__ import annotations

__all__ = [
    "ManagedDomain",
    "ManagedGroup",
    "PVMTConfiguration",
    "PVMTConfigurationAccessor",
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
import capellambse.model.common as c
from capellambse import helpers
from capellambse.model import capellacore
from capellambse.model import crosslayer as xl
from capellambse.model import la, oa, pa, sa

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


class ScopeError(c.InvalidModificationError):
    """Raised when trying to apply a PVMT group to an out-of-scope element."""

    @property
    def group(self) -> ManagedGroup:
        return self.args[0]

    @property
    def obj(self) -> c.ModelObject:
        return self.args[1]

    def __str__(self) -> str:
        groupname = f"{self.group.parent.name}.{self.group.name}"
        objrepr = getattr(self.obj, "_short_repr_", lambda: repr(self.obj))()
        return f"PVMT group {groupname!r} does not apply to {objrepr}"


def _matchprops(
    obj: c.ModelObject,
    props: tuple[tuple[str, str, str], ...],
) -> bool:
    for prop, op, wanted in props:
        group, prop = prop.rsplit(".", 1)
        try:
            actual = obj.property_value_groups[group][prop]  # type: ignore
        except (AttributeError, KeyError):
            return False

        cmp = _PROP_OPS[op]
        if isinstance(actual, (float, int, str)):
            ismatch = cmp(actual, type(actual)(wanted))
        elif isinstance(actual, bool):
            ismatch = cmp(actual, wanted == "true")
        elif isinstance(actual, capellacore.EnumerationPropertyLiteral):
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
    def classes(self) -> tuple[type[c.ModelObject], ...]:
        classes = []
        for match in _RULES_RE.finditer(self.raw):
            if match.group("key") != "CLASS":
                continue
            uri = match.group("value")
            _, clsname = uri.rsplit("/", 1)
            (cls,) = c.find_wrapper(clsname)
            classes.append(cls)

        return tuple(classes)

    @property
    def layers(self) -> tuple[type[xl.BaseArchitectureLayer], ...]:
        classes: list[type[xl.BaseArchitectureLayer]] = []
        for match in _RULES_RE.finditer(self.raw):
            if match.group("key") != "ARCHITECTURE":
                continue

            for arch in match.group("value").split(";"):
                if arch == "OPERATIONAL":
                    classes.append(oa.OperationalAnalysis)
                elif arch == "SYSTEM":
                    classes.append(sa.SystemAnalysis)
                elif arch == "LOGICAL":
                    classes.append(la.LogicalArchitecture)
                elif arch == "PHYSICAL":
                    classes.append(pa.PhysicalArchitecture)
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


class PVMTDescriptionProperty(c.AttributeProperty):
    def __init__(self, attribute: str) -> None:
        super().__init__(
            attribute,
            returntype=SelectorRules,
            default="",
            __doc__="The element selector rules for this group.",
        )

    def __set__(self, obj, value) -> None:
        if isinstance(value, SelectorRules):
            value = value.raw
        elif not isinstance(value, str):
            raise TypeError(
                "Unsupported type, must be str or SelectorRules:"
                f" {type(value).__name__}"
            )

        # TODO implement validation
        super().__set__(obj, value)


class ManagedGroup(c.GenericElement):
    """A managed group of property values."""

    _required_attrs = frozenset({"name"})

    selector = PVMTDescriptionProperty("description")
    description = c.Alias("selector", dirhide=True)  # type: ignore[assignment]

    @property
    def fullname(self) -> str:
        return f"{self.parent.name}.{self.name}"

    def applies_to(self, obj: c.ModelObject) -> bool:
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

    def find_applicable(self) -> c.ElementList:
        """Find all elements in the model that this group applies to."""
        objs = self._model.search(*self.selector.classes)
        if layers := self.selector.layers:
            objs = objs.filter(
                lambda i: isinstance(getattr(i, "layer", None), layers)
            )
        if props := self.selector.properties:
            objs = objs.filter(lambda i: _matchprops(i, props))
        return objs

    def apply(self, obj: c.ModelObject) -> capellacore.PropertyValueGroup:
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
                c.build_xtype(type(propdef)),
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


class ManagedDomain(c.GenericElement):
    """A "domain" in the property value management extension."""

    _required_attrs = frozenset({"name"})

    version = property(
        lambda self: self.property_values.by_name("version").value
    )
    types = c.RoleTagAccessor(
        "ownedEnumerationPropertyTypes",
        capellacore.EnumerationPropertyType,
    )
    groups = c.RoleTagAccessor(
        "ownedPropertyValueGroups",
        capellacore.PropertyValueGroup,
        aslist=c.ElementList,
        mapkey="name",
        alternate=ManagedGroup,
    )
    enumeration_property_types = c.RoleTagAccessor(
        "ownedEnumerationPropertyTypes",
        capellacore.EnumerationPropertyType,
        aslist=c.ElementList,
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


class PVMTConfiguration(c.GenericElement):
    """Provides access to the model-wide PVMT configuration."""

    # pylint: disable-next=super-init-not-called
    def __init__(self, *_args, **_kw) -> None:
        raise TypeError("Use 'model.pvmt' to access PVMT configuration")

    domains = c.RoleTagAccessor(
        "ownedPropertyValuePkgs",
        capellacore.PropertyValuePkg,
        aslist=c.ElementList,
        mapkey="name",
        alternate=ManagedDomain,
    )


class PVMTConfigurationAccessor(c.Accessor[PVMTConfiguration]):
    """Finds the model-wide PVMT configuration and provides access to it."""

    @t.overload
    def __get__(self, obj: None, objtype: type[t.Any]) -> te.Self: ...
    @t.overload
    def __get__(
        self, obj: c.ModelObject, objtype: type[c.ModelObject] | None = ...
    ) -> PVMTConfiguration: ...
    def __get__(self, obj, objtype=None):
        del objtype
        if obj is None:  # pragma: no cover
            return self

        try:
            ext = obj.property_value_packages.by_name("EXTENSIONS")
        except KeyError:
            LOGGER.debug("Creating EXTENSIONS package")
            ext = obj.property_value_packages.create(name="EXTENSIONS")
        return PVMTConfiguration.from_model(obj, ext._element)
