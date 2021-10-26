# Copyright 2021 DB Netz AG
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Common classes used by all MelodyModel functions.

.. diagram:: [CDB] Common Types ORM
"""
from __future__ import annotations

import collections
import collections.abc as cabc
import typing as t

import markupsafe

from capellambse import helpers
from capellambse.loader import xmltools

# pylint: disable=invalid-name
S = t.TypeVar("S", bound=t.Optional[str])
T = t.TypeVar("T", bound="ModelObject")
U = t.TypeVar("U")
# pylint: enable=invalid-name

XTYPE_HANDLERS: dict[
    str | None, dict[str, type[t.Any]]
] = collections.defaultdict(dict)
r"""Defines a mapping between ``xsi:type``\ s and wrapper classes.

The first layer's keys can be either ``None`` or the ``xsi:type`` of the
architectural layer that the wrapper should be applied to.  In the case
of ``None``, the wrapper will be applied to all layers.  Note that
layer-specific wrappers have precedence over layer-agnostic ones.

These keys map to a further dictionary.  This second layer maps from the
``xsi:type``\ (s) that each wrapper handles to the wrapper class.
"""


def build_xtype(class_: type[ModelObject]) -> str:
    module = class_.__module__.split(".")[-1]
    clsname = class_.__name__
    return f"org.polarsys.capella.core.data.{module}:{clsname}"


def enumliteral(
    generic_element: GenericElement, attr: str, default: str = "NOT_SET"
) -> xmltools.AttributeProperty | str:
    uuid = generic_element._element.attrib.get(attr)
    if uuid is None:
        return default

    return generic_element.from_model(
        generic_element._model, generic_element._model._loader[uuid]
    ).name


def markuptype(markup: str, *args: t.Any, **kw: t.Any) -> markupsafe.Markup:
    return markupsafe.Markup(helpers.repair_html(markup), *args, **kw)


def set_accessor(
    cls: type[GenericElement],
    attr: str,
    accessor: Accessor,
) -> None:
    setattr(cls, attr, accessor)
    accessor.__set_name__(cls, attr)


def set_self_references(*args: tuple[type[GenericElement], str]) -> None:
    for cls, attr in args:
        set_accessor(cls, attr, ProxyAccessor(cls, aslist=ElementList))


def xtype_handler(  # pylint: disable=keyword-arg-before-vararg  # PEP-570
    arch: str | None = None, /, *xtypes: str
) -> cabc.Callable[[type[T]], type[T]]:
    """Register a class as handler for a specific ``xsi:type``.

    ``arch`` is the ``xsi:type`` of the desired architecture.  It must
    always be a simple string or None.  In the latter case the
    definition applies to all elements regardless of their architectural
    layer.  Architecture-specific definitions will always win over
    architecture-independent ones.

    Each string given in ``xtypes`` notes an ``xsi:type`` of elements
    that this class handles.  It is possible to specify multiple values,
    in which case the class will be registered for each ``xsi:type``
    under the architectural layer given in ``arch``.

    Handler classes' ``__init__`` methods must accept two positional
    arguments.  The first argument is the :class:`MelodyModel` instance
    which loaded the corresponding model, and the second one is the LXML
    element that needs to be handled.

    Example::

        >>> @xtype_handler('arch:xtype', 'xtype:1', 'xtype:2')
        ... class Test:
        ...     _xmltag = "ownedTests"
        ...     def from_model(self, model, element, /):
        ...         ...  # Instantiate from model XML element
    """
    if arch is not None and not isinstance(arch, str):  # pragma: no cover
        raise TypeError(
            "'arch' must be a str or None, not {}".format(type(arch).__name__)
        )

    # Compile a list of all xtype strings
    xtype_strs = []
    for xtype in xtypes:
        if isinstance(xtype, str):
            xtype_strs.append(xtype)
        else:  # pragma: no cover
            raise ValueError(
                "All `xtype`s must be str, not {!r}".format(
                    type(xtype).__name__
                )
            )

    def register_xtype_handler(cls: type[T]) -> type[T]:
        if not xtype_strs:
            xtype_strs.append(build_xtype(cls))

        for xtype in xtype_strs:
            if xtype in XTYPE_HANDLERS[arch]:  # pragma: no cover
                raise LookupError(f"Duplicate xsi:type {xtype} in {arch}")
            XTYPE_HANDLERS[arch][xtype] = cls
        return cls

    return register_xtype_handler


from .accessors import *
from .element import *
