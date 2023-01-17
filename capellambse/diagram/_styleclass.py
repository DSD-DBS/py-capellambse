# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Functions for receiving the styleclass from a given ``ModelObject``."""
from __future__ import annotations

__all__ = ["get_styleclass"]

import collections.abc as cabc
import re
import typing as t

from .. import model
from ..model.crosslayer import capellacommon, cs, fa, information

if t.TYPE_CHECKING:
    from capellambse import ModelObject


def get_styleclass(obj: ModelObject) -> str:
    """Return the styleclass from an individual ``ModelObject``.

    Parameters
    ----------
    obj
        An object received from querying the High-Level API.

    Returns
    -------
    styleclass
        A string used for styling and decorating given ``obj`` in a
        diagram representation.
    """
    styleclass_factory = _STYLECLASSES.get(type(obj).__name__, _default)
    return styleclass_factory(obj)


def _default(obj: ModelObject) -> str:
    assert isinstance(obj, model.GenericElement)
    return obj.xtype.rsplit(":", maxsplit=1)[-1]


def _association(obj: ModelObject) -> str:
    assert isinstance(obj, information.Association)
    default_kind = kind = "ASSOCIATION"
    for member in obj.members:  # type: ignore[union-attr]
        if member.kind != default_kind:
            kind = member.kind
    return kind.capitalize()


def _component_port(obj: ModelObject) -> str:
    assert isinstance(obj, fa.ComponentPort)
    if obj.direction is None:
        return "CP_UNSET"
    return f"CP_{obj.direction}"


def _control_node(obj: ModelObject) -> str:
    assert isinstance(obj, fa.ControlNode)
    return "".join((obj.kind.name.capitalize(), _default(obj)))


def _functional_chain_involvement(obj: ModelObject) -> str:
    assert isinstance(
        obj,
        (
            fa.FunctionalChainInvolvementLink,
            fa.FunctionalChainInvolvementFunction,
        ),
    )
    styleclass = _default(obj)
    if _default(obj.parent) == "OperationalProcess":
        return styleclass.replace("Functional", "Operational")
    return styleclass


def _generic_component(obj: ModelObject) -> str:
    assert isinstance(obj, cs.Component)
    styleclass = _default(obj)
    return "".join(
        (
            styleclass[: -len("Component")],
            "Human" * obj.is_human,
            ("Component", "Actor")[obj.is_actor],
        )
    )


def _physical_component(obj: ModelObject) -> str:
    assert _default(obj) == "PhysicalComponent"
    styleclass = _generic_component(obj)
    ptrn = re.compile("^(.*)(Component|Actor)$")
    nature = obj.nature.name  # type: ignore[attr-defined]
    return ptrn.sub(rf"\1{nature.capitalize()}\2", styleclass)


def _part(obj: ModelObject) -> str:
    assert isinstance(obj, cs.Part)
    xclass = _default(obj.type)
    if xclass == "PhysicalComponent":
        return _physical_component(obj)
    elif xclass == "Entity":
        return _default(obj.type)
    return _generic_component(obj.type)


def _port_allocation(obj: ModelObject) -> str:
    assert isinstance(obj, information.PortAllocation)
    styleclasses = set(
        p for p in (obj.source, obj.target) if _default(p) != "ComponentPort"
    )
    return f"{'_'.join(sorted(styleclasses))}Allocation"


def _region(obj: ModelObject) -> str:
    assert isinstance(obj, capellacommon.Region)
    parent_xclass = _default(obj.parent)
    return f"{parent_xclass}{_default(obj)}"


_STYLECLASSES: dict[str, cabc.Callable[[ModelObject], str]] = {
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
