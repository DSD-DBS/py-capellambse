# SPDX-FileCopyrightText: Copyright DB InfraGO AG
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
    "Rules",
    "Validation",
    "VirtualType",
    "rule",
    "virtual_type",
]

import collections.abc as cabc
import dataclasses
import enum
import logging
import typing as t

from lxml import etree

import capellambse
import capellambse.model.modeltypes as mt
from capellambse import model
from capellambse.model import common as c

LOGGER = logging.getLogger(__name__)
_T = t.TypeVar("_T", bound=t.Union[c.GenericElement, "VirtualType"])


@dataclasses.dataclass(frozen=True)
class VirtualType(t.Generic[_T]):
    name: str
    real_type: type[_T]
    filter: cabc.Callable[[_T], bool]

    def search(self, model_: capellambse.MelodyModel) -> c.ElementList:
        assert isinstance(self.real_type, (str, type(c.GenericElement)))
        return model_.search(self.real_type).filter(self.filter)

    def matches(self, obj: c.GenericElement) -> bool:
        return isinstance(obj, self.real_type) and self.filter(obj)


@dataclasses.dataclass(frozen=True)
class RealType(t.Generic[_T]):
    class_: type[_T]

    @property
    def name(self) -> str:
        return self.class_.__name__

    def search(self, model_: capellambse.MelodyModel) -> c.ElementList:
        assert isinstance(self.class_, (str, type(c.GenericElement)))
        return model_.search(self.class_)

    def matches(self, obj: c.GenericElement) -> bool:
        return isinstance(obj, self.class_)


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
        try:
            known = self.__registry[vtype.name]
        except KeyError:
            pass
        else:
            raise RuntimeError(f"Virtual type already known: {known}")
        self.__registry[vtype.name] = vtype


_types_registry = _VirtualTypesRegistry()


def virtual_type(
    real_type: str | type[_T],
) -> cabc.Callable[[cabc.Callable[[_T], bool]], VirtualType[_T]]:
    if isinstance(real_type, str):
        (cls,) = t.cast(tuple[type[_T], ...], c.find_wrapper(real_type))
    else:
        cls = real_type

    def decorate(func: cabc.Callable[[_T], bool]) -> VirtualType[_T]:
        vtype = VirtualType(func.__name__, cls, func)
        _types_registry.register(vtype)
        return vtype

    return decorate


@virtual_type(model.oa.OperationalActivity)
def OperationalActivity(obj):
    return obj != obj._model.oa.root_activity


@virtual_type(model.ctx.SystemFunction)
def SystemFunction(obj):
    return obj != obj._model.sa.root_function


@virtual_type(model.la.LogicalFunction)
def LogicalFunction(obj):
    return obj != obj._model.la.root_function


@virtual_type(model.pa.PhysicalFunction)
def PhysicalFunction(obj):
    return obj != obj._model.pa.root_function


class Category(mt._StringyEnumMixin, enum.Enum):
    """A category for a rule."""

    REQUIRED = enum.auto()
    RECOMMENDED = enum.auto()
    SUGGESTED = enum.auto()


@dataclasses.dataclass
class Result:
    """The result of checking a validation rule against a model object."""

    rule: Rule
    object: c.GenericElement
    passed: bool

    def __repr__(self) -> str:
        """Return the representation of a result."""
        return (
            f"{type(self).__name__}(rule={self.rule!r},"
            f" object={self.object._short_repr_()},"
            f" value={self.passed!r})"
        )


@dataclasses.dataclass(frozen=True)
class Rule(t.Generic[_T]):
    """A validation rule."""

    id: str
    name: str
    types: frozenset[str]
    rationale: str
    category: Category
    action: str
    validate: cabc.Callable[[_T], bool]

    def find_objects(
        self, model_: capellambse.MelodyModel
    ) -> cabc.Iterator[_T]:
        seen: set[str] = set()
        for i in self.types:
            for obj in _types_registry[i].search(model_):
                if obj.uuid in seen:
                    continue
                seen.add(obj.uuid)
                yield obj

    def applies_to(self, obj: c.GenericElement) -> bool:
        """Check whether this Rule applies to a specific element."""
        return any(_types_registry[i].matches(obj) for i in self.types)


class Rules(dict[str, Rule]):
    """Stores validation rules indexed by their ID."""

    def by_category(self, category: Category | str) -> list[Rule]:
        """Filter the validation rules by category."""
        if isinstance(category, str):
            category = Category[category]
        return [i for i in self.values() if i.category == category]

    def by_type(self, type: type[c.GenericElement] | str) -> list[Rule]:
        """Filter the validation rules by type."""
        if not isinstance(type, str):
            type = type.__name__
        return [i for i in self.values() if type in i.types]


_VALIDATION_RULES = Rules()


