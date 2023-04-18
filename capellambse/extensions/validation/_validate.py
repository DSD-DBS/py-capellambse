# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

__all__ = [
    "Category",
    "ElementValidation",
    "ModelValidation",
    "register_rule",
    "Result",
    "Results",
    "Rule",
    "store_result",
    "Type",
    "Validation",
    "Validator",
]

import abc
import collections.abc as cabc
import dataclasses
import enum
import functools
import typing as t
from itertools import chain

from lxml import etree

import capellambse
from capellambse import helpers
from capellambse.model import common as c


class Category(enum.Flag):
    """A category for a rule."""

    REQUIRED = enum.auto()
    RECOMMENDED = enum.auto()
    SUGGESTED = enum.auto()


@dataclasses.dataclass
class Result:
    """A validation rule result."""

    uuid: helpers.UUIDString
    category: t.Literal[Category.REQUIRED] | t.Literal[
        Category.RECOMMENDED
    ] | t.Literal[Category.SUGGESTED]
    value: bool
    object: c.GenericElement


ElementType = t.TypeVar("ElementType", bound=c.GenericElement)

Validator = cabc.Callable[
    [ElementType], t.Union[bool, t.Literal["NotApplicable"]]
]  # | Callable [[Metric], Result]
Type = t.Union[
    str, type[c.GenericElement]
]  # | type[Metric] | type[AggregateMetric]
"""Type to be used in capellambse.model.MelodyModel.search(type) or metric
function the value of which will be validated by the rule."""


@dataclasses.dataclass(frozen=True, eq=True)
class Rule:
    """Common (generic) class representing any validation rule."""

    id: str
    name: str
    types: list[Type]
    rationale: str
    category: Category
    action: str
    applicable_to: str
    validator: Validator
    hyperlink_further_reading: str | None = None
    """The actual function will be assigned to this attribute, so that we do
    not need to have 100 classes for 100 rules."""

    def __call__(
        self, obj: c.GenericElement
    ) -> bool | t.Literal["NotApplicable"]:
        return self.validator(obj)

    def __hash__(self) -> int:
        return hash(self.id)


def _rule_attr_getter(val: str, attr: str) -> Rule | RuleList:
    all_rules = chain.from_iterable(VALIDATION_RULES.values())
    rules = [rule for rule in all_rules if getattr(rule, attr) == val]
    if len(rules) == 1:
        return rules[0]
    return RuleList(rules)


class RuleList(list[Rule]):
    """Stores all discovered validation rules."""

    def __init__(self, rules: cabc.Iterable[Rule] | None = None) -> None:
        super().__init__(rules or [])

    for attr in ("id", "name", "rationale", "action", "applicable_to"):
        method = functools.partial(_rule_attr_getter, attr=attr)
        method.__doc__ = f"Filter the validation rules by ``{attr}``"
        vars()[f"by_{attr}"] = method

    def by_category(self, category: Category | str) -> RuleList:
        """Filter the validation rules by ``category``."""
        if isinstance(category, str):
            category = Category[category]
        return VALIDATION_RULES[category]

    def by_type(self, type: type[c.GenericElement] | str) -> RuleList:
        if not isinstance(type, str):
            type = type.__name__

        rules = list[Rule]()
        for rule in chain.from_iterable(VALIDATION_RULES.values()):
            types = (
                t if isinstance(t, str) else t.__name__ for t in rule.types
            )
            if type in types:
                rules.append(rule)
        return RuleList(rules)


class Rules(dict[t.Union[Category, str], RuleList]):
    def __getitem__(self, key: Category | str) -> RuleList:
        if isinstance(key, str):
            key = Category[key]
        return super().__getitem__(key)


VALIDATION_RULES = Rules(
    {
        Category.REQUIRED: RuleList([]),
        Category.RECOMMENDED: RuleList([]),
        Category.SUGGESTED: RuleList([]),
    }
)


