# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Common namespace definitions for the Capella metamodel."""

from capellambse import modelv2 as model

ACTIVITY = model.Namespace(
    "http://www.polarsys.org/capella/common/activity/{VERSION}",
    "org.polarsys.capella.common.data.activity",
    model.CORE_VIEWPOINT,
    "6.0.0",
)
BEHAVIOR = model.Namespace(
    "http://www.polarsys.org/capella/common/behavior/{VERSION}",
    "org.polarsys.capella.common.data.behavior",
    model.CORE_VIEWPOINT,
    "6.0.0",
)
CAPELLACOMMON = model.Namespace(
    "http://www.polarsys.org/capella/core/common/{VERSION}",
    "org.polarsys.capella.core.data.capellacommon",
    model.CORE_VIEWPOINT,
    "6.0.0",
)
CAPELLACORE = model.Namespace(
    "http://www.polarsys.org/capella/core/core/{VERSION}",
    "org.polarsys.capella.core.data.capellacore",
    model.CORE_VIEWPOINT,
    "6.0.0",
)
CAPELLAMODELLER = model.Namespace(
    "http://www.polarsys.org/capella/core/modeller/{VERSION}",
    "org.polarsys.capella.core.data.capellamodeller",
    model.CORE_VIEWPOINT,
    "6.0.0",
)
CS = model.Namespace(
    "http://www.polarsys.org/capella/core/cs/{VERSION}",
    "org.polarsys.capella.core.data.cs",
    model.CORE_VIEWPOINT,
    "6.0.0",
)
EPBS = model.Namespace(
    "http://www.polarsys.org/capella/core/epbs/{VERSION}",
    "org.polarsys.capella.core.data.epbs",
    model.CORE_VIEWPOINT,
    "6.0.0",
)
FA = model.Namespace(
    "http://www.polarsys.org/capella/core/fa/{VERSION}",
    "org.polarsys.capella.core.data.fa",
    model.CORE_VIEWPOINT,
    "6.0.0",
)
INFORMATION = model.Namespace(
    "http://www.polarsys.org/capella/core/information/{VERSION}",
    "org.polarsys.capella.core.data.information",
    model.CORE_VIEWPOINT,
    "6.0.0",
)
INFORMATION_COMMUNICATION = model.Namespace(
    "http://www.polarsys.org/capella/core/information/communication/{VERSION}",
    "org.polarsys.capella.core.data.information.communication",
    model.CORE_VIEWPOINT,
    "6.0.0",
)
INFORMATION_DATATYPE = model.Namespace(
    "http://www.polarsys.org/capella/core/information/datatype/{VERSION}",
    "org.polarsys.capella.core.data.information.datatype",
    model.CORE_VIEWPOINT,
    "6.0.0",
)
INFORMATION_DATAVALUE = model.Namespace(
    "http://www.polarsys.org/capella/core/information/datavalue/{VERSION}",
    "org.polarsys.capella.core.data.information.datavalue",
    model.CORE_VIEWPOINT,
    "6.0.0",
)
INTERACTION = model.Namespace(
    "http://www.polarsys.org/capella/core/interaction/{VERSION}",
    "org.polarsys.capella.core.data.interaction",
    model.CORE_VIEWPOINT,
    "6.0.0",
)
MODELLINGCORE = model._obj.NS
LA = model.Namespace(
    "http://www.polarsys.org/capella/core/la/{VERSION}",
    "org.polarsys.capella.core.data.la",
    model.CORE_VIEWPOINT,
    "6.0.0",
)
LIBRARIES = model.Namespace(
    "http://www.polarsys.org/capella/common/libraries/{VERSION}",
    "libraries",
    model.CORE_VIEWPOINT,
    "6.0.0",
)
OA = model.Namespace(
    "http://www.polarsys.org/capella/core/oa/{VERSION}",
    "org.polarsys.capella.core.data.oa",
    model.CORE_VIEWPOINT,
    "6.0.0",
)
PA = model.Namespace(
    "http://www.polarsys.org/capella/core/pa/{VERSION}",
    "org.polarsys.capella.core.data.pa",
    model.CORE_VIEWPOINT,
    "6.0.0",
)
PA_DEPLOYMENT = model.Namespace(
    "http://www.polarsys.org/capella/core/pa/deployment/{VERSION}",
    "org.polarsys.capella.core.data.pa.deployment",
    model.CORE_VIEWPOINT,
    "6.0.0",
)
SA = model.Namespace(
    "http://www.polarsys.org/capella/core/ctx/{VERSION}",
    "org.polarsys.capella.core.data.ctx",
    model.CORE_VIEWPOINT,
    "6.0.0",
)
