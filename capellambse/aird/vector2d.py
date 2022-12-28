# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Two dimensional vector calculation utility."""
# pylint: disable=unsubscriptable-object, not-an-iterable  # false-positives
from __future__ import annotations

__all__ = [
    "Vec2Element",
    "Vec2List",
    "Vec2Property",
    "Vec2ish",
    "Vector2D",
    "line_intersect",
]

import collections.abc as cabc
import math
import operator
import typing as t

_T = t.TypeVar("_T")

Vec2Element = t.Union[float, int]
Vec2ish = t.Tuple[Vec2Element, Vec2Element]


class Vector2D(t.NamedTuple):
    """A vector in 2-dimensional space."""

    x: Vec2Element = 0
    y: Vec2Element = 0

    def __add__(self, other: Vec2ish) -> Vector2D:  # type: ignore[override]
        return self.__map2(operator.add, other)

    def __radd__(self, other: Vec2ish) -> Vector2D:
        return self.__map2(operator.add, other, True)

    def __sub__(self, other: Vec2ish) -> Vector2D:
        return self.__map2(operator.sub, other)

    def __rsub__(self, other: Vec2ish) -> Vector2D:
        return self.__map2(operator.sub, other, True)

    @t.overload  # type: ignore
    def __mul__(self, other: Vec2ish) -> Vec2Element:
        ...

    @t.overload
    def __mul__(self, other: Vec2Element) -> Vector2D:
        ...

    def __mul__(self, other: Vec2Element | Vec2ish) -> Vector2D | Vec2Element:
        result = self.__map2(operator.mul, other)
        if result is NotImplemented:
            return self.__map(operator.mul, other)
        return sum(result)

    @t.overload  # type: ignore[override]
    def __rmul__(self, other: Vec2ish) -> Vec2Element:
        ...

    @t.overload
    def __rmul__(self, other: Vec2Element) -> Vector2D:
        ...

    def __rmul__(self, other: Vec2Element | Vec2ish) -> Vector2D | Vec2Element:
        result = self.__map2(operator.mul, other, True)
        if result is NotImplemented:
            return self.__map(operator.mul, other, True)
        return sum(result)

    def __matmul__(self, other: Vec2ish) -> Vector2D:
        return self.__map2(operator.mul, other)

    def __rmatmul__(self, other: Vec2ish) -> Vector2D:
        return self.__map2(operator.mul, other, True)

    def __truediv__(self, other: Vec2Element) -> Vector2D:
        return self.__map(operator.truediv, other)

    def __rtruediv__(self, other: Vec2Element) -> Vector2D:
        return self.__map(operator.truediv, other, True)

    def __floordiv__(self, other: Vec2Element) -> Vector2D:
        result = self.__map(operator.floordiv, other)
        if result is NotImplemented:  # pragma: no cover
            return result
        return type(self)(int(result.x), int(result.y))

    def __rfloordiv__(self, other: Vec2Element) -> Vector2D:
        result = self.__map(operator.floordiv, other, True)
        if result is NotImplemented:  # pragma: no cover
            return result
        return type(self)(int(result.x), int(result.y))

    def __abs__(self) -> Vector2D:
        return type(self)(abs(self[0]), abs(self[1]))

    def __str__(self) -> str:  # pragma: no cover
        return f"({self[0]}, {self[1]})"

    @property
    def sqlength(self) -> float:
        """Calculate the squared length of this vector."""
        return self[0] ** 2 + self[1] ** 2

    @property
    def length(self) -> float:
        """Calculate the length of this vector."""
        return math.sqrt(self.sqlength)

    @property
    def normalized(self) -> Vector2D:
        """Create a unit Vector2D with the same direction as this one.

        Raises
        ------
        ZeroDivisionError
            if this Vector2D has zero length
        """
        length = self.length
        return Vector2D(*(i / length for i in self))

    def closestaxis(self) -> Vector2D:
        """Determine the axis closest to this Vector2D."""
        horizontal = abs(self[0]) >= abs(self[1])
        return Vector2D(*((-1, 1)[i >= 0] for i in self)) @ (
            horizontal,
            not horizontal,
        )

    def angleto(self, other: Vec2ish) -> float:
        r"""Calculate the angle to ``other``.

        This method calculates the angle that ``other`` was rotated by
        in order to have the same direction as ``self``, in radians.

        Notes
        -----
        The returned angle will always constitute the shortest rotation
        possible, i.e. it can have values between :math:`-\pi` and
        :math:`+\pi`.
        """
        angle = math.atan2(self[1], self[0]) - math.atan2(other[1], other[0])
        if angle > math.pi:  # pragma: no cover
            angle -= 2 * math.pi
        elif angle < -math.pi:  # pragma: no cover
            angle += 2 * math.pi
        return angle

    def rotatedby(self, theta: Vec2Element) -> Vector2D:
        """Rotate this Vector2D by ``theta`` radians."""
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        return Vector2D(
            self[0] * cos_t - self[1] * sin_t,
            self[0] * sin_t + self[1] * cos_t,
        )

    def boxsnap(self, corner1: Vec2ish, corner2: Vec2ish) -> Vector2D:
        """Snap this vector to the side of a box and return the result.

        Parameters
        ----------
        corner1
            A Vector2D describing the first corner of the target box.
        corner2
            A Vector2D describing the second corner of the target box.
        dirvec
            Ignored.
        """
        minx = min(corner1[0], corner2[0])
        miny = min(corner1[1], corner2[1])
        maxx = max(corner1[0], corner2[0])
        maxy = max(corner1[1], corner2[1])
        topleft = Vector2D(minx, miny)
        bottomright = Vector2D(maxx, maxy)
        return self.__dirless_boxsnap(topleft, bottomright)

    def __dirless_boxsnap(
        self, topleft: Vector2D, bottomright: Vector2D
    ) -> Vector2D:
        x, y = self.x, self.y
        if x < topleft.x:
            x = topleft.x
        elif x > bottomright.x:
            x = bottomright.x
        if y < topleft.y:
            y = topleft.y
        elif y > bottomright.y:
            y = bottomright.y

        if self != (x, y):
            return Vector2D(x, y)

        distances = [
            Vector2D(topleft.x - self.x, 0),
            Vector2D(bottomright.x - self.x, 0),
            Vector2D(0, topleft.y - self.y),
            Vector2D(0, bottomright.y - self.y),
        ]
        offset = min(distances, key=lambda i: i.sqlength)
        return self + offset

    def __map(
        self,
        func: cabc.Callable[[Vec2Element, Vec2Element], Vec2Element],
        other: Vec2Element | Vec2ish,
        reflected: bool = False,
    ) -> Vector2D:
        if not isinstance(other, (int, float)):  # pragma: no cover
            return NotImplemented
        if reflected:
            return type(self)(func(other, self[0]), func(other, self[1]))
        return type(self)(func(self[0], other), func(self[1], other))

    def __map2(
        self,
        func: cabc.Callable[[Vec2Element, Vec2Element], Vec2Element],
        other: Vec2Element | Vec2ish,
        reflected: bool = False,
    ) -> Vector2D:
        if isinstance(other, (int, float)):  # pragma: no cover
            return NotImplemented
        if not len(other) == 2:  # pragma: no cover
            raise ValueError("Length of 'other' must be 2")
        if reflected:
            return type(self)(func(other[0], self[0]), func(other[1], self[1]))
        return type(self)(func(self[0], other[0]), func(self[1], other[1]))


