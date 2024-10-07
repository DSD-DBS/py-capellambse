# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Common namespace definitions for the Capella metamodel."""

import capellambse.model as m

MODELLINGCORE = m._obj.NS
METADATA = m._obj.NS_METADATA

ACTIVITY = m.Namespace(
    "http://www.polarsys.org/capella/common/activity/{VERSION}",
    "org.polarsys.capella.common.data.activity",
    m.CORE_VIEWPOINT,
    "7.0.0",
)
BEHAVIOR = m.Namespace(
    "http://www.polarsys.org/capella/common/behavior/{VERSION}",
    "org.polarsys.capella.common.data.behavior",
    m.CORE_VIEWPOINT,
    "7.0.0",
)
CAPELLACOMMON = m.Namespace(
    "http://www.polarsys.org/capella/core/common/{VERSION}",
    "org.polarsys.capella.core.data.capellacommon",
    m.CORE_VIEWPOINT,
    "7.0.0",
)
CAPELLACORE = m.Namespace(
    "http://www.polarsys.org/capella/core/core/{VERSION}",
    "org.polarsys.capella.core.data.capellacore",
    m.CORE_VIEWPOINT,
    "7.0.0",
)
CAPELLAMODELLER = m.Namespace(
    "http://www.polarsys.org/capella/core/modeller/{VERSION}",
    "org.polarsys.capella.core.data.capellamodeller",
    m.CORE_VIEWPOINT,
    "7.0.0",
)
CS = m.Namespace(
    "http://www.polarsys.org/capella/core/cs/{VERSION}",
    "org.polarsys.capella.core.data.cs",
    m.CORE_VIEWPOINT,
    "7.0.0",
)
EPBS = m.Namespace(
    "http://www.polarsys.org/capella/core/epbs/{VERSION}",
    "org.polarsys.capella.core.data.epbs",
    m.CORE_VIEWPOINT,
    "7.0.0",
)
FA = m.Namespace(
    "http://www.polarsys.org/capella/core/fa/{VERSION}",
    "org.polarsys.capella.core.data.fa",
    m.CORE_VIEWPOINT,
    "7.0.0",
)
INFORMATION = m.Namespace(
    "http://www.polarsys.org/capella/core/information/{VERSION}",
    "org.polarsys.capella.core.data.information",
    m.CORE_VIEWPOINT,
    "7.0.0",
)
INFORMATION_COMMUNICATION = m.Namespace(
    "http://www.polarsys.org/capella/core/information/communication/{VERSION}",
    "org.polarsys.capella.core.data.information.communication",
    m.CORE_VIEWPOINT,
    "7.0.0",
)
INFORMATION_DATATYPE = m.Namespace(
    "http://www.polarsys.org/capella/core/information/datatype/{VERSION}",
    "org.polarsys.capella.core.data.information.datatype",
    m.CORE_VIEWPOINT,
    "7.0.0",
)
INFORMATION_DATAVALUE = m.Namespace(
    "http://www.polarsys.org/capella/core/information/datavalue/{VERSION}",
    "org.polarsys.capella.core.data.information.datavalue",
    m.CORE_VIEWPOINT,
    "7.0.0",
)
INTERACTION = m.Namespace(
    "http://www.polarsys.org/capella/core/interaction/{VERSION}",
    "org.polarsys.capella.core.data.interaction",
    m.CORE_VIEWPOINT,
    "7.0.0",
)
LA = m.Namespace(
    "http://www.polarsys.org/capella/core/la/{VERSION}",
    "org.polarsys.capella.core.data.la",
    m.CORE_VIEWPOINT,
    "7.0.0",
)
LIBRARIES = m.Namespace(
    "http://www.polarsys.org/capella/common/libraries/{VERSION}",
    "libraries",
    m.CORE_VIEWPOINT,
    "7.0.0",
)
OA = m.Namespace(
    "http://www.polarsys.org/capella/core/oa/{VERSION}",
    "org.polarsys.capella.core.data.oa",
    m.CORE_VIEWPOINT,
    "7.0.0",
)
PA = m.Namespace(
    "http://www.polarsys.org/capella/core/pa/{VERSION}",
    "org.polarsys.capella.core.data.pa",
    m.CORE_VIEWPOINT,
    "7.0.0",
)
PA_DEPLOYMENT = m.Namespace(
    "http://www.polarsys.org/capella/core/pa/deployment/{VERSION}",
    "org.polarsys.capella.core.data.pa.deployment",
    m.CORE_VIEWPOINT,
    "7.0.0",
)
RE = m.Namespace(
    "http://www.polarsys.org/capella/common/re/{VERSION}",
    "re",
    m.CORE_VIEWPOINT,
    "7.0.0",
)
SA = m.Namespace(
    "http://www.polarsys.org/capella/core/ctx/{VERSION}",
    "org.polarsys.capella.core.data.ctx",
    m.CORE_VIEWPOINT,
    "7.0.0",
)
SHARED_MODEL = m.Namespace(
    "http://www.polarsys.org/capella/core/sharedmodel/{VERSION}",
    "org.polarsys.capella.core.data.sharedmodel",
    m.CORE_VIEWPOINT,
    "7.0.0",
)
