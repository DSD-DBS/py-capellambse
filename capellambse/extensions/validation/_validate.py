# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

__all__ = [
    "Category",
    "ElementValidation",
    "ModelValidation",
    "RealType",
    "Result",
    "Results",
    "Rule",
    "RuleList",
    "Rules",
    "Validation",
    "VirtualType",
    "register_rule",
    "store_result",
    "virtual_type",
]

import abc
import collections.abc as cabc
import dataclasses
import enum
import functools
import itertools
import logging
import typing as t

from lxml import etree

import capellambse
import capellambse.model.modeltypes as mt
from capellambse import helpers, model
from capellambse.model import common as c

LOGGER = logging.getLogger("capellambse.extensions.validation")
_T = t.TypeVar("_T", bound=t.Union[c.GenericElement, "VirtualType"])


@dataclasses.dataclass(frozen=True)
class VirtualType(t.Generic[_T]):
    name: str
    real_type: type[_T]
    filter: cabc.Callable[[_T], bool]

    def search(self, model: capellambse.MelodyModel) -> cabc.Iterable[_T]:
        for i in model.search(self.real_type):
            if self.filter(i):
                yield i


@dataclasses.dataclass(frozen=True)
class RealType(t.Generic[_T]):
    class_: type[_T]

    @property
    def name(self) -> str:
        return self.class_.__name__

    def search(self, model: capellambse.MelodyModel) -> cabc.Iterable[_T]:
        return model.search(self.class_)


class _VirtualTypesRegistry(cabc.Mapping[str, t.Union[VirtualType, RealType]]):
    def __init__(self) -> None:
        self.__registry: dict[str, VirtualType] = {}

    def __iter__(self) -> cabc.Iterator[str]:
        yield from self.__registry

    def __len__(self) -> int:
        return len(self.__registry)

    def __contains__(self, key: object) -> bool:
        return key in self.__registry

    def __getitem__(self, key: str) -> VirtualType | RealType:
        try:
            return self.__registry[key]
        except KeyError:
            pass

        _, class_ = c.resolve_handler(key)
        return RealType(class_)

    def register(self, vtype: VirtualType) -> None:
        if vtype.name in self:
            known = self.__registry[vtype.name]
            raise RuntimeError(f"Virtual type already known: {known}")
        self.__registry[vtype.name] = vtype


_types_registry = _VirtualTypesRegistry()


def virtual_type(
    real_type: str | type[_T],
) -> cabc.Callable[[cabc.Callable[[_T], bool]], VirtualType[_T]]:
    def decorate(func: cabc.Callable[[_T], bool]) -> VirtualType[_T]:
        nonlocal real_type
        if isinstance(real_type, str):
            _, real_type = c.resolve_handler(real_type)

        vtype = VirtualType(func.__name__, real_type, func)
        _types_registry.register(vtype)
        return vtype

    return decorate


@virtual_type(model.oa.OperationalActivity)
def OperationalActivity(obj):
    return obj.parent != obj._model.oa.activity_package


@virtual_type(model.ctx.SystemFunction)
def SystemFunction(obj):
    return obj.parent != obj._model.sa.function_package


@virtual_type(model.la.LogicalFunction)
def LogicalFunction(obj):
    return obj.parent != obj._model.la.function_package


@virtual_type(model.la.LogicalFunction)
def PhysicalFunction(obj):
    return obj.parent != obj._model.pa.function_package


class Category(mt._StringyEnumMixin, enum.Enum):
    """A category for a rule."""

    REQUIRED = enum.auto()
    RECOMMENDED = enum.auto()
    SUGGESTED = enum.auto()


@dataclasses.dataclass
class Result:
    """A validation rule result."""

    uuid: helpers.UUIDString
    category: Category
    value: bool
    object: c.GenericElement

    def __repr__(self) -> str:
        """Return the representation of a result."""
        obj_repr = self.object._short_repr_()
        return (
            f"Result(uuid={self.uuid!r}, category={self.category!r},"
            f" value={self.value!r}, object={obj_repr})"
        )


