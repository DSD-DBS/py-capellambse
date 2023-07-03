# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
"""Objects for diffing declarative model YAML files."""

from __future__ import annotations

import collections.abc as cabc
import enum
import logging
import sys
import typing as t

import capellambse
from capellambse import decl, helpers
from capellambse.model import common as c

logger = logging.getLogger(__name__)
ATTR_BLACKLIST = frozenset(("uuid",))
ALLOWED_ATTR_TYPES = frozenset(
    (
        "AttributeProperty",
        "HTMLAttributeProperty",
        "NumericAttributeProperty",
        "BooleanAttributeProperty",
        "DatetimeAttributeProperty",
        "EnumAttributeProperty",
        "AttrProxyAccessor",
        "DirectProxyAccessor",
        "LinkAccessor",
        "PhysicalLinkEndsAccessor",
        "RoleTagAccessor",
        "SpecificationAccessor",
        "ElementRelationAccessor",
    )
)
PARENT_CHILD_RELATIONSHIP = frozenset(
    (c.DirectProxyAccessor, c.RoleTagAccessor)
)


def diff(
    left: capellambse.MelodyModel | c.GenericElement,
    right: capellambse.MelodyModel | c.GenericElement,
) -> list[dict[str, t.Any]]:
    """Compare ``left`` and ``right`` and return a delta in decl format."""
    if not isinstance(right, type(left)):
        raise ValueError("Can't diff model elements of different type.")
    path = [(helpers.UUIDString(left.uuid), "")]
    return _recursive_diff(left, right, path, set())


def _recursive_diff(
    left: capellambse.MelodyModel | c.GenericElement,
    right: capellambse.MelodyModel | c.GenericElement,
    path: list[tuple[helpers.UUIDString, str]],
    visited: set[helpers.UUIDString],
) -> list[dict[str, t.Any]]:
    """Compare two objects and record any differences between them.

    Parameters
    ----------
    left
        The base object to compare.
    right
        The object which ``left`` is compared to.
    path
        A list of tuples, where each tuple contains a UUID and attribute
        name, representing the path to the current comparison in the
        object graph.
    visited
        A set of UUIDs of the objects already visited to avoid cycles.

    Raises
    ------
    ValueError
        If the provided objects are not of the same type and no path was
        provided.

    Returns
    -------
    instructions
        A list of changes in declarative modelling syntax. Each change
        is a dictionary containing the UUID of the parent object and the
        specific modification: an attribute addition, deletion, or
        modification.
    """
    parent_uuid, attr = path[-1]
    if left.uuid in visited:
        return []

    visited.add(left.uuid)
    uuid = decl.UUIDReference(left.uuid)
    if type(left) != type(right):  # pylint: disable=unidiomatic-typecheck
        if not attr:
            lrepr = left._short_repr_()
            rrepr = right._short_repr_()
            raise ValueError(
                f"Provided {lrepr!r} and {rrepr!r} are not of the same type."
            )

        puuid = decl.UUIDReference(parent_uuid)
        return [
            {"parent": puuid, "delete": {attr: uuid}},
            {"parent": puuid, "extend": {attr: _decl_attributes(right)}},
        ]

    changes = list[dict[str, t.Any]]()
    for attr in _get_attribute_names(left):
        left_value = _try_getattr(left, attr)
        right_value = _try_getattr(right, attr)
        if left_value == "ERROR" or right_value == "ERROR":
            continue

        accessor = getattr(type(left), attr)
        if isinstance(left_value, c.ElementList):
            left_set: set[helpers.UUIDString] = set(left_value.by_uuid)
            right_set: set[helpers.UUIDString] = set(right_value.by_uuid)

            added = right_set - left_set
            removed = left_set - right_set
            commons = left_set & right_set

            change: dict[str, t.Any] = {"parent": uuid}
            if added:
                extensions: list[dict[str, t.Any] | decl.UUIDReference] = []
                for uuid in added:
                    if isinstance(accessor, tuple(PARENT_CHILD_RELATIONSHIP)):
                        obj = right_value.by_uuid(uuid)
                        assert isinstance(obj, c.GenericElement)
                        extensions.append(_decl_attributes(obj))
                    else:
                        extensions.append(decl.UUIDReference(uuid))

                change["extend"] = {attr: extensions}

            if removed:
                change["delete"] = {
                    attr: [decl.UUIDReference(uuid) for uuid in removed]
                }

            if isinstance(accessor, tuple(PARENT_CHILD_RELATIONSHIP)):
                for common_uuid in commons:
                    left_item = left_value.by_uuid(common_uuid)
                    right_item = right_value.by_uuid(common_uuid)
                    path.append((common_uuid, attr))
                    assert isinstance(left_item, c.GenericElement)
                    assert isinstance(right_item, c.GenericElement)
                    changes.extend(
                        _recursive_diff(left_item, right_item, path, visited)
                    )
                    path.pop()  # Stay on the right path!

            if len(change) > 1:
                changes.append(change)
        elif isinstance(left_value, c.GenericElement):
            if isinstance(accessor, tuple(PARENT_CHILD_RELATIONSHIP)):
                assert isinstance(right_value, c.GenericElement)
                path.append((left.uuid, attr))
                changes.extend(
                    _recursive_diff(left_value, right_value, path, visited)
                )
                path.pop()  # Stay on the right path!
            elif left_value.uuid != right_value.uuid:
                ruuid = helpers.UUIDString(right_value.uuid)
                changes.append(
                    {
                        "parent": uuid,
                        "modify": {attr: decl.UUIDReference(ruuid)},
                    }
                )
        elif left_value != right_value:
            changes.append({"parent": uuid, "modify": {attr: right_value}})

    return changes


