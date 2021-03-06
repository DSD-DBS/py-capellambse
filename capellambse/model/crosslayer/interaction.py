# Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

from .. import common as c

XT_CAP2PROC = "org.polarsys.capella.core.data.interaction:FunctionalChainAbstractCapabilityInvolvement"
XT_CAP2ACT = "org.polarsys.capella.core.data.interaction:AbstractFunctionAbstractCapabilityInvolvement"
XT_CAP_REAL = (
    "org.polarsys.capella.core.data.interaction:AbstractCapabilityRealization"
)


@c.xtype_handler(None)
class Scenario(c.GenericElement):
    """A scenario that holds instance roles."""


class Exchange(c.GenericElement):
    """An abstract Exchange."""

    source = c.ParentAccessor(c.GenericElement)


@c.xtype_handler(None)
class AbstractCapabilityExtend(Exchange):
    """An AbstractCapabilityExtend."""

    _xmltag = "extends"

    target = c.AttrProxyAccessor(c.GenericElement, "extended")


@c.xtype_handler(None)
class AbstractCapabilityInclude(Exchange):
    """An AbstractCapabilityInclude."""

    _xmltag = "includes"

    target = c.AttrProxyAccessor(c.GenericElement, "included")


@c.xtype_handler(None)
class AbstractCapabilityGeneralization(Exchange):
    """An AbstractCapabilityGeneralization."""

    _xmltag = "superGeneralizations"

    target = c.AttrProxyAccessor(c.GenericElement, "super")


class AbstractInvolvement(c.GenericElement):
    """An abstract Involvement."""

    involved = c.AttrProxyAccessor(c.GenericElement, "involved")

    @property
    def name(self) -> str:  # type: ignore
        return f"[{self.__class__.__name__}] to {self.involved.name} ({self.involved.uuid})"


@c.xtype_handler(None)
class AbstractFunctionAbstractCapabilityInvolvement(AbstractInvolvement):
    """An abstract CapabilityInvolvement linking to SystemFunctions."""
