# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

from .. import common as c


@c.xtype_handler(None)
class Constraint(c.GenericElement):
    """A constraint."""

    _xmltag = "ownedConstraints"

    constrained_elements = c.AttrProxyAccessor(
        c.GenericElement,
        "constrainedElements",
        aslist=c.MixedElementList,
    )

    specification = c.SpecificationAccessor()


@c.xtype_handler(None)
class Generalization(c.GenericElement):
    """A Generalization."""

    _xmltag = "ownedGeneralizations"


c.set_accessor(
    c.GenericElement,
    "constraints",
    c.DirectProxyAccessor(Constraint, aslist=c.ElementList),
)
