# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

from .. import common as c

XT_CAP2PROC = (
    "org.polarsys.capella.core.data.interaction"
    ":FunctionalChainAbstractCapabilityInvolvement"
)
XT_CAP2ACT = (
    "org.polarsys.capella.core.data.interaction"
    ":AbstractFunctionAbstractCapabilityInvolvement"
)
XT_CAP_REAL = (
    "org.polarsys.capella.core.data.interaction"
    ":AbstractCapabilityRealization"
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

    source = c.ParentAccessor(c.GenericElement)
    target = c.AttrProxyAccessor(c.GenericElement, "extended")


@c.xtype_handler(None)
class AbstractCapabilityInclude(Exchange):
    """An AbstractCapabilityInclude."""

    _xmltag = "includes"

    source = c.ParentAccessor(c.GenericElement)
    target = c.AttrProxyAccessor(c.GenericElement, "included")


@c.xtype_handler(None)
class AbstractCapabilityGeneralization(Exchange):
    """An AbstractCapabilityGeneralization."""

    _xmltag = "superGeneralizations"

    source = c.ParentAccessor(c.GenericElement)
    target = c.AttrProxyAccessor(c.GenericElement, "super")


class AbstractInvolvement(c.GenericElement):
    """An abstract Involvement."""

    source = c.ParentAccessor(c.GenericElement)
    target = c.AttrProxyAccessor(c.GenericElement, "involved")

    involved = c.AttrProxyAccessor(c.GenericElement, "involved")

    @property
    def name(self) -> str:  # type: ignore[override]
        """Return the name."""
        direction = ""
        if self.involved is not None:
            direction = f" to {self.involved.name} ({self.involved.uuid})"

        return f"[{self.__class__.__name__}]{direction}"


@c.xtype_handler(None)
class AbstractFunctionAbstractCapabilityInvolvement(AbstractInvolvement):
    """An abstract CapabilityInvolvement linking to SystemFunctions."""
