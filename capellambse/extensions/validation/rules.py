# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from capellambse.model import common as c
from capellambse.model.layers import ctx as sa

from . import _validate

# __all__ = ["has_non_empty_description"]


@_validate.register_rule(
    category=_validate.Category.REQUIRED,
    types=[sa.SystemComponent, sa.SystemFunction, sa.Capability],
    id="Rule-001",
    name="Object has a description or summary",
    rationale=(
        "Object name may be insufficient to describe the object. "
        "Name also may use acronyms, abbreviations or context "
        "references that may not be known to the reader. In simple "
        "cases it might be sufficient to populate the summary field, "
        "however when the object is more complex, the description "
        "field should be used."
    ),
    actions=["Fill the description and/or summary text fields."],
)
def has_non_empty_description_or_summary(obj: c.GenericElement) -> bool:
    return bool(obj.description) or bool(obj.summary)


@_validate.register_rule(
    category=_validate.Category.REQUIRED,
    types=[sa.Capability],
    id="Rule-002",
    name="Capability involves an Actor",
    rationale="Every Capability shall involve an Actor",
    actions=["Add an involvement with an actor to the Capability."],
)
def capability_involves_an_actor(obj: sa.Capability) -> bool:
    return len(obj.involved_components.by_is_actor(True)) > 0


@_validate.register_rule(
    category=_validate.Category.REQUIRED,
    types=[sa.Capability],
    id="Rule-003",
    name="Capability involves an actor function",
    rationale=(
        "Every Capability shall have an involvement to an actor function."
    ),
    actions=["Add an involvement with an actor function to the Capability."],
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
    name="Capability involves a SystemFunction",
    rationale=(
        "Every Capability shall have an involvement to a SystemFunction."
    ),
    actions=["Add an involvement with a SystemFunction to the Capability."],
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
    name="IS- and SHOULD-entity-involvements match",
    rationale="This should be a thing.",
    actions=["Make more involvements."],
)
def is_and_should_entity_involvements_match(obj: sa.Capability) -> bool:
    is_involvements = {x.owner.uuid for x in obj.involved_functions if x.owner}
    should_involvements = {x.uuid for x in obj.involved_components}
    return is_involvements == should_involvements


@_validate.register_rule(
    category=_validate.Category.RECOMMENDED,
    types=[sa.Capability],
    id="Rule-006",
    name="Capability has precondition",
    rationale="A Capability shall define its precondition.",
    actions=["Fill in the precondition of the Capability."],
)
def has_precondition(obj) -> bool:
    return obj.precondition is not None


@_validate.register_rule(
    category=_validate.Category.RECOMMENDED,
    types=[sa.Capability],
    id="Rule-007",
    name="Capability has postcondition",
    rationale="A Capability shall define its postcondition.",
    actions=["Fill in the postcondition of the Capability."],
)
def has_postcondition(obj):
    return obj.postcondition is not None


try:
    import spacy  # type: ignore
except ImportError:

    @_validate.register_rule(
        category=_validate.Category.SUGGESTED,
        types=[sa.Capability],
        id="Rule-007",
        name="Spacy failed to load",
        rationale="Cannot apply this rule.",
        actions=["Install spacy and download the natural language model."],
    )
    def behavior_name_follows_verb_noun_pattern(obj) -> bool:
        del obj
        return False

else:
    try:
        NLP = spacy.load("en_core_web_lg")
    except OSError:

        @_validate.register_rule(
            category=_validate.Category.SUGGESTED,
            types=[sa.Capability],
            id="Rule-007",
            name="Spacy failed to load",
            rationale="Cannot apply this rule.",
            actions=["Download the natural language model."],
        )
        def behavior_name_follows_verb_noun_pattern(obj) -> bool:
            del obj
            return False

    else:

        @_validate.register_rule(
            category=_validate.Category.SUGGESTED,
            types=[sa.Capability],
            id="Rule-007",
            name="Behavior name follows verb-noun pattern",
            rationale="This makes things more consistent.",
            actions=[
                (
                    "Change the name of the behavior to follow "
                    'the pattern of "VERB NOUN",'
                    ' for example "brew coffee".'
                )
            ],
        )
        def behavior_name_follows_verb_noun_pattern(obj) -> bool:
            if len(obj.name) < 1:
                return False
            doc = NLP(obj.name)
            if len(doc) < 2:
                return False
            if doc[0].pos_ != "VERB":
                return False
            if not "NOUN" in [x.pos_ for x in doc[1:]]:
                return False
            return True
