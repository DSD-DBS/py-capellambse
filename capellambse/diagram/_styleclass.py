# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Functions for receiving the styleclass from a given model object."""
from __future__ import annotations

__all__ = ["get_styleclass"]

import collections.abc as cabc

from capellambse import model


def get_styleclass(obj: model.ModelObject) -> str:
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


def _default(obj: model.ModelObject) -> str:
    if isinstance(obj, model.GenericElement):
        return obj.xtype.split(":")[-1]
    return type(obj).__name__


def _association(obj: model.ModelObject) -> str:
    assert isinstance(obj, model.information.Association)
    default_kind = kind = "ASSOCIATION"
    assert isinstance(obj.roles, model.ElementList)
    for member in obj.roles:
        if member.kind != default_kind:
            kind = member.kind.name
    return kind.capitalize()


def _functional_chain_involvement(obj: model.ModelObject) -> str:
    assert isinstance(
        obj,
        (
            model.fa.FunctionalChainInvolvementLink,
            model.fa.FunctionalChainInvolvementFunction,
        ),
    )
    styleclass = _default(obj)
    if isinstance(obj.parent, model.oa.OperationalProcess):
        return styleclass.replace("Functional", "Operational")
    return styleclass


def _functional_exchange(obj: model.ModelObject) -> str:
    assert isinstance(obj, model.fa.FunctionalExchange)
    styleclass = _default(obj)
    if get_styleclass(obj.target) == "OperationalActivity":
        return styleclass.replace("Functional", "Operational")
    return styleclass


def _generic_component(obj: model.ModelObject, extra: str = "") -> str:
    assert isinstance(obj, model.cs.Component)
    styleclass = _default(obj)
    return "".join(
        (
            styleclass[: -len("Component")],
            "Human" * obj.is_human,
            extra,
            ("Component", "Actor")[obj.is_actor],
        )
    )


def _physical_component(obj: model.ModelObject) -> str:
    assert isinstance(obj, model.pa.PhysicalComponent)
    nature = (obj.nature.name, "")[obj.nature.name == "UNSET"]
    return _generic_component(obj, extra=nature.capitalize())


def _part(obj: model.ModelObject) -> str:
    assert isinstance(obj, model.cs.Part)
    assert not isinstance(obj.type, model.ElementList)
    xclass = _default(obj.type)
    if xclass == "PhysicalComponent":
        return _physical_component(obj)
    elif xclass == "Entity":
        return xclass
    return _generic_component(obj.type)


def _port_allocation(obj: model.ModelObject) -> str:
    assert isinstance(obj, model.information.PortAllocation)
    styleclasses = {
        get_styleclass(p)
        for p in (obj.source, obj.target)
        if not isinstance(p, (model.fa.ComponentPort, model.ElementList))
    }
    return f"{'_'.join(sorted(styleclasses))}Allocation"


_STYLECLASSES: dict[str, cabc.Callable[..., str]] = {
    "Association": _association,
    "CapellaIncomingRelation": lambda _: "RequirementRelation",
    "CapellaOutgoingRelation": lambda _: "RequirementRelation",
    "Class": lambda o: "Primitive" * o.is_primitive + "Class",
    "ComponentPort": lambda o: f"CP_{o.direction or 'UNSET'}",
    "ControlNode": lambda o: o.kind.name.capitalize() + _default(o),
    "Entity": lambda o: (
        ("Entity", "OperationalActor")[o.is_actor and o.is_human]
    ),
    "FunctionalChainInvolvementFunction": _functional_chain_involvement,
    "FunctionalChainInvolvementLink": _functional_chain_involvement,
    "FunctionalExchange": _functional_exchange,
    "FunctionInputPort": lambda _: "FIP",
    "FunctionOutputPort": lambda _: "FOP",
    "LogicalComponent": _generic_component,
    "Part": _part,
    "PhysicalComponent": _physical_component,
    "PhysicalPort": lambda _: "PP",
    "Property": lambda o: o.kind.name.capitalize(),
    "PortAllocation": _port_allocation,
    "Region": lambda o: _default(o.parent) + _default(o),
    "SystemComponent": _generic_component,
}
