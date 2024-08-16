# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import typing as t

from svgwrite import container, gradients, path

# compatibility re-export
from capellambse.diagram._icons import _make_lgradient  # noqa: F401

from . import decorations

Gradient = gradients.LinearGradient | gradients.RadialGradient


def _make_marker(
    ref_pts: tuple[float, float],
    size: tuple[float, float],
    *,
    id_: str,
    d: str,
    **kwargs: t.Any,
) -> container.Marker:
    marker = container.Marker(
        insert=ref_pts,
        size=size,
        id_=id_,
        orient="auto",
        markerUnits="userSpaceOnUse",
    )
    marker.add(path.Path(d=d, **kwargs))
    return marker


@decorations.marker_factories
def fine_arrow_mark(id_, /, **kw) -> container.Marker:
    d = (
        "M 0.4535,0.107 7.309,3.621 0.492,7.407 "
        "0.144,7.407 6.414,3.63 0.136,0.479 Z"
    )
    return _make_marker((7, 3.75), (7.5, 7.5), id_=id_, d=d, **kw)


def _make_arrow_marker(id_: str, /, **kw) -> container.Marker:
    return _make_marker(
        (5, 2.5), (5.5, 5.5), id_=id_, d="M 0,0 5,2.5 0,5", **kw
    )


@decorations.marker_factories
def arrow_mark(id_, /, **kw) -> container.Marker:
    kw.setdefault("fill", "#fff")
    return _make_arrow_marker(id_, **kw)


@decorations.marker_factories
def filled_arrow_mark(id_, /, **kw) -> container.Marker:
    kw.setdefault("fill", "#000")
    return _make_arrow_marker(id_, **kw)


def _make_diamond_marker(id_: str, /, **kw) -> container.Marker:
    return _make_marker(
        (0, 3), (11, 6), id_=id_, d="M 0,3 5,0.5 10,3 5,5.5 Z", **kw
    )


@decorations.marker_factories
def diamond_mark(id_, /, **kw) -> container.Marker:
    kw.setdefault("fill", "#fff")
    return _make_diamond_marker(id_, **kw)


@decorations.marker_factories
def filled_diamond_mark(id_, /, **kw) -> container.Marker:
    kw.setdefault("fill", "#000")
    return _make_diamond_marker(id_, **kw)


@decorations.marker_factories
def generalization_mark(id_, /, **kw) -> container.Marker:
    kw.setdefault("fill", "#fff")
    d = "M 0.1275,7.5 7.5,3.75 0,0 Z"
    return _make_marker((7, 4), (7.5, 7.5), id_=id_, d=d, **kw)