class Vec2Property:
    """A property that automatically converts 2-tuples into Vector2D."""

    __slots__ = ("default", "name", "__objclass__")
    default: Vector2D | None
    name: str | None
    __objclass__: type[t.Any]

    def __init__(self, default: Vec2ish | None = None):
        if default is None or isinstance(default, Vector2D):
            self.default = default
        else:
            self.default = Vector2D(*default)

    @t.overload
    def __get__(self, obj: None, objtype: type[t.Any]) -> Vec2Property:
        ...

    @t.overload
    def __get__(
        self, obj: t.Any, objtype: type[t.Any] | None = ...
    ) -> Vector2D:
        ...

    def __get__(
        self, obj: t.Any | None, objtype: type[t.Any] | None = None
    ) -> Vec2Property | Vector2D:
        if obj is None:
            return self
        if self.name is None:
            raise RuntimeError("This property does not have a name yet")
        try:
            return getattr(obj, f"_{type(self).__name__}__{self.name}")
        except AttributeError:
            if self.default:
                return self.default
            raise

    def __set__(self, obj: t.Any, value: Vec2ish) -> None:
        if self.name is None:
            raise RuntimeError("This property does not have a name yet")
        if not isinstance(value, Vector2D):
            value = Vector2D(*value)
        setattr(obj, f"_{type(self).__name__}__{self.name}", value)

    def __set_name__(self, owner: type[t.Any], name: str) -> None:
        self.__objclass__ = owner
        self.name = name


