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
import typing as t

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

Validator = cabc.Callable[[ElementType], bool]  # | Callable [[Metric], Result]
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
    actions: list[str]
    validator: Validator
    hyperlink_further_reading: str | None = None
    """The actual function will be assigned to this attribute, so that we do
    not need to have 100 classes for 100 rules."""

    def __call__(self, obj: c.GenericElement) -> bool:  # | Metric
        return self.validator(obj)

    def __hash__(self) -> int:
        return hash(self.id)


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


VALIDATION_RULES: dict[Category, dict[Type, list[Rule]]] = {
    Category.REQUIRED: {},
    Category.RECOMMENDED: {},
    Category.SUGGESTED: {},
}
VALIDATION_RESULTS = Results()


def register_rule(
    category: Category,
    types: list[Type],
    id: str,
    name: str,
    rationale: str,
    actions: list[str],
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
            actions,
            rule,
            hyperlink_further_reading,
        )
        for typ in types:
            VALIDATION_RULES[category].setdefault(typ, []).append(rule)
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
    def rules(self) -> dict[Category, dict[Type, list[Rule]]]:
        """Return all registered validation rules."""
        return VALIDATION_RULES

    @property
    def results(self) -> Results:
        """Return all stored validation rule results."""
        return VALIDATION_RESULTS

    def validate(self, *, rule: Rule | str | None = None) -> Results:
        """Execute all registered validation rules and store results."""
        for category, obj_type_rules in self.rules.items():
            for type, rules in obj_type_rules.items():
                for obj in self._model.search(type):
                    for _rule in rules:
                        if isinstance(rule, Rule) and rule != _rule:
                            continue
                        if isinstance(rule, str) and rule != _rule.id:
                            continue

                        result = Result(
                            uuid=obj.uuid,
                            category=category,
                            value=_rule(obj),
                            object=obj,
                        )
                        store_result(_rule, obj, result)
        return self.results


class ElementValidation(Validation):
    """Provides access to the model's validation rules and results."""

    @property
    def rules(self) -> dict[Category, dict[Type, list[Rule]]]:
        """Return all registered validation rules for this ModelObject."""
        return {
            category: {
                typ: rules
                for typ, rules in obj_type_rules.items()
                if typ == type(self._element)
            }
            for category, obj_type_rules in VALIDATION_RULES.items()
        }

    @property
    def results(self) -> Results:
        """Return the validation rule results for this ModelObject."""
        return VALIDATION_RESULTS.by_uuid(self._element.uuid)

    def validate(self, *, rule: Rule | str | None = None) -> Results:
        """Execute the rules and store results for this ModelObject."""
        for category, obj_type_rules in self.rules.items():
            for typ, rules in obj_type_rules.items():
                if typ != type(self._element):
                    continue
                for _rule in rules:
                    if isinstance(rule, Rule) and rule != _rule:
                        continue
                    if isinstance(rule, str) and rule != _rule.id:
                        continue

                    result = Result(
                        uuid=self._element.uuid,
                        category=category,
                        value=_rule(self._element),
                        object=self._element,
                    )
                    store_result(_rule, self._element, result)
        return self.results
