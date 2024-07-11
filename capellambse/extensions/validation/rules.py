# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import capellambse
from capellambse.extensions import validation
from capellambse.model import modeltypes
from capellambse.model.crosslayer import capellacommon as cc
from capellambse.model.crosslayer import fa
from capellambse.model.layers import ctx as sa
from capellambse.model.layers import la, oa, pa

from . import _validate
from ._validate import rule


@validation.virtual_type(sa.SystemComponent)
def SystemActor(cmp: sa.SystemComponent) -> bool:
    return cmp.is_actor


@validation.virtual_type(pa.PhysicalComponent)
def BehaviourPhysicalComponent(cmp: pa.PhysicalComponent) -> bool:
    return cmp.nature == modeltypes.PhysicalComponentNature.BEHAVIOR


@validation.virtual_type(cc.State)
def OperationalState(state: cc.State) -> bool:
    layer = _find_layer(state)
    return isinstance(layer, oa.OperationalAnalysis)


@validation.virtual_type(cc.State)
def SystemState(state: cc.State) -> bool:
    layer = _find_layer(state)
    return isinstance(layer, sa.SystemAnalysis)


@validation.virtual_type(cc.State)
def LogicalState(state: cc.State) -> bool:
    layer = _find_layer(state)
    return isinstance(layer, la.LogicalArchitecture)


@validation.virtual_type(cc.State)
def PhysicalState(state: cc.State) -> bool:
    layer = _find_layer(state)
    return isinstance(layer, pa.PhysicalArchitecture)


def _find_layer(
    obj,
) -> (
    oa.OperationalAnalysis
    | sa.SystemAnalysis
    | la.LogicalArchitecture
    | pa.PhysicalArchitecture
):
    parent = obj.parent
    while not isinstance(
        parent,
        (
            oa.OperationalAnalysis,
            sa.SystemAnalysis,
            la.LogicalArchitecture,
            pa.PhysicalArchitecture,
        ),
    ):
        parent = parent.parent
    return parent