ElementType = t.TypeVar("ElementType", bound=c.GenericElement)


@dataclasses.dataclass(frozen=True)
class Rule(t.Generic[_T]):
    """Common (generic) class representing any validation rule."""

    id: str
    name: str
    types: list[str]
    rationale: str
    category: Category
    action: str
    validator: cabc.Callable[[_T], bool]
    """Returns True if the object passed this rule."""
    hyperlink_further_reading: str | None = None

    def find(self, model: capellambse.MelodyModel) -> cabc.Iterator[_T]:
        for i in self.types:
            yield from _types_registry[i].search(model)

    def __call__(self, obj: _T) -> bool:
        return self.validator(obj)

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.id == other
        return hash(self) == hash(other)


def _rule_attr_getter(val: str, attr: str) -> Rule | RuleList:
    all_rules = itertools.chain.from_iterable(VALIDATION_RULES.values())
    rules = [rule for rule in all_rules if getattr(rule, attr) == val]
    if len(rules) == 1:
        return rules[0]
    return RuleList(rules)


class RuleList(list[Rule]):
    """Stores validation rules."""

    def __init__(self, rules: cabc.Iterable[Rule] | None = None) -> None:
        super().__init__(rules or [])

    if t.TYPE_CHECKING:

        def __getattr__(self, key: str) -> cabc.Callable[..., RuleList]:
            ...

    for attr in ("id", "name", "rationale", "action"):
        method = functools.partial(_rule_attr_getter, attr=attr)
        method.__doc__ = f"Filter the validation rules by ``{attr}``"
        vars()[f"by_{attr}"] = method

    def by_category(self, category: Category | str) -> RuleList:
        """Filter the validation rules by ``category``."""
        return RuleList((rule for rule in self if rule.category == category))

    def by_type(self, type: type[c.GenericElement] | str) -> RuleList:
        """Filter the validation rules by ``type``."""
        if not isinstance(type, str):
            type = type.__name__
        return RuleList((rule for rule in self if type in rule.types))


class Rules(dict[Category, RuleList]):
    """Stores validation rules classified into categories."""

    def __getitem__(self, key: Category | str) -> RuleList:
        return super().__getitem__(t.cast(Category, key))

    def by_id(self, rid: str) -> Rule:
        """Filter the validation results by ``uuid``."""
        for rules in self.values():
            for rule in rules:
                if rule.id == rid:
                    return rule
        raise KeyError(f"No rule found with id: {rid!r}")

    def by_category(self, category: Category | str) -> RuleList:
        """Filter the validation results by ``category``."""
        if isinstance(category, str):
            category = Category[category]
        return self[category]

    def by_type(self, type: type[c.GenericElement] | str) -> Rules:
        """Filter the validation results by ``type``."""
        if not isinstance(type, str):
            type = type.__name__
        return Rules(
            {
                category: RuleList(
                    (rule for rule in rules if type in rule.types)
                )
                for category, rules in self.items()
                if rules
            }
        )


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
        return super().__getitem__(key)  # type: ignore[index]

    def by_uuid(self, uuid: helpers.UUIDString) -> dict[Rule, Result]:
        """Filter the validation results by ``uuid``."""
        return {rule: res[uuid] for rule, res in self.items() if uuid in res}

    def by_category(self, category: Category | str) -> Results:
        """Filter the validation results by ``category``."""
        return Results(
            {
                rule: {
                    uid: r
                    for uid, r in res.items()
                    if r.category == category and r
                }
                for rule, res in self.items()
            }
        )

    def by_value(self, value: bool) -> Results:
        """Filter the validation results by ``value``."""
        return Results(
            {
                rule: {
                    uid: r for uid, r in res.items() if r.value == value and r
                }
                for rule, res in self.items()
            }
        )

    def by_type(self, type: str) -> Results:
        """Filter the validation results by ``type``."""
        results = dict[Rule, dict[helpers.UUIDString, Result]]()
        for rule, res in self.items():
            if not res:
                continue

            for rule_type in rule.types:
                if rule_type != type:
                    continue

                results[rule] = res

        return Results(results)

    def setdefault(
        self,
        key: t.Any,
        default: dict[helpers.UUIDString, Result] | None = None,
    ) -> dict[helpers.UUIDString, Result]:
        if not isinstance(default, dict):
            raise ValueError("Only a result dictionary is accepted")
        return super().setdefault(key, default)


