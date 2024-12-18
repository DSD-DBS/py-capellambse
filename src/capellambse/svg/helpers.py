# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import collections.abc as cabc
import math
import typing as t

from capellambse import helpers

AlignmentLiteral = t.Literal["center", "left", "right"]


def check_for_horizontal_overflow(
    text: str,
    width: int | float,
    icon_padding: int | float,
    icon_size: int | float,
    alignment: AlignmentLiteral = "center",
) -> tuple[cabc.Sequence[str], float, float]:
    max_text_width = width - icon_size - icon_padding
    max_text_width = max(max_text_width, 0)
    lines = helpers.word_wrap(text, max_text_width)
    text_width = max(w for w, _ in map(helpers.extent_func, lines))
    label_width = text_width + icon_size + icon_padding
    if alignment == "center":
        label_margin = (width - label_width) / 2
    elif alignment == "left":
        label_margin = 0
    else:
        label_margin = width - label_width
    return (lines, label_margin, text_width)


def check_for_vertical_overflow(
    lines: cabc.Sequence[str],
    height: float | int,
    max_text_width: float | int,
) -> list[str]:
    overflow = ""
    lines_to_render = []
    text_height = 0.0
    for i, (line, (_, line_height)) in enumerate(
        zip(lines, map(helpers.extent_func, lines), strict=True)
    ):
        if text_height + line_height > height:
            overflow = lines[i - 1] if i else line
            break

        text_height += line_height
        lines_to_render.append(line)

    if overflow:
        line_width = helpers.extent_func(overflow + "...")[0]
        if line_width < max_text_width:
            overflow += "..."
        else:
            dot_width = helpers.extent_func("...")[0]
            new_lines = helpers.word_wrap(
                overflow, math.floor(max_text_width - dot_width)
            )
            overflow = new_lines[0] + "..."

        if lines_to_render:
            lines_to_render[-1] = overflow
        else:
            lines_to_render.append(overflow)

    assert height >= text_height
    return lines_to_render
