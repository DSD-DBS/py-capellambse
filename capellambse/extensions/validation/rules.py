# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import re

from capellambse.extensions import validation
from capellambse.model.crosslayer import fa
from capellambse.model.layers import ctx as sa

from . import _validate


@validation.virtual_type(sa.SystemComponent)
def SystemActor(cmp: sa.SystemComponent) -> bool:
    return cmp.is_actor


@_validate.register_rule(
    category=_validate.Category.REQUIRED,
    types=sa.SystemComponent,
    id="Rule-001",
    name="Object has a description or summary",
    rationale=(
        "A comprehensive description or summary for an object is "
        "essential to ensure a clear understanding of its purpose, "
        "function, and role within the system. Providing a concise, "
        "yet informative description fosters better collaboration "
        "among team members, reduces ambiguity, and facilitates "
        "efficient decision-making."
    ),
    action="fill the description and/or summary text fields",
)
def has_non_empty_description_or_summary(
    obj: sa.SystemComponent,
) -> bool:
    return bool(obj.description) or bool(obj.summary)


@_validate.register_rule(
    category=_validate.Category.REQUIRED,
    types=[sa.Capability],
    id="Rule-002",
    name="Capability involves an Actor",
    rationale=(
        "By involving a primary actor and considering the supporting "
        "actors in a System Capability, the system design highlights "
        "the relationships between system elements and the roles they "
        "play in achieving the desired outcomes. This approach enables "
        "more effective communication among stakeholders, facilitates "
        "traceability, and fosters collaboration throughout the system "
        "development process."
    ),
    action=(
        "involve a primary Actor that would benefit from the "
        "Capability and any supporting Actors required for the "
        "desired outcome"
    ),
)
def capability_involves_an_actor(obj: sa.Capability) -> bool:
    return len(obj.involved_components.by_is_actor(True)) > 0


@_validate.register_rule(
    category=_validate.Category.REQUIRED,
    types=[sa.Capability],
    id="Rule-003",
    name="Capability involves at least one Actor Function",
    rationale=(
        "A well-defined Capability should involve at least one Actor "
        "Function. This helps understanding the functional contribution "
        "of an Actor in the scope of the Capability."
    ),
    action="involve an actor function in the Capability",
)
def capability_involves_an_actor_function(obj: sa.Capability) -> bool:
    owners = [
        True
        for fnc in obj.involved_functions
        if (fnc.owner and fnc.owner.is_actor)
    ]
    return len(owners) > 0


@_validate.register_rule(
    category=_validate.Category.REQUIRED,
    types=[sa.Capability],
    id="Rule-004",
    name="Capability involves at least one System Function",
    rationale=(
        "A well-defined Capability should involve at least one System "
        "Function. This helps understanding the functional contribution "
        "of the System in the scope of the Capability."
    ),
    action="involves a system function in the Capability",
)
def capability_involves_a_system_function(obj: sa.Capability) -> bool:
    owners = [
        True
        for fnc in obj.involved_functions
        if (fnc.owner and not fnc.owner.is_actor)
    ]
    return len(owners) > 0


@_validate.register_rule(
    category=_validate.Category.REQUIRED,
    types=[sa.Capability],
    id="Rule-005",
    name="IS- and SHOULD entity involvements match",
    rationale=(
        "Capability should involve both Actors and Functions, "
        "with Functions allocated to respective entities (Actor "
        "or System). A mismatch between these two lists might "
        "suggest that a function is linked to an uninvolved actor, "
        "or an actor is involved without having any associated "
        "functions for that capability. Ensuring proper alignment "
        "helps maintain logical consistency and efficiency in the "
        "system design."
    ),
    action=(
        "To correct the mismatch, review and update the "
        "Capability's involved Actors and Functions, ensuring each "
        "Actor contributes at least one Function, and each Function "
        "is allocated to an appropriate Actor or System"
    ),
)
def is_and_should_entity_involvements_match(obj: sa.Capability) -> bool:
    is_involvements = {x.owner.uuid for x in obj.involved_functions if x.owner}
    should_involvements = {x.uuid for x in obj.involved_components}
    return is_involvements == should_involvements


