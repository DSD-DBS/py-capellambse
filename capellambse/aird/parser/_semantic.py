# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Parser entry point for semantic elements.

Semantic elements have a ``<target>`` which references the represented
object in the ``.melodymodeller`` or ``.melodyfragment`` file.  The
melody file is the source of truth for all attributes that are not
specific to a single diagram, i.e. basically everything except position,
size and styling.
"""
from __future__ import annotations

import collections.abc as cabc
import logging
import typing as t

from lxml import etree

import capellambse  # pylint: disable=unused-import  # used in typing
from capellambse import aird

from . import _box_factories
from . import _common as c
from . import _edge_factories

LOGGER = logging.getLogger(__name__)
NO_RENDER_XMT = frozenset(
    {
        "diagram:DNodeListElement",
    }
)


def from_xml(ebd: c.ElementBuilder) -> aird.DiagramElement:
    """Deserialize a semantic element."""
    uid = ebd.data_element.attrib.get("element")
    if uid is None:
        raise c.SkipObject()

    diag_element = ebd.melodyloader.follow_link(ebd.data_element, uid)
    if diag_element.get(c.ATT_XMT) in NO_RENDER_XMT:
        raise c.SkipObject()

    target = next(diag_element.iterchildren("target"), None)
    if target is None:
        raise c.SkipObject()
    needed_target_attrib = frozenset({"href", c.ATT_XMT})
    actual_target_attrib = set(target.attrib) & needed_target_attrib
    if actual_target_attrib != needed_target_attrib:
        LOGGER.error(
            "Missing required attributes %s from target of %r",
            ", ".join(actual_target_attrib ^ needed_target_attrib),
            uid,
        )
        raise c.SkipObject()

    styleclass = target.attrib[c.ATT_XMT]
    try:
        styleclass = styleclass.split(":")[1]
    except IndexError:
        raise ValueError(f"Invalid target type {styleclass}") from None

    try:
        styleclass, drawtype = STYLECLASS_LOOKUP[styleclass]
    except KeyError:
        drawtype = _GENERIC_FACTORIES

    sem_elms = list(diag_element.iterchildren("semanticElements"))
    melodyobjs: list[etree._Element] = []
    for sem_elm in sem_elms:
        sem_href = sem_elm.attrib["href"]
        try:
            sem_obj = ebd.melodyloader.follow_link(sem_elm, sem_href)
        except KeyError:
            LOGGER.warning(
                "Referenced semantic element %r does not exist", sem_href
            )
        melodyobjs.append(sem_obj)
    if not melodyobjs:
        melodyobjs = [
            ebd.melodyloader.follow_link(target, target.attrib["href"])
        ]
    elif melodyobjs[0] is None:
        raise c.SkipObject()

    seb = c.SemanticElementBuilder(
        target_diagram=ebd.target_diagram,
        diagram_tree=ebd.diagram_tree,
        data_element=ebd.data_element,
        melodyloader=ebd.melodyloader,
        fragment=ebd.fragment,
        styleclass=styleclass,
        diag_element=diag_element,
        melodyobjs=melodyobjs,
    )
    return drawtype(seb)


class FactorySelector:
    """Selects a factory based on whether it's for a box or an edge."""

    __slots__ = ("box", "edge")

    def __init__(
        self,
        box: cabc.Callable[[c.SemanticElementBuilder], aird.Box],
        edge: cabc.Callable[[c.SemanticElementBuilder], aird.Edge],
    ) -> None:
        self.box = box
        self.edge = edge

    def __call__(self, seb: c.SemanticElementBuilder) -> aird.DiagramElement:
        factory: cabc.Callable[[c.SemanticElementBuilder], aird.DiagramElement]
        if seb.data_element.tag == "children":
            factory = self.box
        elif seb.data_element.tag == "edges":
            factory = self.edge
        else:
            raise ValueError(f"Unknown element type {seb.data_element.tag}")
        return factory(seb)


