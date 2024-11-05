# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import capellambse
import capellambse.metamodel as mm
import capellambse.model as m

from . import _validate
from ._validate import rule, virtual_type


@virtual_type(mm.sa.Capability)
def SystemCapability(_: mm.sa.Capability) -> bool:
    return True


@virtual_type(mm.sa.SystemComponent)
def SystemActor(cmp: mm.sa.SystemComponent) -> bool:
    return cmp.is_actor


@virtual_type(mm.sa.SystemComponent)
def SystemComponent(cmp: mm.sa.SystemComponent) -> bool:
    return not cmp.is_actor


@virtual_type(mm.pa.PhysicalComponent)
def BehaviourPhysicalComponent(cmp: mm.pa.PhysicalComponent) -> bool:
    return cmp.nature == mm.modeltypes.PhysicalComponentNature.BEHAVIOR


@virtual_type(mm.capellacommon.State)
def OperationalState(state: mm.capellacommon.State) -> bool:
    return isinstance(state.layer, mm.oa.OperationalAnalysis)


@virtual_type(mm.capellacommon.State)
def SystemState(state: mm.capellacommon.State) -> bool:
    return isinstance(state.layer, mm.sa.SystemAnalysis)


@virtual_type(mm.capellacommon.State)
def LogicalState(state: mm.capellacommon.State) -> bool:
    return isinstance(state.layer, mm.la.LogicalArchitecture)


@virtual_type(mm.capellacommon.State)
def PhysicalState(state: mm.capellacommon.State) -> bool:
    return isinstance(state.layer, mm.pa.PhysicalArchitecture)


@virtual_type(mm.fa.FunctionalExchange)
def PhysicalFunctionExchange(fex: mm.fa.FunctionalExchange) -> bool:
    return isinstance(fex.layer, mm.pa.PhysicalArchitecture)


# 00. Common
@rule(
    category=_validate.Category.RECOMMENDED,
    types=[
        mm.sa.Capability,
        mm.sa.SystemFunction,
        SystemActor,
        SystemComponent,
        mm.oa.Entity,
        mm.oa.OperationalCapability,
        mm.oa.OperationalActivity,
        mm.la.LogicalFunction,
        mm.la.LogicalComponent,
        mm.pa.PhysicalFunction,
        mm.pa.PhysicalComponent,
        mm.capellacommon.State,
    ],
    id="Rule-001",
    name="Object has a description or summary",
    rationale=(
        "A comprehensive description or summary for an object is essential to"
        " ensure a clear understanding of its purpose, function, and role"
        " within the system. Providing a concise, yet informative description"
        " fosters better collaboration among team members, reduces ambiguity,"
        " and facilitates efficient decision-making."
    ),
    action="fill the description and/or summary text fields",
)
def has_non_empty_description_or_summary(
    obj: capellambse.model.ModelElement,
) -> bool:
    return bool(obj.description) or bool(obj.summary)


@rule(
    category=_validate.Category.REQUIRED,
    types=[
        mm.sa.Capability,
        mm.oa.OperationalCapability,
    ],
    id="Rule-002",
    name="Capability involves an Entity / Actor",
    rationale=(
        "Each Capability serves a need and brings a benefit for at least one"
        " of the Actors/Entities. By involving an actor / entity in a"
        " Capability we explicitly name stakeholders behind the Capability."
    ),
    action=(
        "Add at least one involved Actor or Entity,"
        " or include the Capability in another one."
    ),
)
def capability_involves_entity(obj: capellambse.model.ModelElement) -> bool:
    if isinstance(obj, mm.oa.OperationalCapability):
        has_involvements = bool(obj.involved_entities)
    else:
        assert isinstance(obj, mm.sa.Capability)
        has_involvements = bool(obj.involved_components)
    return has_involvements or bool(obj.included_by)


@rule(
    category=_validate.Category.RECOMMENDED,
    types=[
        mm.sa.Capability,
        mm.oa.OperationalCapability,
        mm.la.CapabilityRealization,
        # The CapabilityRealization in the pa layer is also affected by this
        # rule but is not defined as pa.CapabilityRealization since its the
        # same class as la.CapabilityRealization
    ],
    id="Rule-004",
    name="Capability has a defined pre-condition",
    rationale=(
        "Defining a pre-condition for a Capability helps clarify the necessary"
        " state of the primary Actor before interacting with the System, which"
        " enables a better understanding of the context and ensures"
        " prerequisites are met for successful system performance within the"
        " scope of the Capability."
    ),
    action=(
        "Define a pre-condition for this Capability that describes the initial"
        " state or requirements of the primary Actor before interacting with"
        " the System, to provide clarity on the starting context for the"
        " Capability."
    ),
)
def has_precondition(obj: capellambse.model.ModelElement) -> bool:
    return obj.precondition is not None


@rule(
    category=_validate.Category.RECOMMENDED,
    types=[
        mm.sa.Capability,
        mm.oa.OperationalCapability,
        mm.la.CapabilityRealization,
    ],
    id="Rule-005",
    name="Capability has a defined post-condition",
    rationale=(
        "Defining a post-condition for a Capability helps establish the"
        " expected state of the primary Actor after interacting with the"
        " System, ensuring clear understanding of the desired outcome and"
        " enabling effective evaluation of system performance within the scope"
        " of the Capability."
    ),
    action=(
        "Define a post-condition for this Capability that describes the"
        " expected state or outcome for the primary Actor after interacting"
        " with the System, to ensure clear understanding of the desired"
        " results and enable effective evaluation of system performance."
    ),
)
def has_postcondition(obj):
    return obj.postcondition is not None