@_validate.register_rule(
    category=_validate.Category.RECOMMENDED,
    types=[sa.Capability],
    id="Rule-006",
    name="Capability has a defined pre-condition",
    rationale=(
        "Defining a pre-condition for a Capability helps clarify the "
        "necessary state of the primary Actor before interacting with "
        "the System, which enables a better understanding of the context "
        "and ensures prerequisites are met for successful system "
        "performance within the scope of the Capability."
    ),
    action=(
        "Define a pre-condition for this Capability that describes the "
        "initial state or requirements of the primary Actor before "
        "interacting with the System, to provide clarity on the "
        "starting context for the Capability."
    ),
)
def has_precondition(obj) -> bool:
    return obj.precondition is not None


@_validate.register_rule(
    category=_validate.Category.RECOMMENDED,
    types=[sa.Capability],
    id="Rule-007",
    name="Capability has a defined post-condition",
    rationale=(
        "Defining a post-condition for a Capability helps establish "
        "the expected state of the primary Actor after interacting "
        "with the System, ensuring clear understanding of the desired "
        "outcome and enabling effective evaluation of system performance "
        "within the scope of the Capability."
    ),
    action=(
        "Define a post-condition for this Capability that describes the "
        "expected state or outcome for the primary Actor after "
        "interacting with the System, to ensure clear understanding of "
        "the desired results and enable effective evaluation of system "
        "performance."
    ),
)
def has_postcondition(obj):
    return obj.postcondition is not None


@_validate.register_rule(
    category=_validate.Category.REQUIRED,
    types=[sa.SystemFunction],
    id="SF-030",
    name="Function shall be allocated to the System or an Actor.",
    rationale=(
        "An unallocated Function can lead to ambiguity, as it's unclear "
        "which entity is responsible for its implementation. Allocating the "
        "Function to the System or an Actor will clarify ownership and "
        "ensure proper delivery within the overall system context."
    ),
    action="allocate Function to the System or an Actor, or delete it",
)
def function_is_allocated(obj: sa.SystemFunction) -> bool:
    return bool(obj.owner)


# TODO: This rules requires a solution for sub-setting the SystemComponent
# (to those that are not actors)
@_validate.register_rule(
    category=_validate.Category.REQUIRED,
    types=SystemActor,
    id="SY-001",
    name="System has at least one Function allocated to it.",
    rationale="A System has functionalities and those have to be described.",
    action="Allocate at least one Function to the System",
)
def system_involves_function(sys: sa.SystemComponent) -> bool:
    return len(sys.allocated_functions) > 0


@_validate.register_rule(
    category=_validate.Category.REQUIRED,
    types=[sa.SystemFunction],
    id="SF-040",
    name="Function shall have at least one input or output",
    rationale=(
        "A Function without inputs or outputs may not effectively contribute "
        "to the overall model, as it would not interact with other functions."
    ),
    action="consider adding inputs and / or outputs to the Function.",
)
def function_has_inputs_and_outputs(obj: sa.SystemFunction) -> bool:
    return (
        len(obj.inputs) > 0 or len(obj.outputs) > 0
    )  # len is more explicit than "return func.inputs and func.outputs"


# TODO: This requires a solution for determining which of the SystemFunctions
#  are actually SystemFunctions (allocated to a SystemComponent that is not
# an Actor)
# @_validate.register_rule(
#     category=_validate.Category.RECOMMENDED,
#     type=ctx.SystemFunction,
#     id="SF-050",
#     name="A System Function shall be connected to at least one System Actor
#  through a Functional Exchange.",
#     rationale="A System Function is justified only if it provides some
# useful service directly to an System Actor. BUT: there are functions
#  connected only to other functions, \
#     which then connect to actors. So the rule should read: A System
#  Function shall be connected directly or indirectly (via other functions)
# to at least one System Actor through a Functional Exchange.",
#     actions=["Connect the System Function via a Functional Exchange to a
# System Actor or to another System Function which is (directly or
# indirectly) connected \
#     to a System Actor or delete the System Function."],
# )
# def function_of_system_exchanges_with_actor(func: ctx.SystemFunction)
# -> bool:
#     using_actors = sum(ex.source.is_actor or ex.target.is_actor for ex
# in func.related_exchanges)
#     return bool(using_actors)
# TODO: the above mentioned .condition/.filter attribute is needed here too,
# to constrain this rule to just functions allcoated to the system (and
# exclude those allocated to the actors)