class Results:
    """A set of validation results."""

    def __init__(
        self,
        results: cabc.Iterable[tuple[tuple[Rule, str], Result]] = (),
    ) -> None:
        self.__container = dict(results)

    def __len__(self) -> int:
        return len(self.__container)

    def __iter__(self) -> cabc.Iterator[Result]:
        return iter(self.__container.values())

    def get_result(
        self, rule_: Rule | str, target: str | c.GenericElement, /
    ) -> Result | None:
        if isinstance(rule_, str):
            rule_ = _VALIDATION_RULES[rule_]
        if not isinstance(target, str):
            target = target.uuid
        assert isinstance(target, str)

        try:
            return self.__container[rule_, target]
        except KeyError:
            return None

    def iter_rules(self) -> cabc.Iterator[Rule]:
        seen: set[str] = set()
        for result in self.__container.values():
            if result.rule.id in seen:
                continue
            seen.add(result.rule.id)
            yield result.rule

    def iter_objects(self) -> cabc.Iterator[c.GenericElement]:
        seen: set[str] = set()
        for result in self.__container.values():
            if result.object.uuid in seen:
                continue
            seen.add(result.object.uuid)
            yield result.object

    def iter_results(self) -> cabc.Iterator[Result]:
        return iter(self)

    def iter_compliant_objects(self) -> cabc.Iterator[c.GenericElement]:
        for obj in self.iter_objects():
            if all(i.passed for i in self.by_object(obj).iter_results()):
                yield obj

    def by_rule(self, key: Rule | str, /) -> Results:
        if not isinstance(key, Rule):
            key = _VALIDATION_RULES[key]
        return Results(
            ((rule_, objid), result)
            for (rule_, objid), result in self.__container.items()
            if rule_ == key
        )

    def by_object(self, target: str | c.GenericElement, /) -> Results:
        """Filter the validation results by the target object."""
        if not isinstance(target, str):
            target = target.uuid
        return Results(
            ((rule_, objid), result)
            for (rule_, objid), result in self.__container.items()
            if target == objid
        )

    def by_category(self, category: Category | str, /) -> Results:
        """Filter the validation results by category."""
        return Results(
            ((rule_, objid), result)
            for (rule_, objid), result in self.__container.items()
            if rule_.category == category
        )

    def by_passed(self, passed: bool, /) -> Results:
        """Filter the validation results by whether the rule passed or not."""
        return Results(
            ((rule_, objid), result)
            for (rule_, objid), result in self.__container.items()
            if result.passed == passed
        )

    def by_type(self, /, *types: str) -> Results:
        """Filter the validation results by target object type."""
        if not types:
            raise TypeError("Results.by_type requires at least one argument")
        typeobjs = [_types_registry[i] for i in types]
        return Results(
            ((rule_, objid), result)
            for (rule_, objid), result in self.__container.items()
            if any(t.matches(result.object) for t in typeobjs)
        )


def rule(
    id: str,
    category: Category,
    *,
    name: str,
    rationale: str,
    action: str,
    types: (
        str
        | VirtualType[_T]
        | type[_T]
        | cabc.Iterable[str | VirtualType[_T] | type[_T]]
    ),
) -> cabc.Callable[[cabc.Callable[[_T], bool]], Rule]:
    """Create a validation rule.

    This decorator registers the validator function as a modelling rule.
    The function is called with each model object to be validated. It
    must return True if the rule passed, and False if it did not pass.

    Parameters
    ----------
    category
        The category of severity for this rule.
    types
        Types of objects that this rule applies to.

        Object types can be either real types (subclasses of
        :class:`~capellambse.model.common.GenericElement`) or virtual
        types created with the :func:`virtual_type` decorator. These can
        be freely mixed in the rule decorator.
    id
        The unique ID of this rule.

        If another rule with this ID already exists, an error is raised.
    name
        Human-readable short name for the rule.
    rationale
        Text describing why the rule is useful.
    action
        Human-reabale short description of what needs to be changed for
        the rule to pass.
    """
    if id in _VALIDATION_RULES:
        raise ValueError(f"Duplicate rule ID: {id}")

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

    def rule_decorator(validator: cabc.Callable[[_T], bool], /) -> Rule:
        rule_ = Rule(
            id,
            name,
            frozenset(type_names),
            rationale,
            category,
            action,
            validator,
        )
        _VALIDATION_RULES.setdefault(rule_.id, rule_)
        assert _VALIDATION_RULES[rule_.id] is rule_
        return rule_

    return rule_decorator


class Validation:
    """Basic class for access to validation rules and results."""

    _model: capellambse.MelodyModel
    _element: etree._Element
    _constructed: bool

    parent = c.AlternateAccessor(c.GenericElement)

    def __init__(self, **kw: t.Any) -> None:
        raise TypeError("Cannot create Validation object this way")

    @classmethod
    def from_model(
        cls, model_: capellambse.MelodyModel, element: etree._Element
    ) -> Validation:
        """Create a Validation object for a MelodyModel or an element."""
        self = cls.__new__(cls)
        self._model = model_
        self._element = element
        self._constructed = True
        return self


class ModelValidation(Validation):
    """Provides access to the model's validation rules and results."""

    @property
    def rules(self) -> Rules:
        """Return all registered validation rules."""
        return _VALIDATION_RULES

    def validate(self) -> Results:
        """Execute all registered validation rules and store results."""
        all_results = []
        for rule_ in _VALIDATION_RULES.values():
            for obj in rule_.find_objects(self._model):
                all_results.append(
                    (
                        (rule_, obj.uuid),
                        Result(rule_, obj, rule_.validate(obj)),
                    )
                )
        return Results(all_results)

    def search(self, /, *typenames: str) -> c.ElementList[t.Any]:
        found: dict[str, t.Any] = {}
        for i in typenames:
            objs = _types_registry[i].search(self._model)
            found.update((o.uuid, o._element) for o in objs)
        return c.MixedElementList(self._model, list(found.values()))


class ElementValidation(Validation):
    """Provides access to the model's validation rules and results."""

    @property
    def rules(self) -> list[Rule]:
        """Return all registered validation rules that apply to this object."""
        obj = self.parent
        return [i for i in _VALIDATION_RULES.values() if i.applies_to(obj)]

    def validate(self) -> Results:
        """Validate this element against the rules that apply to it."""
        obj = self.parent
        all_results = []
        for rule_ in _VALIDATION_RULES.values():
            if rule_.applies_to(obj):
                all_results.append(
                    (
                        (rule_, obj.uuid),
                        Result(rule_, obj, rule_.validate(obj)),
                    )
                )
        return Results(all_results)
