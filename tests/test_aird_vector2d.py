# Copyright 2021 DB Netz AG
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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


class TestVectorSnapping:
    PORTBOX = aird.diagram.Box(
        (1, 1), aird.parser._common.PORT_SIZE, port=True
    )

    @pytest.mark.parametrize(
        ["points", "expected"],
        [
            pytest.param(
                [aird.Vector2D(-1, 6), aird.Vector2D(0, 6)],
                aird.Vector2D(1, 6),
                id="From West - Perfect align",
            ),
            pytest.param(
                [aird.Vector2D(-1, 1), aird.Vector2D(0, 1)],
                aird.Vector2D(1, 1),
                id="From West - (-Y)-Offset, still in bounds",
            ),
            pytest.param(
                [aird.Vector2D(-1, 11), aird.Vector2D(0, 11)],
                aird.Vector2D(1, 11),
                id="From West - (+Y)-Offset, still in bounds",
            ),
            pytest.param(
                [aird.Vector2D(0, -1), aird.Vector2D(0, 0)],
                aird.Vector2D(1, 1),
                id="Upperleft - Offbounds",
            ),
            pytest.param(
                [aird.Vector2D(6, -1), aird.Vector2D(6, 0)],
                aird.Vector2D(6, 1),
                id="From North - Perfect align",
            ),
            pytest.param(
                [aird.Vector2D(1, -1), aird.Vector2D(1, 0)],
                aird.Vector2D(1, 1),
                id="From North - (-X)-Offset, still in bounds",
            ),
            pytest.param(
                [aird.Vector2D(11, -1), aird.Vector2D(11, 0)],
                aird.Vector2D(11, 1),
                id="From North - (+X)-Offset, still in bounds",
            ),
            pytest.param(
                [aird.Vector2D(13, 0), aird.Vector2D(12, 0)],
                aird.Vector2D(11, 1),
                id="Upperright - Offbounds",
            ),
            pytest.param(
                [aird.Vector2D(13, 1), aird.Vector2D(12, 1)],
                aird.Vector2D(11, 1),
                id="From East - (-Y)-Offset, still in bounds",
            ),
            pytest.param(
                [aird.Vector2D(13, 11), aird.Vector2D(12, 11)],
                aird.Vector2D(11, 11),
                id="From East - (+Y)-Offset, still in bounds",
            ),
            pytest.param(
                [aird.Vector2D(6, 13), aird.Vector2D(6, 12)],
                aird.Vector2D(6, 11),
                id="From South - Perfect align",
            ),
            pytest.param(
                [aird.Vector2D(1, 13), aird.Vector2D(1, 12)],
                aird.Vector2D(1, 11),
                id="From South - (-X)-Offset, still in bounds",
            ),
            pytest.param(
                [aird.Vector2D(11, 13), aird.Vector2D(11, 12)],
                aird.Vector2D(11, 11),
                id="From South - (+X)-Offset, still in bounds",
            ),
        ],
    )
    def test_edge_snaptarget_to_middle_of_port(
        self, points: list[aird.Vector2D], expected: aird.Vector2D
    ):
        """Test snapping of edges from all sides to the closest point on
        border of port. Port movement not allowed.
        """
        aird.parser._edge_factories.snaptarget(points, 1, 0, self.PORTBOX)

        assert points[-1] == expected
