# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Functions for receiving the styleclass from a given model object."""
from __future__ import annotations

__all__ = ["get_styleclass"]

import collections.abc as cabc
import re

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
    return type(obj).__name__


def _association(obj: model.ModelObject) -> str:
    assert isinstance(obj, model.information.Association)
    default_kind = kind = "ASSOCIATION"
    assert isinstance(obj.members, model.ElementList)
    for member in obj.members:
        if member.kind != default_kind:
            kind = member.kind
    return kind.capitalize()


def _component_port(obj: model.ModelObject) -> str:
    assert isinstance(obj, model.fa.ComponentPort)
    if obj.direction is None:
        return "CP_UNSET"
    return f"CP_{obj.direction}"


def _control_node(obj: model.ModelObject) -> str:
    assert isinstance(obj, model.fa.ControlNode)
    return "".join((obj.kind.name.capitalize(), _default(obj)))


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


def _generic_component(obj: model.ModelObject) -> str:
    assert isinstance(obj, model.cs.Component)
    styleclass = _default(obj)
    return "".join(
        (
            styleclass[: -len("Component")],
            "Human" * obj.is_human,
            ("Component", "Actor")[obj.is_actor],
        )
    )


def _physical_component(obj: model.ModelObject) -> str:
    assert isinstance(obj, model.pa.PhysicalComponent)
    styleclass = _generic_component(obj)
    ptrn = re.compile("^(.*)(Component|Actor)$")
    nature = obj.nature.name
    return ptrn.sub(rf"\1{nature.capitalize()}\2", styleclass)


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
    styleclasses = set(
        get_styleclass(p)
        for p in (obj.source, obj.target)
        if not isinstance(p, (model.fa.ComponentPort, model.ElementList))
    )
    return f"{'_'.join(sorted(styleclasses))}Allocation"


def _region(obj: model.ModelObject) -> str:
    assert isinstance(obj, model.capellacommon.Region)
    parent_xclass = _default(obj.parent)
    return f"{parent_xclass}{_default(obj)}"


_STYLECLASSES: dict[str, cabc.Callable[[model.ModelObject], str]] = {
    "Association": _association,
    "CapellaIncomingRelation": lambda _: "RequirementRelation",
    "CapellaOutgoingRelation": lambda _: "RequirementRelation",
    "ComponentPort": _component_port,
    "ControlNode": _control_node,
    "FunctionalChainInvolvementFunction": _functional_chain_involvement,
    "FunctionalChainInvolvementLink": _functional_chain_involvement,
    "FunctionInputPort": lambda _: "FIP",
    "FunctionOutputPort": lambda _: "FOP",
    "LogicalComponent": _generic_component,
    "Part": _part,
    "PhysicalComponent": _physical_component,
    "PhysicalPort": lambda _: "PP",
    "PortAllocation": _port_allocation,
    "Region": _region,
    "SystemComponent": _generic_component,
}
