# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from lxml import etree

def serialize(
    tree: etree._Element,
    /,
    *,
    line_length: int,
    siblings: bool,
) -> bytes: ...
