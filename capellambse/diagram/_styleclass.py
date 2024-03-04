# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Functions for receiving the styleclass from a given model object."""
from __future__ import annotations

__all__ = ["get_styleclass"]

import collections.abc as cabc
import re

from capellambse import metamodel as M
from capellambse import model as m


def get_styleclass(obj: m.ModelElement) -> str:
    """Return the styleclass for an individual model object.

    Parameters
    ----------
    obj
        An object received from querying the High-Level API.

    Returns
    -------
    str
        A string used for styling and decorating given ``obj`` in a
        diagram representation.
    """
    styleclass_factory = _STYLECLASSES.get(type(obj).__name__, _default)
    return styleclass_factory(obj)


def _default(obj: m.ModelElement) -> str:
    return type(obj).__name__


def _association(obj: m.ModelElement) -> str:
    assert isinstance(obj, M.information.Association)
    default_kind = kind = "ASSOCIATION"
    assert isinstance(obj.roles, m.ElementList)
    for member in obj.roles:
        if member.kind != default_kind:
            kind = member.kind.name
    return kind.capitalize()


def _component_port(obj: m.ModelElement) -> str:
    assert isinstance(obj, M.fa.ComponentPort)
    if obj.direction is None:
        return "CP_UNSET"
    return f"CP_{obj.direction}"


def _control_node(obj: m.ModelElement) -> str:
    assert isinstance(obj, M.fa.ControlNode)
    return "".join((obj.kind.name.capitalize(), _default(obj)))


def _functional_chain_involvement(obj: m.ModelElement) -> str:
    assert isinstance(
        obj,
        (
            M.fa.FunctionalChainInvolvementLink,
            M.fa.FunctionalChainInvolvementFunction,
        ),
    )
    styleclass = _default(obj)
    if isinstance(obj.parent, M.oa.OperationalProcess):
        return styleclass.replace("Functional", "Operational")
    return styleclass


def _functional_exchange(obj: m.ModelElement) -> str:
    assert isinstance(obj, M.fa.FunctionalExchange)
    styleclass = _default(obj)
    if get_styleclass(obj.target) == "OperationalActivity":
        return styleclass.replace("Functional", "Operational")
    return styleclass


def _generic_component(obj: m.ModelElement) -> str:
    assert isinstance(obj, M.cs.Component)
    styleclass = _default(obj)
    return "".join(
        (
            styleclass[: -len("Component")],
            "Human" * obj.is_human,
            ("Component", "Actor")[obj.is_actor],
        )
    )


def _physical_component(obj: m.ModelElement) -> str:
    assert isinstance(obj, M.pa.PhysicalComponent)
    styleclass = _generic_component(obj)
    ptrn = re.compile("^(.*)(Component|Actor)$")
    nature = [obj.nature.name, ""][obj.nature.name == "UNSET"]
    return ptrn.sub(rf"\1{nature.capitalize()}\2", styleclass)


def _part(obj: m.ModelElement) -> str:
    assert isinstance(obj, M.cs.Part)
    assert not isinstance(obj.type, m.ElementList)
    xclass = _default(obj.type)
    if xclass == "PhysicalComponent":
        return _physical_component(obj)
    elif xclass == "Entity":
        return xclass
    return _generic_component(obj.type)


def _port_allocation(obj: m.ModelElement) -> str:
    assert isinstance(obj, M.information.PortAllocation)
    styleclasses = set(
        get_styleclass(p)
        for p in (obj.source, obj.target)
        if not isinstance(p, (M.fa.ComponentPort, m.ElementList))
    )
    return f"{'_'.join(sorted(styleclasses))}Allocation"


def _region(obj: m.ModelElement) -> str:
    assert isinstance(obj, M.capellacommon.Region)
    parent_xclass = _default(obj.parent)
    return f"{parent_xclass}{_default(obj)}"


def _property(obj: m.ModelElement) -> str:
    assert isinstance(obj, M.information.Property)
    return obj.kind.name.capitalize()


def _class(obj: m.ModelElement) -> str:
    assert isinstance(obj, M.information.Class)
    return "Primitive" * obj.is_primitive + "Class"


_STYLECLASSES: dict[str, cabc.Callable[[m.ModelElement], str]] = {
    "Association": _association,
    "CapellaIncomingRelation": lambda _: "RequirementRelation",
    "CapellaOutgoingRelation": lambda _: "RequirementRelation",
    "Class": _class,
    "ComponentPort": _component_port,
    "ControlNode": _control_node,
    "FunctionalChainInvolvementFunction": _functional_chain_involvement,
    "FunctionalChainInvolvementLink": _functional_chain_involvement,
    "FunctionalExchange": _functional_exchange,
    "FunctionInputPort": lambda _: "FIP",
    "FunctionOutputPort": lambda _: "FOP",
    "LogicalComponent": _generic_component,
    "Part": _part,
    "PhysicalComponent": _physical_component,
    "PhysicalPort": lambda _: "PP",
    "Property": _property,
    "PortAllocation": _port_allocation,
    "Region": _region,
    "SystemComponent": _generic_component,
}
