# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import capellambse.model as m

from .. import capellacore, cs
from .. import namespaces as ns

NS = ns.PA_DEPLOYMENT


class AbstractPhysicalInstance(capellacore.CapellaElement, abstract=True):
    pass


class ComponentInstance(
    AbstractPhysicalInstance,
    cs.DeployableElement,
    cs.DeploymentTarget,
):
    abstract_physical_instances = m.Containment["AbstractPhysicalInstance"](
        "ownedAbstractPhysicalInstances", (NS, "AbstractPhysicalInstance")
    )
    instance_deployment_links = m.Containment["InstanceDeploymentLink"](
        "ownedInstanceDeploymentLinks", (NS, "InstanceDeploymentLink")
    )
    type = m.Association["PhysicalComponent"](
        (NS, "PhysicalComponent"), "type"
    )


class ConnectionInstance(AbstractPhysicalInstance):
    connection_ends = m.Association["PortInstance"](
        (NS, "PortInstance"), "connectionEnds"
    )
    type = m.Association["fa.ComponentExchange"](
        (ns.FA, "ComponentExchange"), "type"
    )


class DeploymentAspect(capellacore.Structure):
    configurations = m.Containment["DeploymentConfiguration"](
        "ownedConfigurations", (NS, "DeploymentConfiguration")
    )
    deployment_aspects = m.Containment["DeploymentAspect"](
        "ownedDeploymentAspects", (NS, "DeploymentAspect")
    )


class DeploymentConfiguration(capellacore.NamedElement):
    deployment_links = m.Containment["cs.AbstractDeploymentLink"](
        "ownedDeploymentLinks", (ns.CS, "AbstractDeploymentLink")
    )
    physical_instances = m.Containment["AbstractPhysicalInstance"](
        "ownedPhysicalInstances", (NS, "AbstractPhysicalInstance")
    )


class InstanceDeploymentLink(cs.AbstractDeploymentLink):
    pass


class PartDeploymentLink(cs.AbstractDeploymentLink):
    pass


class PortInstance(AbstractPhysicalInstance):
    connections = m.Association["ConnectionInstance"](
        (NS, "ConnectionInstance"), "connections"
    )
    type = m.Association["fa.ComponentPort"]((ns.FA, "ComponentPort"), "type")


class TypeDeploymentLink(cs.AbstractDeploymentLink):
    pass


from .. import fa  # noqa: F401
from . import PhysicalComponent  # noqa: F401
