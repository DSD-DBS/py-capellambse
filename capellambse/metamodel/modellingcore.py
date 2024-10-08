# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import capellambse.model as m

from . import namespaces as ns

NS = ns.MODELLINGCORE


ModelElement = m._obj.ModelElement


class TraceableElement(m.ModelElement):
    """A template for traceable ModelObjects."""

    source = m.Single(m.Association(m.ModelElement, attr="sourceElement"))
    target = m.Single(m.Association(m.ModelElement, attr="targetElement"))