# 00. Common
@rule(
    category=_validate.Category.RECOMMENDED,
    types=[
        sa.Capability,
        sa.SystemFunction,
        sa.SystemComponent,
        oa.Entity,
        oa.OperationalCapability,
        oa.OperationalActivity,
        la.LogicalFunction,
        la.LogicalComponent,
        pa.PhysicalFunction,
        pa.PhysicalComponent,
        cc.State,
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
    obj: capellambse.model.GenericElement,
) -> bool:
    return bool(obj.description) or bool(obj.summary)


@rule(
    category=_validate.Category.REQUIRED,
    types=[
        sa.Capability,
        oa.OperationalCapability,
    ],
    id="Rule-002",
    name="Capability involves an Entity / Actor",
    rationale=(
        "Each Capability serves a need and brings a benefit for at least one"
        " of the Actors/Entities. By involving an actor / entity in a"
        " Capability we explicitly name stakeholders behind the Capability."
    ),
    action="Add at least one involved Actor or Entity.",
)
def capability_involves_entity(obj: capellambse.model.GenericElement) -> bool:
    if isinstance(obj, oa.OperationalCapability):
        return bool(obj.involved_entities)
    return bool(obj.involved_components)


@rule(
    category=_validate.Category.RECOMMENDED,
    types=[
        sa.Capability,
        oa.OperationalCapability,
        la.CapabilityRealization,
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
def has_precondition(obj: capellambse.model.GenericElement) -> bool:
    return obj.precondition is not None


@rule(
    category=_validate.Category.RECOMMENDED,
    types=[
        sa.Capability,
        oa.OperationalCapability,
        la.CapabilityRealization,
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
    types=[fa.FunctionalExchange],
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
    obj: fa.FunctionalExchange,
) -> bool:
    if _find_layer(obj).name == "Physical Architecture":
        return bool(obj.allocating_component_exchange)
    return True


# 01. Operational Analysis
@rule(
    category=_validate.Category.REQUIRED,
    types=[oa.OperationalCapability],
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
    obj: oa.OperationalCapability,
) -> bool:
    actors = {
        activity.owner.uuid
        for activity in obj.involved_activities
        if activity.owner is not None
    }
    return len(actors) > 1


@rule(
    category=_validate.Category.REQUIRED,
    types=[oa.OperationalActivity],
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
    obj: oa.OperationalActivity,
) -> bool:
    return bool(obj.related_exchanges)


# 02. System Analysis
@rule(
    category=_validate.Category.REQUIRED,
    types=[sa.Capability],
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
def capability_involves_actor_and_system_function(obj: sa.Capability) -> bool:
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
    types=[sa.Capability],
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
def is_and_should_entity_involvements_match(obj: sa.Capability) -> bool:
    is_involvements = {x.owner.uuid for x in obj.involved_functions if x.owner}
    should_involvements = {x.uuid for x in obj.involved_components}
    return is_involvements == should_involvements


@rule(
    category=_validate.Category.REQUIRED,
    types=[sa.SystemFunction],
    id="SF-030",
    name="Function shall be allocated to the System or an Actor.",
    rationale=(
        "An unallocated Function can lead to ambiguity, as it's unclear which"
        " entity is responsible for its implementation. Allocating the"
        " Function to the System or an Actor will clarify ownership and ensure"
        " proper delivery within the overall system context."
    ),
    action="allocate Function to the System or an Actor, or delete it",
)
def function_is_allocated(obj: sa.SystemFunction) -> bool:
    return bool(obj.owner)


@rule(
    category=_validate.Category.RECOMMENDED,
    types=[sa.SystemFunction],
    id="SF-040",
    name="Function shall have at least one input or output",
    rationale=(
        "A Function without inputs or outputs may not effectively contribute"
        " to the overall model, as it would not interact with other functions."
    ),
    action="consider adding inputs and / or outputs to the Function.",
)
def function_has_inputs_and_outputs(obj: sa.SystemFunction) -> bool:
    return len(obj.inputs) > 0 or len(obj.outputs) > 0


@rule(
    category=_validate.Category.REQUIRED,
    types=SystemActor,
    id="SY-001",
    name="System has at least one Function allocated to it.",
    rationale="A System has functionalities and those have to be described.",
    action="Allocate at least one Function to the System",
)
def system_involves_function(sys: sa.SystemComponent) -> bool:
    return len(sys.allocated_functions) > 0


@rule(
    category=_validate.Category.RECOMMENDED,
    # FIXME Only apply to SystemFunctions that are not allocated to an Actor
    types=[sa.SystemFunction],
    id="SF-050",
    name=(
        "A System Function shall be connected to at least one System Actor"
        " through a Functional Exchange."
    ),
    rationale=(
        "A System Function is justified only if it provides some useful"
        " service directly to an System Actor. BUT: there are functions"
        " connected only to other functions, which then connect to actors. So"
        " the rule should read: A System Function shall be connected directly"
        " or indirectly (via other functions) to at least one System Actor"
        " through a Functional Exchange."
    ),
    action=(
        "Connect the System Function via a Functional Exchange to a System"
        " Actor or to another System Function which is (directly or"
        " indirectly) connected to a System Actor or delete the System"
        " Function."
    ),
)
def function_of_system_exchanges_with_actor(func: sa.SystemFunction) -> bool:
    using_actors = sum(
        ex.source.is_actor or ex.target.is_actor
        for ex in func.related_exchanges
    )
    return bool(using_actors)


@rule(
    category=_validate.Category.SUGGESTED,
    types=[fa.FunctionalExchange],
    id="SFE-020",
    name="Functional Exchange should have an allocated Exchange Item.",
    rationale=(
        "Allocating Exchange Items to Functional Exchanges clarifies the data,"
        " material, or energy being exchanged between functions, and allows"
        " for greater understanding and detailing of the exchanged elements."
    ),
    action="add an Exchange Item to the Functional Exchange",
)
def exchange_transmits_items(ex: fa.FunctionalExchange) -> bool:
    return len(ex.exchange_items) > 0


@rule(
    category=_validate.Category.REQUIRED,
    types=[sa.Capability],
    id="SC-200",
    name="System Capability should represent a specific behaviour",
    rationale=(
        "To ensure a System Capability is well-defined and concrete, it should"
        " be based on an actual behavior or use case with an appropriate level"
        " of detail. Work Instructions ARCH.052 'Create initial system"
        " exchange scenarios' or ARCH.053 'Create initial system functional"
        " chains' may help you getting there."
    ),
    action=(
        "Specify the behaviour of the System Capability by creating a system"
        " exchange scenarios or defining functional chains"
    ),
)
def capability_involves_functional_chain_or_scenario(
    cap: sa.Capability,
) -> bool:
    return len(cap.involved_chains) > 0 or len(cap.scenarios) > 0


@rule(
    category=_validate.Category.RECOMMENDED,
    types=[sa.SystemFunction],
    id="VK-001-XD",
    name="Function is connected to another Entity's function (System, Actor)",
    rationale=(
        "To keep system analysis solution-agnostic, it is important to ensure"
        " that System-level functions focus on stakeholder-facing interactions"
        " rather than functional decomposition within a component. This"
        " approach emphasizes component responsibilities towards other actors,"
        " fostering a better understanding of the system's intended behavior"
        " and facilitating alignment with stakeholder needs, while avoiding"
        " premature commitment to specific solutions."
    ),
    action=(
        "consider introducing interaction with another Entity (System, Actor),"
        " merging or removing this function"
    ),
)
def function_has_external_exchanges(obj: sa.SystemFunction) -> bool:
    owner = obj.owner
    all_exchanges = [
        ex for port in obj.inputs + obj.outputs for ex in port.exchanges
    ]
    neighbors = [
        ex.source.owner if ex.source.owner is not owner else ex.target.owner
        for ex in all_exchanges
        if ex.source.owner is not owner and ex.target.owner is not owner
    ]
    return len(neighbors) > 0
