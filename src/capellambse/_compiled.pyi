# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from typing import Protocol

from lxml import etree

class _HasWrite(Protocol):
    def write(self, _: bytes, /) -> None: ...

def serialize(
    tree: etree._Element,
    /,
    *,
    line_length: int,
    siblings: bool,
    file: _HasWrite | None,
) -> bytes: ...
