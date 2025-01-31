# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Collection of tools for drawing model complexity assessment badge."""

from __future__ import annotations

import collections.abc as cabc

COLORS = ("#ffdd87", "#91cc84", "#a5c2e6", "#f89f9f")
LEGEND = (
    (2, "Operational Analysis"),
    (36, "System Analysis"),
    (66, "Logical Architecture"),
    (99, "Physical Architecture"),
)
"""The x-offset and label of each legend entry."""


def draw_rect(
    x: float,
    y: float,
    width: float,
    height: float,
    fill: str = "#FFF",
    stroke: str = "#333",
    stroke_width: float = 0,
) -> str:
    """Construct a rectangle (SVG string)."""
    return (
        f'<rect fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"'
        f' x="{x}" y="{y}" width="{width}" height="{height}" />\n'
    )


def draw_group(
    contents: list[str],
    fill: str | None = None,
    font_size: float | None = None,
    font_family: str | None = None,
) -> str:
    """Construct a group (SVG string)."""
    return (
        "<g"
        + (f' font-family="{font_family}"' if font_family else "")
        + (f' font-size="{font_size:.2}"' if font_size else "")
        + (f' fill="{fill}"' if fill else "")
        + f">\n{''.join(contents)}</g>\n"
    )


def draw_text(
    x: float, y: float, text: str, font_size: float | None = None
) -> str:
    """Construct a text element (SVG string)."""
    return (
        "<text "
        + (f'font-size="{font_size:.2}"' if font_size else "")
        + f'x="{x}" y="{y}">{text}</text>\n'
    )


def draw_legend(x: float, y: float):
    """Construct plot legend (SVG string)."""
    return draw_group(
        [
            draw_rect(x + x_offset, y, 5, 3, fill=COLORS[idx])
            + draw_text(x + x_offset + 6, y + 2.6, text)
            for idx, (x_offset, text) in enumerate(LEGEND)
        ],
        fill="#555",
        font_size=2.8,
    )


def draw_bar(
    data: cabc.Sequence[float],
    max_width: float,
    x: float,
    y: float,
    height: float = 8,
    show_label_threshold: float = 0.1,
) -> str:
    """Construct a 4-segment bar plot (SVG string).

    Segment spacing is defined by {data}; Sum of {data} must match 1 for
    the thing to work the right way. Segments are labeled with "%" if
    the width is above {show_label_threshold}.
    """
    widths = [max_width * x for x in data]
    offsets = [0.0]
    for i, width in enumerate(widths[:-1]):
        offsets.append(offsets[i] + width)
    label = [
        f"{x * 100.0:.0f}%" if x >= show_label_threshold else "" for x in data
    ]
    return draw_group(
        [
            draw_rect(
                x=x + x_offset,
                y=y,
                width=widths[idx],
                height=height,
                fill=COLORS[idx],
            )
            + (
                draw_text(
                    x=x + x_offset + 1,
                    y=y + (height / 2.0) + 1,
                    text=label[idx],
                )
                if len(label[idx]) > 0
                else ""
            )
            for idx, x_offset in enumerate(offsets)
        ],
        font_size=3.2,
    )


def draw_diagrams_icon(x: float | int, y: float | int):
    """Create simple diagram icon (SVG string)."""
    return (
        '<g stroke="#555" stroke-width=".2">'
        f'<path fill="#FFF" d="M{x + 0.5} {y + 1.8} h3.6 v3.1 H{x + 0.5} z"/>'
        f'<path fill="#a5c2e6" d="M{x + 1} {y + 2.4} h1v.7 H{x + 1}z '
        'm.8 1.2h1v.7h-1z m.9-1.1h.8v.6h-.8z"/><path fill="none" '
        f'd="M{x + 1}.9 {y + 2.8} h.8 m-1.3.3.4.8 m1 .1.4-.9"/></g>'
    )


def draw_objects_icon(x: float | int, y: float | int):
    """Create simple objects icon (SVG string)."""
    return (
        '<g stroke="#555" stroke-width=".3">'
        f'<path fill="#ffdd87" d="M{x + 1} {y + 2.1} h1.9 V{y + 4} h-2 z"/>'
        f'<path fill="#a5c2e6" d="M{x + 1.8} {y + 3} h2 v1.8 h-2 z"/></g>'
    )


def draw_labeled_bar(
    x: float,
    y: float,
    label: str,
    segments: list[int],
    draw_icon: cabc.Callable[[float | int, float | int], str],
) -> str:
    """Construct a bar with label and icon (SVG string)."""
    total = sum(segments)
    if total:
        normalized_segments = [x / total for x in segments]
    else:
        normalized_segments = [0 for _ in segments]
    return (
        draw_icon(x, y)
        + draw_text(x + 5, y + 3, f"{total}")
        + draw_text(x + 5, y + 6, label)
        + draw_bar(normalized_segments, 104, x + 22.2, y)
    )


def draw_summary_badge(
    objects: list[int], diagrams: list[int], scale: float = 4.0
) -> str:
    """Construct summary badge (SVG string)."""
    text = draw_group(
        [
            draw_rect(1, 0, 132, 30, stroke_width=0.2),
            draw_rect(23.8, 1.4, 108, 22, stroke_width=0.2),
            draw_labeled_bar(2, 3.4, "objects", objects, draw_objects_icon),
            draw_labeled_bar(
                2, 13.4, "diagrams", diagrams, draw_diagrams_icon
            ),
            draw_legend(1, 25),
        ],
        font_family="sans-serif",
        font_size=3.2,
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg"'
        f' width="{scale * 134}" height="{scale * 30}" viewBox="0 0 134 30">'
        f"{text}</svg>\n"
    )
