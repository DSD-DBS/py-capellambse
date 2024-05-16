# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import typing as t

from capellambse import modelv2 as m

from . import capellacore, cs
from . import namespaces as ns

if t.TYPE_CHECKING:
    from . import fa, pa

NS = ns.PA_DEPLOYMENT


class AbstractPhysicalInstance(capellacore.CapellaElement, abstract=True):
    pass


class ComponentInstance(
    AbstractPhysicalInstance, cs.DeployableElement, cs.DeploymentTarget
):
    owned_instances = m.Containment["AbstractPhysicalInstance"](
        "ownedAbstractPhysicalInstances", (NS, "AbstractPhysicalInstance")
    )
    ports = m.TypeFilter["PortInstance"](
        "owned_instances", (NS, "PortInstance")
    )
    deployment_links = m.Containment["InstanceDeploymentLink"](
        "ownedInstanceDeploymentLinks", (NS, "InstanceDeploymentLink")
    )
    type = m.Association["pa.PhysicalComponent"](
        "type", (ns.PA, "PhysicalComponent")
    )


class ConnectionInstance(AbstractPhysicalInstance):
    ends = m.Association["PortInstance"](
        "connectionEnds", (NS, "PortInstance")
    )
    type = m.Association["fa.ComponentExchange"](
        "type", (ns.FA, "ComponentExchange")
    )


class DeploymentAspect(capellacore.Structure):
    configurations = m.Containment["DeploymentConfiguration"](
        "ownedConfigurations", (NS, "DeploymentConfiguration")
    )
    aspects = m.Containment["DeploymentAspect"](
        "ownedDeploymentAspects", (NS, "DeploymentAspect")
    )


class DeploymentConfiguration(capellacore.NamedElement):
    links = m.Containment["cs.AbstractDeploymentLink"](
        "ownedDeploymentLinks", (ns.CS, "AbstractDeploymentLink")
    )
    instances = m.Containment["AbstractPhysicalInstance"](
        "ownedPhysicalInstances", (NS, "AbstractPhysicalInstance")
    )


class InstanceDeploymentLink(cs.AbstractDeploymentLink):
    pass


class PartDeploymentLink(cs.AbstractDeploymentLink):
    pass


class PortInstance(AbstractPhysicalInstance):
    connections = m.Association["ConnectionInstance"](
        "connections", (NS, "ConnectionInstance")
    )
    component = m.Single["ComponentInstance"](
        m.Backref((NS, "ComponentInstance"), lookup="ports"),
        enforce="max",
    )
    type = m.Association["fa.ComponentPort"]("type", (ns.FA, "ComponentPort"))


class TypeDeploymentLink(cs.AbstractDeploymentLink):
    pass