_GENERIC_FACTORIES = FactorySelector(
    _box_factories.generic_factory, _edge_factories.generic_factory
)
#: This dictionary implements a mapping between the Capella internal
#: types and the types used in the drawing interface protocol.
#: The dictionary keys are the Capella types, the values are a tuple of
#: the style class and the specific factory function.
#:
#: If a key is not found in this dictionary, its value is assumed to be
#: a tuple of its key and the ``_GENERIC_FACTORIES``.
SemanticDeserializer = t.Callable[
    [c.SemanticElementBuilder], "capellambse.aird.DiagramElement"
]
STYLECLASS_LOOKUP: dict[str, tuple[str | None, SemanticDeserializer]]
STYLECLASS_LOOKUP = {
    "AbstractCapabilityInclude": (
        "AbstractCapabilityInclude",
        _edge_factories.include_extend_factory,
    ),
    "AbstractCapabilityExtend": (
        "AbstractCapabilityExtend",
        _edge_factories.include_extend_factory,
    ),
    "Association": (
        "Association",
        _edge_factories.association_factory,
    ),
    "CapellaIncomingRelation": (
        "RequirementRelation",
        _edge_factories.req_relation_factory,
    ),
    "CapellaOutgoingRelation": (
        "RequirementRelation",
        _edge_factories.req_relation_factory,
    ),
    "ChoicePseudoState": (
        "ChoicePseudoState",
        _box_factories.pseudo_symbol_factory,
    ),
    "Class": ("Class", _box_factories.class_factory),
    "ComponentPort": ("CP", _box_factories.component_port_factory),
    "Constraint": (
        "Constraint",
        FactorySelector(
            _box_factories.constraint_factory,
            _edge_factories.constraint_factory,
        ),
    ),
    "ControlNode": ("ControlNode", _box_factories.control_node_factory),
    "ExchangeItemElement": (
        "ExchangeItemElement",
        _edge_factories.eie_factory,
    ),
    "Enumeration": ("Enumeration", _box_factories.enumeration_factory),
    "EnumerationLiteral": (
        None,
        c.SkipObject.raise_,
    ),  # handled as part of `Enumeration`
    "Entity": (
        "Entity",
        FactorySelector(
            _box_factories.generic_factory, _edge_factories.labelless_factory
        ),
    ),
    "FunctionInputPort": ("FIP", _GENERIC_FACTORIES),
    "FunctionOutputPort": ("FOP", _GENERIC_FACTORIES),
    "ForkPseudoState": (
        "ForkPseudoState",
        _box_factories.pseudo_symbol_factory,
    ),
    "Mode": ("Mode", _box_factories.statemode_factory),
    "State": ("State", _box_factories.statemode_factory),
    "StateTransition": (
        "StateTransition",
        _edge_factories.state_transition_factory,
    ),
    "SystemComponent": ("SystemComponent", _box_factories.part_factory),
    "OperationalActor": (
        "OperationalActor",
        FactorySelector(
            _box_factories.generic_factory, _edge_factories.labelless_factory
        ),
    ),
    "Part": (None, _box_factories.part_factory),
    "Region": ("Region", _box_factories.region_factory),
    "PortAllocation": (
        "PortAllocation",
        _edge_factories.port_allocation_factory,
    ),
    "Property": (None, c.SkipObject.raise_),  # Handled as part of `Class`
    "Service": (None, c.SkipObject.raise_),  # Handled as part of `Class`
    "SequenceLink": ("SequenceLink", _edge_factories.sequence_link_factory),
    "PhysicalPort": ("PP", _GENERIC_FACTORIES),
    "Requirement": ("Requirement", _box_factories.requirements_box_factory),
    # FunctionalChains
    "FunctionalChainInvolvementFunction": (
        "FunctionalChainInvolvementFunction",
        _box_factories.fcif_factory,
    ),
    "FunctionalChainInvolvementLink": (
        "FunctionalChainInvolvementLink",
        _edge_factories.fcil_factory,
    ),
    "FunctionalChainReference": (
        "FunctionalChainReference",
        _box_factories.generic_stacked_factory,
    ),
}