def _decl_attributes(
    obj: capellambse.MelodyModel | c.GenericElement,
    visited: set[helpers.UUIDString] | None = None,
) -> dict[str, t.Any]:
    attrs = _get_attribute_names(obj)
    decl_attrs: dict[str, t.Any] = {}
    if visited is None:
        visited = set()

    if obj.uuid in visited:
        return decl_attrs  # avoid recursion on already visited objects

    visited.add(obj.uuid)
    for attr in attrs:
        accessor = getattr(type(obj), attr)
        if not (value := _try_getattr(obj, attr)):
            continue

        decl_attr: t.Any
        if isinstance(accessor, tuple(PARENT_CHILD_RELATIONSHIP)):
            # Child object case
            if isinstance(value, (c.GenericElement, capellambse.MelodyModel)):
                decl_attr = _decl_attributes(value)
            elif isinstance(value, c.ElementList):
                decl_attr = [_decl_attributes(v) for v in value]
        else:
            # Reference case
            if isinstance(value, (c.GenericElement, capellambse.MelodyModel)):
                decl_attr = decl.UUIDReference(value.uuid)
            elif isinstance(value, c.ElementList):
                decl_attr = [decl.UUIDReference(v.uuid) for v in value]
            else:
                decl_attr = _convert(value)

        if isinstance(decl_attr, list) and not decl_attr:
            continue

        decl_attrs[attr] = decl_attr

    return decl_attrs


def _get_attribute_names(
    obj: capellambse.MelodyModel | c.GenericElement,
) -> cabc.Iterator[str]:
    allowed_types = ALLOWED_ATTR_TYPES
    blacklist = ATTR_BLACKLIST
    for name in dir(obj):
        attr_descriptor = getattr(type(obj), name, None)
        if type(attr_descriptor).__name__ not in allowed_types:
            continue

        if name in blacklist:
            continue

        yield name


def _try_getattr(
    obj: c.GenericElement | capellambse.MelodyModel, attr: str
) -> c.GenericElement | c.ElementList | t.Any:
    value = "ERROR"
    try:
        value = getattr(obj, attr)
    except (AttributeError, ValueError, TypeError) as error:
        if isinstance(obj, capellambse.MelodyModel):
            orepr = repr(obj)
        else:
            orepr = obj._short_repr_()

        logger.error(
            "Failed to get %r from %r. %r", attr, orepr, error.args[0]
        )
    return value


def _convert(value: t.Any) -> str:
    if isinstance(value, enum.Enum):
        return value.name
    return value


try:
    import click
except ImportError:

    def _main() -> None:
        """Display a dependency error."""
        print("Error: Please install 'click' and retry", file=sys.stderr)
        raise SystemExit(1)

else:

    @click.command()
    @click.argument("left", type=capellambse.ModelCLI(), required=True)
    @click.argument("right", type=capellambse.ModelCLI(), required=True)
    @click.option("-d", "--destination", type=click.File("w"), required=True)
    def _main(
        left: capellambse.MelodyModel,
        right: capellambse.MelodyModel,
        destination: t.IO,
    ) -> None:
        """Return the difference of two given Capella models."""
        difference = diff(left, right)
        export_string = decl.dump(difference)
        destination.write(export_string)


if __name__ == "__main__":
    _main()
