# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Stylesheet generator for SVG diagrams."""

from __future__ import annotations

import collections.abc as cabc
import itertools
import logging
import operator
import re
import typing as t

from capellambse import diagram

logger = logging.getLogger(__name__)
RE_ELMCLASS = re.compile(r"^([A-Z][a-z_]*)(\.[A-Za-z][A-Za-z0-9_]*)?(:.+)?$")
CUSTOM_STYLE_ATTRS = {"marker-fill"}


class Styling:
    """Container for style attributes of svg objects.

    Notes
    -----
    Attributes containing '-' are only referenceable via getattr() or
    subscripting syntax, due to Python identifier naming rules.
    """

    def __init__(
        self, diagram_class: str | None, class_: str, prefix: str = "", **attr
    ):
        self._diagram_class = diagram_class
        self._class = class_
        self._prefix = prefix

        for key, val in attr.items():
            setattr(self, key, val)

    def __setattr__(self, name: str, value: t.Any) -> None:
        if not name.startswith("_"):
            name = name.replace("_", "-")
        super().__setattr__(name, value)

    def __getattribute__(self, attr: str) -> str:
        if attr in {"marker-start", "marker-end"}:
            defaultstyles = diagram.get_style(self._diagram_class, self._class)
            try:
                value = super().__getattribute__(attr)
            except AttributeError as err:
                try:
                    value = defaultstyles[self._style_name(attr)]
                except KeyError:
                    raise err from None
            try:
                stroke = self.stroke
            except AttributeError:
                stroke = (
                    defaultstyles.get(self._style_name("stroke")) or "#000"
                )
            return f'url("#{value}_{diagram.RGB.fromcss(stroke).tohex()}")'

        return super().__getattribute__(attr)

    def __bool__(self) -> bool:
        try:
            next(iter(self))
        except StopIteration:
            return False
        return True

    def __iter__(self) -> cabc.Iterator[str]:
        defaultstyles = diagram.get_style(self._diagram_class, self._class)
        for attr in ("marker-start", "marker-end"):
            if (
                not getattr(super(), attr, None)
                and self._style_name(attr) in defaultstyles
            ):
                yield attr

        yield from itertools.filterfalse(
            operator.methodcaller("startswith", "_"), dir(self)
        )

    @classmethod
    def _to_css(
        cls, value: float | int | str | diagram.RGB | cabc.Iterable | None
    ) -> float | int | str:
        if isinstance(value, str | int | float):
            return value
        if value is None:
            return "none"
        if isinstance(value, diagram.RGB):
            return f"#{value.tohex()}"
        if isinstance(value, cabc.Iterable):
            grad_id = cls._generate_id(
                "CustomGradient",
                value,  # type: ignore[arg-type]  # false-positive
            )
            return f'url("#{grad_id}")'
        raise ValueError(f"Invalid styling value: {value!r}")

    def _to_dict(self) -> dict[str, float | int | str]:
        """Convert this styling to a dictionary.

        The returned dict also includes the built-in default styles for
        the diagram class and object class given to the constructor.

        :meta public:
        """
        styles = diagram.get_style(self._diagram_class, self._class)
        if self._prefix:
            styles = {
                k[len(self._prefix) + 1 :]: v
                for k, v in styles.items()
                if k.startswith(f"{self._prefix}_")
            }
        else:
            styles = {k: v for k, v in styles.items() if "_" not in k}
        styles.update(
            (attr, getattr(self, attr))
            for attr in dir(self)
            if not attr.startswith("_")
        )
        return {k: self._to_css(v) for k, v in styles.items()}

    @staticmethod
    def _generate_id(
        name: str, value: cabc.Iterable[str | diagram.RGB]
    ) -> str:
        """Return unqiue identifier for given css-value."""
        return "_".join(
            itertools.chain(
                (name,),
                (diagram.RGB.fromcss(v).tohex() for v in value),
            ),
        )

    def _style_name(self, attr: str) -> str:
        if not self._prefix:
            return attr

        return "_".join((self._prefix, attr))

    def __contains__(self, obj: t.Any) -> bool:
        return hasattr(self, obj)
