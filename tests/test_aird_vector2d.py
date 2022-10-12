# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import itertools
import math
import operator

import pytest

from capellambse import aird


@pytest.mark.parametrize(
    ["calculate", "vec_1", "vec_2", "expected"],
    [
        # Addition of two vectors
        (
            operator.add,
            aird.Vector2D(2, 5),
            aird.Vector2D(8, 1),
            aird.Vector2D(10, 6),
        ),
        (operator.add, aird.Vector2D(2, 5), (8, 1), aird.Vector2D(10, 6)),
        (operator.add, (2, 5), aird.Vector2D(8, 1), aird.Vector2D(10, 6)),
        # Subtraction of two vectors
        (
            operator.sub,
            aird.Vector2D(8, 5),
            aird.Vector2D(2, 1),
            aird.Vector2D(6, 4),
        ),
        (operator.sub, aird.Vector2D(8, 5), (2, 1), aird.Vector2D(6, 4)),
        (operator.sub, (8, 5), aird.Vector2D(2, 1), aird.Vector2D(6, 4)),
        # Multiplication with scalar
        (operator.mul, aird.Vector2D(3, 4), 2, aird.Vector2D(6, 8)),
        (operator.mul, 2, aird.Vector2D(3, 4), aird.Vector2D(6, 8)),
        # Multiplication with vector
        (operator.mul, aird.Vector2D(3, 4), aird.Vector2D(5, 2), 23),
        (operator.mul, aird.Vector2D(3, 4), (5, 2), 23),
        (operator.mul, (3, 4), aird.Vector2D(5, 2), 23),
        # Matrix multiplication
        (
            operator.matmul,
            aird.Vector2D(3, 4),
            aird.Vector2D(5, 2),
            aird.Vector2D(15, 8),
        ),
        (operator.matmul, aird.Vector2D(3, 4), (5, 2), aird.Vector2D(15, 8)),
        (operator.matmul, (3, 4), aird.Vector2D(5, 2), aird.Vector2D(15, 8)),
        # True division
        (operator.truediv, aird.Vector2D(8, 6), 2, aird.Vector2D(4.0, 3.0)),
        (operator.truediv, 8, aird.Vector2D(4, 2), aird.Vector2D(2.0, 4.0)),
        # Floor division
        (operator.floordiv, aird.Vector2D(8, 6), 2, aird.Vector2D(4, 3)),
        (operator.floordiv, 8, aird.Vector2D(4, 2), aird.Vector2D(2, 4)),
    ],
)
def test_vector_math(calculate, vec_1, vec_2, expected):
    actual = calculate(vec_1, vec_2)
    assert isinstance(actual, type(expected))
    if isinstance(expected, aird.Vector2D):
        assert isinstance(actual[0], type(expected[0]))
        assert isinstance(actual[1], type(expected[1]))
    assert actual == expected


@pytest.mark.parametrize(
    ["vector", "expected"],
    [
        (aird.Vector2D(-2, 1), (2, 1)),
        (aird.Vector2D(3, -5), (3, 5)),
        (aird.Vector2D(2, 2), (2, 2)),
        (aird.Vector2D(-7, -4), (7, 4)),
    ],
)
def test_abs_makes_negative_components_positive(vector, expected):
    actual = abs(vector)
    assert isinstance(actual, aird.Vector2D)
    assert actual == expected


@pytest.mark.parametrize(
    ["vector", "expected"],
    [
        (aird.Vector2D(-2, 1), 5),
        (aird.Vector2D(3, -5), 34),
        (aird.Vector2D(2, 2), 8),
        (aird.Vector2D(-7, -4), 65),
    ],
)
def test_squared_length(vector, expected):
    actual = vector.sqlength
    assert math.isclose(actual, expected)


@pytest.mark.parametrize(
    ["vector", "expected"],
    [
        (aird.Vector2D(-2, 1), 2.23606797749979),
        (aird.Vector2D(3, -5), 5.830951894845301),
        (aird.Vector2D(2, 2), 2.8284271247461903),
        (aird.Vector2D(-7, -4), 8.06225774829855),
    ],
)
def test_length(vector, expected):
    actual = vector.length
    assert math.isclose(actual, expected)


@pytest.mark.parametrize(
    ["vector", "expected"],
    [
        (aird.Vector2D(-2, 1), (-0.8944271909999159, 0.4472135954999579)),
        (aird.Vector2D(3, -5), (0.5144957554275265, -0.8574929257125441)),
        (aird.Vector2D(2, 2), (0.7071067811865475, 0.7071067811865475)),
        (
            aird.Vector2D(-7, -4),
            (-0.8682431421244593, -0.49613893835683387),
        ),
    ],
)
def test_normalized(vector, expected):
    actual = vector.normalized
    assert math.isclose(actual[0], expected[0])
    assert math.isclose(actual[1], expected[1])


