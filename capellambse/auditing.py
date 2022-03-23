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
from __future__ import annotations

import collections.abc as cabc
import sys
import typing as t

import capellambse

from . import helpers


class AttributeAuditor:
    """Audits access to attributes of ModelElements.

    .. warning::
        This will permanently add an audithook to the global hook table.
        The auditor will keep the model alive, which may consume
        excessive memory. To avoid this once you are done with the
        model, set the ``model`` property of the auditor object to
        ``None``. This is automatically done if you use it as a
        context manager.

    Examples
    --------
    >>> auditor = AttributeAuditor(model, {"name", "description"})
    >>> print(model.la.all_components[0].name)
    Hogwarts
    >>> auditor.recorded_ids
    {'0d2edb8f-fa34-4e73-89ec-fb9a63001440'}
    >>> # Cleanup
    >>> auditor.model = None

    >>> with AttributeAuditor(model, {"name", "description"}) as auditor:
    ...     print(model.la.all_components[0].name)
    ...
    Hogwarts
    >>> auditor.recorded_ids
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

    def __enter__(self) -> AttributeAuditor:
        return self

    def __exit__(self, *_: t.Any) -> None:
        self.model = None

    def __audit(self, event: str, args: tuple[t.Any, ...]) -> None:
        if event == "capellambse.read_attribute":
            obj, attr_name, _ = args
            if not hasattr(obj, "_model") or obj._model is not self.model:
                return

            if attr_name in self.attrs and hasattr(obj, "uuid"):
                self.recorded_ids.add(obj.uuid)