class Vec2List(t.MutableSequence[Vector2D]):
    """A list that automatically converts its elements into Vector2D."""

    def __init__(self, values: cabc.Iterable[Vec2ish]):
        self.__list: list[Vector2D] = []
        self.extend(values)

    def __len__(self) -> int:
        return len(self.__list)

    @t.overload
    def __getitem__(self, index: int) -> Vector2D:
        ...

    @t.overload
    def __getitem__(self, index: slice) -> cabc.MutableSequence[Vector2D]:
        ...

    def __getitem__(
        self, index: int | slice
    ) -> Vector2D | cabc.Sequence[Vector2D]:
        return self.__list[index]

    @t.overload
    def __setitem__(
        self,
        index: int,
        value: Vec2ish,
    ) -> None:
        ...

    @t.overload
    def __setitem__(
        self,
        index: slice,
        value: cabc.Iterable[Vec2ish],
    ) -> None:
        ...

    def __setitem__(
        self,
        index: int | slice,
        value: Vec2ish | cabc.Iterable[Vec2ish],
    ) -> None:
        if isinstance(index, slice):
            assert not isinstance(value, Vector2D)
            value = t.cast(cabc.Iterable[Vec2ish], value)
            self.__list[index] = (self.__cast(v) for v in value)
        else:
            assert isinstance(value, Vector2D)
            self.__list[index] = self.__cast(value)

    def __delitem__(self, index: int | slice) -> None:
        del self.__list[index]

    def append(self, value: Vec2ish) -> None:
        self.__list.append(self.__cast(value))

    def copy(self) -> Vec2List:
        """Create a copy of this Vec2List."""
        return Vec2List(self)

    def extend(self, values: cabc.Iterable[Vec2ish]) -> None:
        for i in values:
            self.append(i)

    def insert(self, index: int, value: Vector2D) -> None:
        self.__list.insert(index, self.__cast(value))

    @staticmethod
    def __cast(element: Vec2ish) -> Vector2D:
        if not isinstance(element, Vector2D):
            element = Vector2D(*element)
        return element


def line_intersect(
    line1: tuple[Vec2ish, Vec2ish], line2: tuple[Vec2ish, Vec2ish]
) -> Vector2D:
    """Calculate the point where ``line1`` and ``line2`` intersect.

    Both lines are straight lines with infinite length that are defined
    by the given points.

    Notes
    -----
    The implementation is based on
    `https://mathworld.wolfram.com/Line-LineIntersection.html`.
    """
    (x1, y1), (x2, y2) = line1
    (x3, y3), (x4, y4) = line2
    denum = (x1 - x2) * (y3 - y4) - (x3 - x4) * (y1 - y2)
    if denum == 0:
        raise ValueError("Lines are parallel")

    d1 = x1 * y2 - x2 * y1
    d2 = x3 * y4 - x4 * y3
    x = d1 * (x3 - x4) - d2 * (x1 - x2)
    y = d1 * (y3 - y4) - d2 * (y1 - y2)
    return Vector2D(x / denum, y / denum)
