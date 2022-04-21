# Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

from .. import common as c

XT_CAP2PROC = "org.polarsys.capella.core.data.interaction:FunctionalChainAbstractCapabilityInvolvement"
XT_CAP2ACT = "org.polarsys.capella.core.data.interaction:AbstractFunctionAbstractCapabilityInvolvement"
XT_CAP_GEN = "org.polarsys.capella.core.data.interaction:AbstractCapabilityGeneralization"
XT_SCENARIO = "org.polarsys.capella.core.data.interaction:Scenario"
XT_CAP_REAL = (
    "org.polarsys.capella.core.data.interaction:AbstractCapabilityRealization"
)


@c.xtype_handler(None)
class Scenario(c.GenericElement):
    """A scenario that holds instance roles."""
