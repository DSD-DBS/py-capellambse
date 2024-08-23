# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Implements a high-level interface to Capella projects."""

from __future__ import annotations

import collections.abc as cabc
import enum
import functools
import typing as t
import warnings

E = t.TypeVar("E", bound=enum.Enum)
"""TypeVar for ":py:class:`~enum.Enum`"."""
S = t.TypeVar("S", bound=str | None)
"""TypeVar for ":py:class:`str` | None"."""
T = t.TypeVar("T", bound="ModelObject")
"""TypeVar for ":py:class:`capellambse.model.ModelObject`"."""
T_co = t.TypeVar("T_co", bound="ModelObject", covariant=True)
"""Covariant TypeVar for ":py:class:`capellambse.model.ModelObject`"."""
U = t.TypeVar("U")
"""TypeVar (unbound)."""


def set_accessor(
    cls: type[ModelObject], attr: str, accessor: Accessor
) -> None:
    setattr(cls, attr, accessor)
    accessor.__set_name__(cls, attr)


def set_self_references(*args: tuple[type[ModelObject], str]) -> None:
    for cls, attr in args:
        set_accessor(cls, attr, DirectProxyAccessor(cls, aslist=ElementList))


def attr_equal(attr: str) -> cabc.Callable[[type[T]], type[T]]:
    def add_wrapped_eq(cls: type[T]) -> type[T]:
        orig_eq = cls.__eq__

        @functools.wraps(orig_eq)
        def new_eq(self, other: object) -> bool:
            try:
                cmpkey = getattr(self, attr)
            except AttributeError:
                pass
            else:
                if isinstance(other, type(cmpkey)):
                    result = cmpkey.__eq__(other)
                else:
                    result = other.__eq__(cmpkey)
                if result is not NotImplemented:
                    return result
            return orig_eq(self, other)

        cls.__eq__ = new_eq  # type: ignore[method-assign]
        cls.__hash__ = None  # type: ignore

        return cls

    return add_wrapped_eq


def stringy_enum(et: type[enum.Enum]) -> type[enum.Enum]:
    """Make an Enum stringy.

    This decorator makes an Enum's members compare equal to their
    respective ``name``.
    """

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self is other
        if isinstance(other, str):
            return self.name == other
        return NotImplemented

    def __str__(self):
        return str(self.name)

    def __hash__(self):
        return hash(self.name)

    et.__eq__ = __eq__  # type: ignore[method-assign]
    et.__str__ = __str__  # type: ignore[method-assign]
    et.__hash__ = __hash__  # type: ignore[method-assign]
    return et


from . import diagram
from ._descriptors import *
from ._model import *
from ._obj import *
from ._pods import *
from ._xtype import *

# NOTE: These are not in __all__ to avoid duplicate documentation in Sphinx,
#       however their docstring should mention the re-export.
from .diagram import AbstractDiagram as AbstractDiagram
from .diagram import Diagram as Diagram
from .diagram import DiagramAccessor as DiagramAccessor
from .diagram import DiagramType as DiagramType

ModelElement.parent = ParentAccessor(ModelElement)


if not t.TYPE_CHECKING:
    from ._descriptors import __all__ as _all1
    from ._model import __all__ as _all2
    from ._obj import __all__ as _all3
    from ._pods import __all__ as _all4
    from ._xtype import __all__ as _all5

    __all__ = [
        "E",
        "S",
        "T",
        "T_co",
        "U",
        "attr_equal",
        "diagram",
        "set_self_references",
        "stringy_enum",
        *_all1,
        *_all2,
        *_all3,
        *_all4,
        *_all5,
    ]

    _deprecated_names = {
        "GenericElement": ModelElement,
        "RoleTagAccessor": Containment,
        "AttrProxyAccessor": Association,
        "LinkAccessor": Allocation,
        "ReferenceSearchingAccessor": Backref,
    }

    def __getattr__(attr):
        if target := _deprecated_names.get(attr):
            warnings.warn(
                f"{attr} is deprecated, use {target.__name__} instead",
                DeprecationWarning,
                stacklevel=2,
            )
            return target
        raise AttributeError(f"{__name__} has no attribute {attr}")