@rule(
    category=_validate.Category.REQUIRED,
    types=[PhysicalFunctionExchange],
    id="Rule-006",
    name=(
        "All Functional exchanges shall be allocated to at least one component"
        " exchange"
    ),
    rationale=(
        "Each functional exchange should be allocated to any one of the"
        " component exchange. Otherwise this implies that the information"
        " flow is not considered or apportioned in the architecture."
    ),
    action=(
        "Allocated the functional exchange to the appropriate component"
        " exchange"
    ),
)
def functional_exchange_allocated_to_component_exchange(
    obj: m.ModelElement,
) -> bool:
    return bool(obj.allocating_component_exchange)


@rule(
    category=_validate.Category.REQUIRED,
    types=[mm.sa.SystemFunction, mm.oa.OperationalActivity],
    id="Rule-011",
    name="A Behavior element shall be allocated to a structure element",
    rationale=(
        "An unallocated Behavior element implies that it is useless functionality"
        " or the modelling is incomplete."
    ),
    action="Allocate a Behavior Element to a Structure Element",
)
def behavior_element_allocated_to_structure_element(
    obj: m.ModelElement,
) -> bool:
    assert isinstance(obj, mm.sa.SystemFunction | mm.oa.OperationalActivity)
    return obj.owner is not None


# 01. Operational Analysis
@rule(
    category=_validate.Category.REQUIRED,
    types=[mm.oa.OperationalCapability],
    id="Rule-007",
    name=(
        "Capability involves at least two Activities from different"
        " entities/actors"
    ),
    rationale=(
        "An operational capability should have at least two operational"
        " activities in a sequence, performed by two different entity/actor to"
        " qualify it to be meaningful."
    ),
    action=(
        "involve two operational activities from two different entity/actor"
    ),
)
def capability_involves_two_activities_from_different_entities(
    obj: m.ModelElement,
) -> bool:
    actors = {
        activity.owner.uuid
        for activity in obj.involved_activities
        if activity.owner is not None
    }
    return len(actors) > 1


@rule(
    category=_validate.Category.REQUIRED,
    types=[mm.oa.OperationalActivity],
    id="Rule-008",
    name="Activity has at least one interaction with another activity",
    rationale=(
        "To have any effect in the context of the model, an Operational "
        " Activity needs to interact (i.e. receive inputs from and/or send "
        " outputs to) with the rest of the model, i.e. with other Operational "
        " Activities."
    ),
    action=(
        "Define an interaction for the operational activity with another"
        " activity"
    ),
)
def activity_has_interaction_with_another_activity(
    obj: m.ModelElement,
) -> bool:
    return bool(obj.related_exchanges)


# 02. System Analysis
@rule(
    category=_validate.Category.REQUIRED,
    types=[mm.sa.Capability],
    id="Rule-009",
    name=(
        "System capability involves at least one Actor Function and one"
        " System function"
    ),
    rationale=(
        "A well-defined Capability should involve at least one Actor Function"
        " and one system function. This helps understanding the functional"
        " contribution of an Actor in the scope of the Capability."
    ),
    action=(
        "involve at least one actor function and system function in the"
        " Capability"
    ),
)
def capability_involves_actor_and_system_function(
    obj: m.ModelElement,
) -> bool:
    actor_functions = [
        fnc
        for fnc in obj.involved_functions
        if fnc.owner and fnc.owner.is_actor
    ]
    system_functions = [
        fnc
        for fnc in obj.involved_functions
        if fnc.owner and not fnc.owner.is_actor
    ]
    return len(actor_functions) > 0 and len(system_functions) > 0


@rule(
    category=_validate.Category.REQUIRED,
    types=[mm.sa.Capability],
    id="Rule-010",
    name="IS- and SHOULD entity involvements match",
    rationale=(
        "Capability should involve both Actors and Functions, with Functions"
        " allocated to respective entities (Actor or System). A mismatch"
        " between these two lists might suggest that a function is linked to"
        " an uninvolved actor, or an actor is involved without having any"
        " associated functions for that capability. Ensuring proper alignment"
        " helps maintain logical consistency and efficiency in the system"
        " design."
    ),
    action=(
        "To correct the mismatch, review and update the Capability's involved"
        " Actors and Functions, ensuring each Actor contributes at least one"
        " Function, and each Function is allocated to an appropriate Actor or"
        " System"
    ),
)
def is_and_should_entity_involvements_match(obj: m.ModelElement) -> bool:
    is_involvements = {x.owner.uuid for x in obj.involved_functions if x.owner}
    should_involvements = {x.uuid for x in obj.involved_components}
    return is_involvements == should_involvements


@rule(
    category=_validate.Category.RECOMMENDED,
    types=[mm.sa.SystemFunction],
    id="SF-040",
    name="Function shall have at least one input or output",
    rationale=(
        "A Function without inputs or outputs may not effectively contribute"
        " to the overall model, as it would not interact with other functions."
    ),
    action="consider adding inputs and / or outputs to the Function.",
)
def function_has_inputs_and_outputs(obj: m.ModelElement) -> bool:
    return len(obj.inputs) > 0 or len(obj.outputs) > 0
