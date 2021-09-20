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
