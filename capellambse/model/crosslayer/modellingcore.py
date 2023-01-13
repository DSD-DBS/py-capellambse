# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Abstract classes acting as templates for concrete classes.

These base classes are used between different layers.
"""

from .. import common as c


class TraceableElement(c.GenericElement):
    """A template for traceable ModelObjects."""

    source = c.AttrProxyAccessor(c.GenericElement, attr="sourceElement")
    target = c.AttrProxyAccessor(c.GenericElement, attr="targetElement")