@_validate.register_rule(
    category=_validate.Category.SUGGESTED,
    types=[fa.FunctionalExchange],
    id="SFE-020",
    name="Functional Exchange should have an allocated Exchange Item.",
    rationale=(
        "Allocating Exchange Items to Functional Exchanges clarifies the "
        "data, material, or energy being exchanged between functions, and "
        "allows for greater understanding and detailing of the exchanged "
        "elements."
    ),
    action="add an Exchange Item to the Functional Exchange",
)
def exchange_transmits_items(ex: fa.FunctionalExchange) -> bool:
    return len(ex.exchange_items) > 0


@_validate.register_rule(
    category=_validate.Category.REQUIRED,
    types=[sa.Capability],
    id="SC-200",
    name="System Capability should represent a specific behaviour",
    rationale=(
        "To ensure a System Capability is well-defined and concrete, it "
        "should be based on an actual behavior or use case with an "
        "appropriate level of detail. Work Instructions ARCH.052 "
        "'Create initial system exchange scenarios' or ARCH.053 'Create "
        "initial system functional chains' may help you getting there."
    ),
    action=(
        "Specify the behaviour of the System Capability by creating a system "
        "exchange scenarios or defining functional chains"
    ),
)
def capability_involves_functional_chain_or_scenario(
    cap: sa.Capability,
) -> bool:
    return len(cap.involved_chains) > 0 or len(cap.scenarios) > 0


@_validate.register_rule(
    category=_validate.Category.RECOMMENDED,
    types=[sa.SystemFunction],
    id="VK-001-XD",
    name="Function is connected to another Entity's function (System, Actor)",
    rationale=(
        "To keep system analysis solution-agnostic, it is important to ensure "
        "that System-level functions focus on stakeholder-facing interactions "
        "rather than functional decomposition within a component. This "
        "approach emphasizes component responsibilities towards other actors, "
        "fostering a better understanding of the system's intended behavior "
        "and facilitating alignment with stakeholder needs, while avoiding "
        "premature commitment to specific solutions."
    ),
    action=(
        "consider introducing interaction with another Entity "
        "(System, Actor), merging or removing this function"
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


# TODO: Spacy and the NLP model shall only load when the rule gets evaluated
#  by validate() call (lazy loading)
def try_import_spacy():
    try:
        import spacy  # type: ignore

        return spacy
    except ImportError:
        return None


def try_download_language_model(spacy):
    try:
        spacy.cli.download("en_core_web_lg")
    except Exception:
        pass


def try_load_language_model(spacy):
    nlp = None
    try:
        nlp = spacy.load("en_core_web_lg")
    except OSError:
        try_download_language_model(spacy)
        try:
            nlp = spacy.load("en_core_web_lg")
        except OSError:
            pass
    return nlp


SPACY = try_import_spacy()
NLP = try_load_language_model(SPACY) if SPACY else None

if SPACY is None:
    rule_name = "Can't check if behavior name follows verb-noun pattern"
    rule_actions = "Install spacy and download the natural language model."
elif NLP is None:
    rule_name = "Can't check if behavior name follows verb-noun pattern"
    rule_actions = "Download the natural language model."
else:
    rule_name = "Behavior name follows verb-noun pattern"
    rule_actions = (
        "change the object name to follow "
        'the pattern of "VERB NOUN",'
        ' for example "brew coffee"'
    )


@_validate.register_rule(
    category=_validate.Category.SUGGESTED,
    types=[sa.Capability, sa.SystemFunction],
    id="Rule-008",
    name=rule_name,
    rationale=(
        "Using the verb-noun pattern for naming behaviors promotes clarity, "
        "consistency, and effective communication across the system. Adhering "
        "to this convention simplifies understanding and management for all "
        "stakeholders. Please revise any non-compliant names to align with "
        "this proven practice."
    ),
    action=rule_actions,
)
def behavior_name_follows_verb_noun_pattern(obj) -> bool:
    text = re.sub(r"^\d+: ", "", obj.name)
    if NLP is None or len(text) < 1:
        return False
    doc = NLP(text)
    if len(doc) < 2:
        return False

    # Check if the first token is a verb
    if doc[0].pos_ != "VERB":
        return False

    # Skip any number of adjectives and adverbs following the verb
    i = 1
    while i < len(doc) and doc[i].pos_ in ("ADJ", "ADV"):
        i += 1

    # If there's a noun after the adjectives/adverbs, the pattern is valid
    if i < len(doc) and doc[i].pos_ in ("NOUN", "PROPN"):
        return True

    return False


# TODO: figure how to ignore / exclude Root System Function
# if obj == model.la.root_component: ...