@pytest.mark.parametrize(
    ["vector", "expected"],
    [
        # Exactly on the box - noop
        (aird.Vector2D(1, 1), aird.Vector2D(1, 1)),
        (aird.Vector2D(1, 3), aird.Vector2D(1, 3)),
        (aird.Vector2D(5, 1), aird.Vector2D(5, 1)),
        (aird.Vector2D(5, 3), aird.Vector2D(5, 3)),
        (aird.Vector2D(1, 2), aird.Vector2D(1, 2)),
        (aird.Vector2D(5, 2), aird.Vector2D(5, 2)),
        (aird.Vector2D(3, 1), aird.Vector2D(3, 1)),
        (aird.Vector2D(3, 3), aird.Vector2D(3, 3)),
        # Inside the box
        (aird.Vector2D(3, 1.5), aird.Vector2D(3, 1)),
        (aird.Vector2D(1.5, 2), aird.Vector2D(1, 2)),
        (aird.Vector2D(3, 2.5), aird.Vector2D(3, 3)),
        (aird.Vector2D(4.5, 2), aird.Vector2D(5, 2)),
        # Outside left
        (aird.Vector2D(0, 2), aird.Vector2D(1, 2)),
        # Outside right
        (aird.Vector2D(6, 2), aird.Vector2D(5, 2)),
        # Outside top
        (aird.Vector2D(3, 0), aird.Vector2D(3, 1)),
        # Outside bottom
        (aird.Vector2D(3, 4), aird.Vector2D(3, 3)),
        # Outside top-left
        (aird.Vector2D(0, 0), aird.Vector2D(1, 1)),
        (aird.Vector2D(-1, 0), aird.Vector2D(1, 1)),
        (aird.Vector2D(0, -1), aird.Vector2D(1, 1)),
        # Outside top-right
        (aird.Vector2D(6, 0), aird.Vector2D(5, 1)),
        (aird.Vector2D(7, 0), aird.Vector2D(5, 1)),
        (aird.Vector2D(6, -1), aird.Vector2D(5, 1)),
        # Outside bottom-left
        (aird.Vector2D(0, 4), aird.Vector2D(1, 3)),
        (aird.Vector2D(-1, 4), aird.Vector2D(1, 3)),
        (aird.Vector2D(0, 5), aird.Vector2D(1, 3)),
        # Outside bottom-right
        (aird.Vector2D(6, 4), aird.Vector2D(5, 3)),
        (aird.Vector2D(7, 4), aird.Vector2D(5, 3)),
        (aird.Vector2D(6, 5), aird.Vector2D(5, 3)),
    ],
)
def test_boxsnap(vector: aird.Vector2D, expected: aird.Vector2D):
    topleft = aird.Vector2D(1, 1)
    botright = aird.Vector2D(5, 3)

    actual = vector.boxsnap(topleft, botright)

    assert actual == expected


@pytest.mark.parametrize(
    ["vector1", "vector2", "expected"],
    [
        pytest.param(
            (aird.Vector2D(0, 0), aird.Vector2D(1, 1)),
            (aird.Vector2D(1, 0), aird.Vector2D(0, 1)),
            aird.Vector2D(0.5, 0.5),
            id="Simple",
        ),
        pytest.param(
            (aird.Vector2D(1, 0), aird.Vector2D(2, 0)),
            (aird.Vector2D(0, 6), aird.Vector2D(0, 3)),
            aird.Vector2D(0, 0),
            id="Intersection not between given points",
        ),
    ],
)
def test_line_intersect(
    vector1: tuple[aird.Vector2D, aird.Vector2D],
    vector2: tuple[aird.Vector2D, aird.Vector2D],
    expected: aird.Vector2D,
):
    point = aird.line_intersect(vector1, vector2)

    assert point == expected


def test_line_intersect_raises_ValueError_when_parallel_lines_given():
    with pytest.raises(ValueError):
        aird.line_intersect(
            (aird.Vector2D(0, 0), aird.Vector2D(0, 1)),
            (aird.Vector2D(1, 0), aird.Vector2D(1, 1)),
        )