class Results(dict[Rule, dict[helpers.UUIDString, Result]]):
    """A validation rule result mapping."""

    def __getitem__(self, key: Rule | str) -> dict[helpers.UUIDString, Result]:
        if isinstance(key, str):
            for rule in self:
                if rule.id == key:
                    key = rule
                    break
            else:
                raise KeyError(f"No rule with id: {key!r} found")

        return super().__getitem__(key)

    def by_uuid(self, uuid: helpers.UUIDString) -> Results:
        """Filter the validation results by ``uuid``."""
        return Results(
            {
                rule: {uid: r for uid, r in res.items() if uid == uuid}
                for rule, res in self.items()
                if uuid in res
            }
        )

    def by_category(self, category: Category | str) -> Results:
        """Filter the validation results by ``category``."""
        if isinstance(category, str):
            category = Category[category]
        return Results(
            {
                rule: {
                    uid: r for uid, r in res.items() if r.category == category
                }
                for rule, res in self.items()
            }
        )

    def by_value(self, value: bool) -> Results:
        """Filter the validation results by ``value``."""
        return Results(
            {
                rule: {uid: r for uid, r in res.items() if r.value == value}
                for rule, res in self.items()
            }
        )

    def by_type(self, typ: str) -> Results:
        """Filter the validation results by ``typ``(e)."""
        return Results(
            {
                rule: dict(res.items())
                for rule, res in self.items()
                for rule_type in rule.types
                if rule_type.__name__ == typ  # type: ignore
            }
        )

    def get_passed_and_total(self, type=None) -> tuple[int, int]:
        """Return the number of passed and total validation rules."""
        passed = 0
        total = 0
        for _, results in self.items():
            for _, result in results.items():
                if not type:
                    total += 1
                    if result.value:
                        passed += 1
                else:
                    result_type = result.object.__class__.__name__
                    if type == result_type:
                        total += 1
                        if result.value:
                            passed += 1
        return passed, total

    def setdefault(
        self,
        key: t.Any,
        default: dict[helpers.UUIDString, Result] | None = None,
    ) -> dict[helpers.UUIDString, Result]:
        if not isinstance(default, dict):
            raise ValueError("Only a result dictionary is accepted")
        return super().setdefault(key, default)


VALIDATION_RESULTS = Results()


def register_rule(
    category: Category,
    types: list[Type],
    id: str,
    name: str,
    rationale: str,
    action: str,
    applicable_to: str,
    hyperlink_further_reading: str | None = None,
) -> cabc.Callable[[Validator], Validator]:
    """Register the validation rule.

    The validator along with the object to validate which will be used
    to feed it with inputs in validate()
    """

    def rule_decorator(rule: Validator) -> Validator:
        rule = Rule(
            id,
            name,
            types,
            rationale,
            category,
            action,
            applicable_to,
            rule,
            hyperlink_further_reading,
        )
        VALIDATION_RULES[category].append(rule)
        return rule

    return rule_decorator


def store_result(rule: Rule, obj: c.GenericElement, result: Result) -> None:
    """Save a ``result`` for the given ``rule`` and ModelObject."""
    results = VALIDATION_RESULTS
    results.setdefault(rule, {}).setdefault(obj.uuid, result)


class Validation(metaclass=abc.ABCMeta):
    """Basic class for access to validation rules and results."""

    _model: capellambse.MelodyModel
    _element: c.GenericElement

    def __init__(self, **kw: t.Any) -> None:
        raise TypeError("Cannot create Validation object this way")

    @classmethod
    def from_model(
        cls, model: capellambse.MelodyModel, element: etree._Element
    ) -> Validation:
        """Create a Validation object for a MelodyModel or an element."""
        self = cls.__new__(cls)
        self._model = model
        self._element = c.GenericElement.from_model(model, element)
        return self


class ModelValidation(Validation):
    """Provides access to the model's validation rules and results."""

    @property
    def rules(self) -> Rules:
        """Return all registered validation rules."""
        return VALIDATION_RULES

    @property
    def results(self) -> Results:
        """Return all stored validation rule results."""
        return VALIDATION_RESULTS

    def validate(self, *, rule: Rule | str | None = None) -> Results:
        """Execute all registered validation rules and store results."""
        for category, obj_type_rules in self.rules.items():
            for _rule in obj_type_rules:
                for obj in self._model.search(*_rule.types):
                    if isinstance(rule, Rule) and rule != _rule:
                        continue
                    if isinstance(rule, str) and rule != _rule.id:
                        continue

                    if (value := _rule(obj)) != "NotApplicable":
                        result = Result(
                            uuid=obj.uuid,
                            category=category,  # type: ignore[arg-type]
                            value=value,
                            object=obj,
                        )
                        store_result(_rule, obj, result)
        return self.results


class ElementValidation(Validation):
    """Provides access to the model's validation rules and results."""

    @property
    def rules(self) -> Rules:
        """Return all registered validation rules for this ModelObject."""
        return Rules(
            {
                category: RuleList(
                    (
                        rule
                        for rule in rules
                        if type(self._element) in rule.types
                    )
                )
                for category, rules in VALIDATION_RULES.items()
            }
        )

    @property
    def results(self) -> Results:
        """Return the validation rule results for this ModelObject."""
        return VALIDATION_RESULTS.by_uuid(self._element.uuid)

    def validate(self, *, rule: Rule | str | None = None) -> Results:
        """Execute the rules and store results for this ModelObject."""
        for category, obj_type_rules in self.rules.items():
            for _rule in obj_type_rules:
                if type(self._element) not in _rule.types:
                    continue
                if isinstance(rule, Rule) and rule != _rule:
                    continue
                if isinstance(rule, str) and rule != _rule.id:
                    continue

                if value := _rule(self._element) != "NotApplicable":
                    result = Result(
                        uuid=self._element.uuid,
                        category=category,  # type: ignore[arg-type]
                        value=value,
                        object=self._element,
                    )
                    store_result(_rule, self._element, result)
        return self.results
