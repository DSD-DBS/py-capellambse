# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

__all__ = [
    "Metadata",
    "Viewpoint",
    "ViewpointReferences",
]

from . import _obj

NS = _obj.Namespace(
    "http://www.polarsys.org/kitalpha/ad/metadata/1.0.0",
    "metadata",
    _obj.CORE_VIEWPOINT,
)


class Metadata(_obj.ModelElement):
    """Metadata about a Capella model.

    This class stores metadata about a Capella model, such as the
    Capella version that was used to create it, and the active
    viewpoints and their versions. It is tightly coupled to its parent
    :class:`Model` instance.
    """


class Viewpoint(_obj.ModelElement):
    """A viewpoint."""


class ViewpointReferences: ...