class TestVectorSnapping:
    PORTBOX = aird.diagram.Box(
        (1, 1), aird.parser._common.PORT_SIZE, port=True
    )
    PORT_WEST = aird.Vector2D(1, 6)
    PORT_NORTH = aird.Vector2D(6, 1)
    PORT_EAST = aird.Vector2D(11, 6)
    PORT_SOUTH = aird.Vector2D(6, 11)

    @pytest.mark.parametrize(
        ["points", "expected"],
        [
            pytest.param(
                [aird.Vector2D(0, -1), aird.Vector2D(0, 1)],
                PORT_WEST,
                id="West - Outside - Parallel(above)",
            ),
            pytest.param(
                [aird.Vector2D(-1, 1), aird.Vector2D(0, 1)],
                PORT_WEST,
                id="West - Outside - Perpendicular",
            ),
            pytest.param(
                [aird.Vector2D(0, 2), aird.Vector2D(0, 1)],
                PORT_WEST,
                id="West - Outside - Parallel(lower)",
            ),
            pytest.param(
                [aird.Vector2D(0, 5), aird.Vector2D(0, 6)],
                PORT_WEST,
                id="West - Outside - Parallel(above) - Perfect align",
            ),
            pytest.param(
                [aird.Vector2D(-1, 6), aird.Vector2D(0, 6)],
                PORT_WEST,
                id="West - Outside - Perpendicular - Perfect align",
            ),
            pytest.param(
                [aird.Vector2D(0, 7), aird.Vector2D(0, 6)],
                PORT_WEST,
                id="West - Outside - Parallel(lower) - Perfect align",
            ),
            pytest.param(
                [aird.Vector2D(0, 10), aird.Vector2D(0, 11)],
                PORT_WEST,
                id="West - Outside - Parallel(above)",
            ),
            pytest.param(
                [aird.Vector2D(-1, 11), aird.Vector2D(0, 11)],
                PORT_WEST,
                id="West - Outside - Perpendicular",
            ),
            pytest.param(
                [aird.Vector2D(0, 12), aird.Vector2D(0, 11)],
                PORT_WEST,
                id="West - Outside - Parallel(lower)",
            ),
        ],
    )
    def test_snap_manhattan_to_middle_of_port_side(
        self, points: list[aird.Vector2D], expected: aird.Vector2D
    ):
        aird.parser._edge_factories.snaptarget(
            points, -1, -2, self.PORTBOX, False, "manhattan"
        )

        points_ = itertools.tee(points, 2)
        next(points_[1], None)
        for p, q in zip(*points_):
            direction = p - q
            assert direction and (direction.x == 0 or direction.y == 0)
        assert points[-1] == expected


@pytest.mark.parametrize(
    ["point", "source", "expected"],
    [
        # horizontal
        ((20, -5), (19, -5), (5, 0)),
        ((-5, 5), (-6, 5), (0, 5)),
        ((-5, 7), (-6, 7), (0, 5)),
        ((20, 15), (19, 15), (5, 10)),
        ((20, 5), (19, 5), (0, 5)),
        ((20, 2), (19, 2), (0, 5)),
        # vertical
        ((-5, 20), (-5, 19), (0, 5)),
        ((5, -5), (5, -6), (5, 0)),
        ((7, -5), (7, -6), (5, 0)),
        ((15, 20), (15, 19), (10, 5)),
        ((5, 20), (5, 19), (5, 0)),
        ((2, 20), (2, 19), (5, 0)),
    ],
)
def test_box_snapping_manhattan(
    point: aird.Vec2ish, source: aird.Vec2ish, expected: aird.Vec2ish
) -> None:
    box = aird.Box((0, 0), (10, 10), port=True)
    style = aird.RoutingStyle.MANHATTAN

    new_point = box.vector_snap(point, source=source, style=style)

    assert new_point == expected


@pytest.mark.parametrize(
    ["point", "source", "expected"],
    [
        # horizontal
        ((2, 0), (-4, 0), (2, 0)),
        ((2, 10), (-4, 10), (2, 10)),
        ((2, 0), (22, 0), (2, 0)),
        ((2, 10), (22, 10), (2, 10)),
        # vertical
        ((4, 20), (4, 40), (4, 10)),
        ((4, -10), (4, -40), (4, 0)),
    ],
)
def test_box_snapping_tree(
    point: aird.Vec2ish, source: aird.Vec2ish, expected: aird.Vec2ish
) -> None:
    box = aird.Box((0, 0), (10, 10), port=False)
    style = aird.RoutingStyle.TREE

    new_point = box.vector_snap(point, source=source, style=style)

    assert new_point == expected


@pytest.mark.parametrize(
    ["point", "source", "expected"],
    [
        # horizontal
        ((2, 0), (-4, 0), (5, 0)),
        ((2, 10), (-4, 10), (5, 10)),
        ((2, 0), (22, 0), (5, 0)),
        ((2, 10), (22, 10), (5, 10)),
        # vertical
        ((4, 20), (4, 40), (5, 10)),
        ((4, -10), (4, -40), (5, 0)),
    ],
)
def test_box_port_snapping_tree(
    point: aird.Vec2ish, source: aird.Vec2ish, expected: aird.Vec2ish
) -> None:
    box = aird.Box((0, 0), (10, 10), port=True)
    style = aird.RoutingStyle.TREE

    new_point = box.vector_snap(point, source=source, style=style)

    assert new_point == expected
