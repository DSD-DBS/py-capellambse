# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import typing as t

from capellambse.model import common as c
from capellambse.model.layers import ctx as sa

from . import _validate

# __all__ = ["has_non_empty_description"]


@_validate.register_rule(
    category=_validate.Category.REQUIRED,
    types=[sa.SystemComponent],
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
    applicable_to="SystemComponent where <i>is_actor</i> is set to True.",
)
def has_non_empty_description_or_summary(
    obj: c.GenericElement,
) -> bool | t.Literal["NotApplicable"]:
    if not obj.is_actor:  # Precondition
        return "NotApplicable"

    return bool(obj.description) or bool(obj.summary)  # Validation-Rule


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
    applicable_to="TODO",
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
    applicable_to="TODO",
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
    applicable_to="TODO",
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
    applicable_to="TODO",
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
    applicable_to="TODO",
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
    applicable_to="TODO",
)
def has_postcondition(obj):
    return obj.postcondition is not None


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
    applicable_to="TODO",
)
def behavior_name_follows_verb_noun_pattern(obj) -> bool:
    if NLP is None or len(obj.name) < 1:
        return False
    doc = NLP(obj.name)
    if len(doc) < 2:
        return False
    if doc[0].pos_ != "VERB":
        return False
    if not "NOUN" in [x.pos_ for x in doc[1:]]:
        return False
    return True


# TODO: figure how to ignore / exclude Root System Function
# if obj == model.la.root_component: ...
