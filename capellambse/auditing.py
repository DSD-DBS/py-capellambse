# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

__all__ = ["AttributeAuditor", "WriteProtector"]

import collections.abc as cabc
import sys
import typing as t

import capellambse

from . import helpers


class AttributeAuditor:
    """Audits access to attributes of ModelElements.

    .. warning::
        This will permanently add an audit hook to the global hook
        table. The auditor will keep the model alive, which may consume
        excessive memory. To avoid this, call the auditor object's
        ``detach()`` method once you are done with it. This is
        automatically done if you use it as a context manager.

    Examples
    --------
    >>> auditor = AttributeAuditor(model, {"name", "description"})
    >>> print(model.la.all_components[0].name)
    Hogwarts
    >>> auditor.recorded_ids
    {'0d2edb8f-fa34-4e73-89ec-fb9a63001440'}
    >>> # Cleanup
    >>> auditor.detach()

    >>> with AttributeAuditor(model, {"name", "description"}) as recorded_ids:
    ...     print(model.la.all_components[0].name)
    ...
    Hogwarts
    >>> recorded_ids
    {'0d2edb8f-fa34-4e73-89ec-fb9a63001440'}
    """

    def __init__(
        self,
        model: capellambse.MelodyModel,
        attrs: cabc.Container[str] = (),
    ) -> None:
        self.model: capellambse.MelodyModel | None = model
        self.attrs = attrs or helpers.EverythingContainer()
        self.recorded_ids: set[str] = set()

        sys.addaudithook(self.__audit)

    def __enter__(self) -> set[str]:
        return self.recorded_ids

    def __exit__(self, *_: t.Any) -> None:
        self.detach()

    def detach(self) -> None:
        self.model = None

    def __audit(self, event: str, args: tuple[t.Any, ...]) -> None:
        if event == "capellambse.getattr":
            obj, attr_name, attr_value = args
            if not hasattr(obj, "_model") or obj._model is not self.model:
                return

            if attr_name in self.attrs:
                self.recorded_ids.add(
                    attr_value if attr_name == "uuid" else obj.uuid
                )


class WriteProtector:
    """Prevents accidental modifications to a model.

    This class intentionally has very limited features. It is intended
    as inspiration and guidance for more specific classes that make more
    sophisticated use of audit events.

    This class also contains a publicly usable set of events that
    signify changes to the model.
    """

    events: t.Final = frozenset(
        {
            "capellambse.create",
            "capellambse.delete",
            "capellambse.insert",
            "capellambse.setattr",
            "capellambse.setitem",
        }
    )
    """Contains all built-in audit events that may modify the model."""

    def __init__(self, model: capellambse.MelodyModel) -> None:
        self.__model: capellambse.MelodyModel | None = model
        sys.addaudithook(self.__audit)

    def __enter__(self) -> None:
        return None

    def __exit__(self, *_: t.Any) -> None:
        self.detach()

    def detach(self) -> None:
        self.__model = None

    def __audit(self, event: str, args: tuple[t.Any, ...]) -> None:
        if self.__model is not None and event in self.events:
            obj: capellambse.model.GenericElement = args[0]
            if obj._model is self.__model:
                raise RuntimeError(
                    f"Cannot modify the model {self.__model.info}"
                )
