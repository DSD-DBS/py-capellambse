# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Abstract classes acting as templates for concrete classes.

These base classes are used between different layers.
"""

from capellambse import model as m


class TraceableElement(m.ModelElement):
    """A template for traceable ModelObjects."""

    source = m.AttrProxyAccessor(m.ModelElement, attr="sourceElement")
    target = m.AttrProxyAccessor(m.ModelElement, attr="targetElement")
