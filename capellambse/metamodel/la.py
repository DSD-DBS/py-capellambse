# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Tools for the Logical Architecture layer."""
from __future__ import annotations

import typing as t

from capellambse import model as m

from . import capellacommon, cs, fa, interaction
from . import namespaces as ns

if t.TYPE_CHECKING:
    from . import sa

NS = ns.LA


class LogicalArchitecturePkg(cs.BlockArchitecturePkg):
    architectures = m.Containment["LogicalArchitecture"](
        "ownedLogicalArchitectures", (NS, "LogicalArchitecture")
    )


class LogicalArchitecture(cs.ComponentArchitecture):
    """Provides access to the LogicalArchitecture layer of the model."""

    component_pkg = m.Single(
        m.Containment["LogicalComponentPkg"](
            "ownedLogicalComponentPkg", (NS, "LogicalComponentPkg")
        ),
        enforce="max",
    )
    realized_system_analysis = m.Single(
        m.Allocation["sa.SystemAnalysis"](
            (NS, "SystemAnalysisRealization"),
            (
                "ownedSystemAnalysisRealizations",
                "targetElement",
                "sourceElement",
            ),
            (ns.SA, "SystemAnalysis"),
        ),
        enforce="max",
    )
    root_function = m.Single(
        m.Shortcut["LogicalFunction"]("function_pkg.functions"),
        enforce="max",
    )

    function_pkg = m.Single(
        m.Containment["LogicalFunctionPkg"](
            "ownedFunctionPkg", (NS, "LogicalFunctionPkg")
        ),
        enforce="max",
    )
    capability_pkg = m.Single(
        m.Containment["CapabilityRealizationPkg"](
            "ownedAbstractCapabilityPkg", (NS, "CapabilityRealizationPkg")
        ),
        enforce="max",
    )

    @property
    def root_component(self) -> LogicalComponent:
        try:
            return next(
                i for i in self.component_pkg.component if not i.is_actor
            )
        except StopIteration:
            raise ValueError("No root component found") from None

    @property
    def all_functions(self) -> m.ElementList[LogicalFunction]:
        return self._model.search((NS, "LogicalFunction"), below=self)

    @property
    def all_capabilities(self) -> m.ElementList[CapabilityRealization]:
        return self._model.search((NS, "CapabilityRealization"), below=self)

    @property
    def all_components(self) -> m.ElementList[LogicalComponent]:
        return self._model.search(
            (NS, "LogicalComponent"), below=self
        ).by_is_actor(False)

    @property
    def all_actors(self) -> m.ElementList[LogicalComponent]:
        return self._model.search(
            (NS, "LogicalComponent"), below=self
        ).by_is_actor(True)

    @property
    def all_functional_chains(self) -> m.ElementList[fa.FunctionalChain]:
        return self._model.search((ns.FA, "FunctionalChain"), below=self)

    actor_exchanges = m.Shortcut["fa.ComponentExchange"](
        "component_pkg.exchanges"
    )

    @property
    def component_exchanges(self) -> m.ElementList[fa.ComponentExchange]:
        return self._model.search(
            (NS, "ComponentExchange"),
            below=self.component_pkg.components[0],
        )

    @property
    def all_function_exchanges(self) -> m.ElementList[fa.FunctionalExchange]:
        return self._model.search((ns.FA, "FunctionalExchange"), below=self)

    @property
    def all_component_exchanges(self) -> m.ElementList[fa.ComponentExchange]:
        return self._model.search((ns.FA, "ComponentExchange"), below=self)

    diagrams: Todo


class LogicalFunction(fa.AbstractFunction):
    """A logical function on the Logical Architecture layer."""

    packages = m.Containment["LogicalFunctionPkg"](
        "ownedLogicalFunctionPkgs", (NS, "LogicalFunctionPkg")
    )
    realized_functions = m.TypeFilter["sa.SystemFunction"](  # type: ignore[assignment]
        None, (ns.SA, "SystemFunction")
    )
    functions = m.TypeFilter["LogicalFunction"](  # type: ignore[assignment]
        None, (NS, "LogicalFunction")
    )
    owner = m.Single(
        m.Backref["LogicalComponent"](
            (NS, "LogicalComponent"), lookup="functions"
        ),
        enforce="max",
    )


class LogicalFunctionPkg(fa.FunctionPkg):
    """A logical function package."""

    functions = m.Containment["LogicalFunction"](
        "ownedLogicalFunctionPkgs", (NS, "LogicalFunction")
    )
    packages = m.Containment["LogicalFunctionPkg"](
        "ownedLogicalFunctionPkgs", (NS, "LogicalFunctionPkg")
    )


class LogicalComponent(
    cs.Component, capellacommon.CapabilityRealizationInvolvedElement
):
    """A logical component on the Logical Architecture layer."""

    components = m.Containment["LogicalComponent"](
        "ownedLogicalComponents", (NS, "LogicalComponent")
    )
    architectures = m.Containment["LogicalArchitecture"](
        "ownedLogicalArchitectures", (NS, "LogicalArchitecture")
    )
    packages = m.Containment["LogicalComponentPkg"](
        "ownedLogicalComponentPkgs", (NS, "LogicalComponentPkg")
    )
    allocated_functions = m.TypeFilter["LogicalFunction"](  # type: ignore[assignment]
        None, (ns.LA, "LogicalFunction")
    )
    realized_components = m.TypeFilter["sa.SystemComponent"](  # type: ignore[assignment]
        None, (ns.SA, "SystemComponent")
    )


class LogicalComponentPkg(cs.ComponentPkg):
    """A logical component package."""

    components = m.Containment["LogicalComponent"](
        "ownedLogicalComponents", (NS, "LogicalComponent")
    )
    packages = m.Containment["LogicalComponentPkg"](
        "ownedLogicalComponentPkgs", (NS, "LogicalComponentPkg")
    )


class CapabilityRealization(interaction.AbstractCapability):  # TODO
    """A capability realization."""


class CapabilityRealizationPkg(capellacommon.AbstractCapabilityPkg):
    """A capability package that can hold capabilities."""