def register_rule(
    category: Category,
    types: (
        str
        | VirtualType[_T]
        | type[_T]
        | cabc.Iterable[str | VirtualType[_T] | type[_T]]
    ),
    id: str,
    name: str,
    rationale: str,
    action: str,
    hyperlink_further_reading: str | None = None,
) -> cabc.Callable[[cabc.Callable[[_T], bool]], cabc.Callable[[_T], bool]]:
    """Register the validation rule.

    The decorator registers the validation rule function (validator)
    along with the object type to be validated (type). The type is the
    object type the rule is applicable to. The type will be used to feed
    the validator with inputs (instances of type) during validation.
    """
    try:
        VALIDATION_RULES.by_id(id)
        LOGGER.warning(
            "Failed to register rule: %r with ID: %r. Rule ID already exists",
            name,
            id,
        )
        unique_check = False
    except KeyError:
        unique_check = True

    if not types:
        raise TypeError("No 'types' specified")
    if isinstance(types, type):
        type_names = [types.__name__]
    elif isinstance(types, (RealType, VirtualType)):
        type_names = [types.name]
    elif isinstance(types, str):
        type_names = [types]
    else:
        type_names = []
        for i in types:
            if isinstance(i, str):
                type_names.append(i)
            elif isinstance(i, (RealType, VirtualType)):
                type_names.append(i.name)
            else:
                type_names.append(i.__name__)

    def rule_decorator(
        rule: cabc.Callable[[_T], bool]
    ) -> cabc.Callable[[_T], bool]:
        rule = Rule(
            id,
            name,
            type_names,
            rationale,
            category,
            action,
            rule,
            hyperlink_further_reading,
        )
        if unique_check:
            VALIDATION_RULES[category].append(rule)
        return rule

    return rule_decorator


def store_result(rule: Rule, obj: c.GenericElement, result: Result) -> None:
    """Save a ``result`` for the given ``rule`` and ModelObject."""
    results = obj._model.validation.results
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
        key = f"{__name__}.RESULTS"
        if key not in self._model.__dict__:
            self._model.__dict__[key] = Results()
            self.validate()
        return self._model.__dict__[key]

    def validate(self) -> Results:
        """Execute all registered validation rules and store results."""
        for category, obj_type_rules in self.rules.items():
            for rule in obj_type_rules:
                for type_name in rule.types:
                    for obj in self.search(type_name):
                        result = Result(
                            uuid=obj.uuid,
                            category=category,
                            value=rule(obj),
                            object=obj,
                        )
                        store_result(rule, obj, result)
        return self.results

    def search(self, typename: str) -> cabc.Iterable[c.GenericElement]:
        typeobj = _types_registry[typename]
        return typeobj.search(self._model)


class ElementValidation(Validation):
    """Provides access to the model's validation rules and results."""

    @property
    def rules(self) -> Rules:
        """Return all registered validation rules for this ModelObject."""
        return self._model.validation.rules.by_type(type(self._element))

    @property
    def results(self) -> dict[Rule, Result]:
        """Return the validation rule results for this ModelObject."""
        return self._model.validation.results.by_uuid(self._element.uuid)

    def validate(self) -> dict[Rule, Result]:
        """Execute the rules and store results for this ModelObject."""
        self._model.validate()
        return self.results
