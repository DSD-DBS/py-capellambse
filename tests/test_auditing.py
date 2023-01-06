# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import collections.abc as cabc
import sys
import typing as t

import pytest

import capellambse
from capellambse.extensions import reqif
from capellambse.loader import xmltools
from capellambse.model import common

# pylint: disable=pointless-statement, redefined-outer-name


def test_AttributeAuditor_tracks_uuids_of_accessed_ModelElements(
    model: capellambse.MelodyModel,
):
    comp, comp1, comp2 = model.la.all_components[:3]
    expected = {comp.uuid, comp2.uuid}
    with capellambse.AttributeAuditor(
        model, {"name", "description"}
    ) as recorded_ids:
        comp.name
        comp1.uuid
        comp2.description

    assert expected == recorded_ids


def test_AttributeAuditor_handles_recursive_uuid(
    model: capellambse.MelodyModel,
):
    comp = model.la.all_components[0]
    with capellambse.AttributeAuditor(model, {"uuid"}) as recorded_ids:
        comp.uuid

    assert {comp.uuid} == recorded_ids


def test_AttributeAuditor_destroys_model_reference_when_detach(
    model: capellambse.MelodyModel,
):
    auditor = capellambse.AttributeAuditor(model, {"name"})

    auditor.detach()

    assert auditor.model is None


@pytest.fixture
def audit_events() -> cabc.Iterator[list[tuple[t.Any, ...]]]:
    events: list[tuple[t.Any, ...]] | None = []

    def audit(event: str, args: tuple[t.Any, ...]) -> None:
        nonlocal events
        if events is None or not event.startswith("capellambse."):
            return
        events.append((event, *args))

    sys.addaudithook(audit)
    try:
        assert events is not None
        yield events
    finally:
        events = None


@pytest.mark.parametrize(
    ["obj_id", "attr", "accessor_type"],
    [
        pytest.param(
            "0d2edb8f-fa34-4e73-89ec-fb9a63001440",
            "name",
            xmltools.AttributeProperty,
            id="AttributeProperty",
        ),
        pytest.param(
            "0d2edb8f-fa34-4e73-89ec-fb9a63001440",
            "is_abstract",
            xmltools.BooleanAttributeProperty,
            id="BooleanAttributeProperty",
        ),
        pytest.param(
            "0d2edb8f-fa34-4e73-89ec-fb9a63001440",
            "description",
            xmltools.HTMLAttributeProperty,
            id="HTMLAttributeProperty",
        ),
        pytest.param(
            "303c2a4d-0eff-41e6-b7e8-0e500cfa38f7",
            "value",
            xmltools.NumericAttributeProperty,
            id="NumericAttributeProperty",
        ),
        pytest.param(
            "b97c09b5-948a-46e8-a656-69d764ddce7d",
            "value",
            xmltools.DatetimeAttributeProperty,
            id="DatetimeAttributeProperty",
        ),
        pytest.param(
            "1ca7b206-be29-4315-a036-0b532b26a191",
            "type",
            xmltools.EnumAttributeProperty,
            id="EnumAttributeProperty",
        ),
        pytest.param(
            "0d2edb8f-fa34-4e73-89ec-fb9a63001440",
            "components",
            common.DirectProxyAccessor,
            id="DirectProxyAccessor",
        ),
        pytest.param(
            "0d2edb8f-fa34-4e73-89ec-fb9a63001440",
            "allocated_functions",
            common.LinkAccessor,
            id="LinkAccessor",
        ),
        pytest.param(
            "0ee1fd1c-db9c-4fa6-8789-197f623b96c0",
            "type",
            common.AttrProxyAccessor,
            id="AttrProxyAccessor",
        ),
        pytest.param(
            "0d2edb8f-fa34-4e73-89ec-fb9a63001440",
            "parent",
            common.ParentAccessor,
            id="ParentAccessor",
        ),
        pytest.param(
            "7abe3167-31d9-4c89-9aad-ef422e9deb6b",
            "specification",
            common.SpecificationAccessor,
            id="SpecificationAccessor",
        ),
        pytest.param(
            "0ee1fd1c-db9c-4fa6-8789-197f623b96c0",
            "min_card",
            common.RoleTagAccessor,
            id="RoleTagAccessor",
        ),
    ],
)
def test_attribute_access_fires_exactly_one_read_attribute_event(
    model: capellambse.MelodyModel,
    audit_events: list[tuple[t.Any, ...]],
    obj_id: str,
    attr: str,
    accessor_type: type[t.Any],
) -> None:
    obj = model.by_uuid(obj_id)
    descriptor = getattr(type(obj), attr, None)
    assert descriptor is not None, f"{type(obj).__name__} has no {attr}"
    assert isinstance(descriptor, accessor_type), "Bad descriptor type"
    audit_events.clear()

    getattr(obj, attr)

    getattr_events = [
        i for i in audit_events if i[0] == "capellambse.read_attribute"
    ]
    assert len(getattr_events) == 1
    event = getattr_events[0]
    _, ev_obj, ev_attr, _ = event
    assert ev_obj == obj
    assert ev_attr == attr


@pytest.mark.parametrize(
    ["obj_id", "attr", "accessor_type"],
    [
        pytest.param(
            "3c2d312c-37c9-41b5-8c32-67578fa52dc3",
            "relations",
            reqif.RequirementsRelationAccessor,
            id="RequirementsRelationAccessor",
        ),
        pytest.param(
            "3c2d312c-37c9-41b5-8c32-67578fa52dc3",
            "related",
            reqif.ElementRelationAccessor,
            id="ElementRelationAccessor",
        ),
    ],
)
def test_attribute_access_fires_read_attribute_events(
    model: capellambse.MelodyModel,
    audit_events: list[tuple[t.Any, ...]],
    obj_id: str,
    attr: str,
    accessor_type: type[t.Any],
) -> None:
    """The last event is the one assigned to the high-level call."""

    obj = model.by_uuid(obj_id)
    descriptor = getattr(type(obj), attr, None)
    assert descriptor is not None, f"{type(obj).__name__} has no {attr}"
    assert isinstance(descriptor, accessor_type), "Bad descriptor type"
    audit_events.clear()

    getattr(obj, attr)

    events = [i for i in audit_events if i[0] == "capellambse.read_attribute"]
    assert len(events) > 1
    event = events[-1]
    _, ev_obj, ev_attr, _ = event
    assert ev_obj == obj
    assert ev_attr == attr
