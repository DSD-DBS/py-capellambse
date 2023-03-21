# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import collections.abc as cabc
import contextlib
import datetime
import sys
import typing as t

import markupsafe
import pytest

import capellambse
from capellambse.extensions import reqif
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


@contextlib.contextmanager
def prohibit_events(*events: str) -> cabc.Iterator[None]:
    active = True
    events = set(events)  # type: ignore

    def audit(event: str, _: tuple[t.Any, ...]) -> None:
        nonlocal active
        if active:
            assert event not in events

    sys.addaudithook(audit)
    try:
        yield
    finally:
        active = False


@pytest.mark.parametrize(
    ["obj_id", "attr", "accessor_type"],
    [
        pytest.param(
            "0d2edb8f-fa34-4e73-89ec-fb9a63001440",
            "name",
            common.AttributeProperty,
            id="AttributeProperty",
        ),
        pytest.param(
            "0d2edb8f-fa34-4e73-89ec-fb9a63001440",
            "is_abstract",
            common.BooleanAttributeProperty,
            id="BooleanAttributeProperty",
        ),
        pytest.param(
            "0d2edb8f-fa34-4e73-89ec-fb9a63001440",
            "description",
            common.HTMLAttributeProperty,
            id="HTMLAttributeProperty",
        ),
        pytest.param(
            "303c2a4d-0eff-41e6-b7e8-0e500cfa38f7",
            "value",
            common.NumericAttributeProperty,
            id="NumericAttributeProperty",
        ),
        pytest.param(
            "b97c09b5-948a-46e8-a656-69d764ddce7d",
            "value",
            common.DatetimeAttributeProperty,
            id="DatetimeAttributeProperty",
        ),
        pytest.param(
            "1ca7b206-be29-4315-a036-0b532b26a191",
            "type",
            common.EnumAttributeProperty,
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
def test_attribute_access_fires_exactly_one_getattr_event(
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

    events = [i for i in audit_events if i[0] == "capellambse.getattr"]
    assert len(events) == 1
    event = events[0]
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

    events = [i for i in audit_events if i[0] == "capellambse.getattr"]
    assert len(events) > 1
    event = events[-1]
    _, ev_obj, ev_attr, _ = event
    assert ev_obj == obj
    assert ev_attr == attr


@pytest.mark.parametrize(
    ["obj_id", "attr", "value_factory", "accessor_type"],
    [
        pytest.param(
            "0d2edb8f-fa34-4e73-89ec-fb9a63001440",
            "name",
            lambda _: "New name",
            common.AttributeProperty,
            id="AttributeProperty",
        ),
        pytest.param(
            "0d2edb8f-fa34-4e73-89ec-fb9a63001440",
            "is_abstract",
            lambda o: not o.is_abstract,
            common.BooleanAttributeProperty,
            id="BooleanAttributeProperty",
        ),
        pytest.param(
            "0d2edb8f-fa34-4e73-89ec-fb9a63001440",
            "description",
            lambda _: markupsafe.Markup("<h1>Thing</h1>"),
            common.HTMLAttributeProperty,
            id="HTMLAttributeProperty",
        ),
        pytest.param(
            "303c2a4d-0eff-41e6-b7e8-0e500cfa38f7",
            "value",
            lambda o: o.value + 1,
            common.NumericAttributeProperty,
            id="NumericAttributeProperty",
        ),
        pytest.param(
            "b97c09b5-948a-46e8-a656-69d764ddce7d",
            "value",
            lambda _: datetime.datetime(2019, 7, 23, 17, 45, 30),
            common.DatetimeAttributeProperty,
            id="DatetimeAttributeProperty",
        ),
        pytest.param(
            "1ca7b206-be29-4315-a036-0b532b26a191",
            "type",
            lambda _: "SHARED_DATA",
            common.EnumAttributeProperty,
            id="EnumAttributeProperty",
        ),
        pytest.param(
            "0d2edb8f-fa34-4e73-89ec-fb9a63001440",
            "components",
            lambda _: [],
            common.DirectProxyAccessor,
            id="DirectProxyAccessor",
        ),
        pytest.param(
            "0d2edb8f-fa34-4e73-89ec-fb9a63001440",
            "allocated_functions",
            lambda _: [],
            common.LinkAccessor,
            id="LinkAccessor",
        ),
        pytest.param(
            "0ee1fd1c-db9c-4fa6-8789-197f623b96c0",
            "type",
            lambda o: o._model.by_uuid("bbc296e1-ed4c-40cf-b37d-c8eb8613228a"),
            common.AttrProxyAccessor,
            id="AttrProxyAccessor",
        ),
        pytest.param(
            "3c2d312c-37c9-41b5-8c32-67578fa52dc3",
            "relations",
            lambda o: [],
            reqif.RequirementsRelationAccessor,
            id="RequirementsRelationAccessor",
        ),
    ],
)
def test_attribute_assignment_fires_exactly_one_setattr_event(
    model: capellambse.MelodyModel,
    audit_events: list[tuple[t.Any, ...]],
    obj_id: str,
    attr: str,
    value_factory: cabc.Callable[[capellambse.ModelObject], t.Any],
    accessor_type: type[t.Any],
) -> None:
    obj = model.by_uuid(obj_id)
    descriptor = getattr(type(obj), attr, None)
    assert descriptor is not None, f"{type(obj).__name__} has no {attr}"
    assert isinstance(descriptor, accessor_type), "Bad descriptor type"
    value = value_factory(obj)
    audit_events.clear()

    setattr(obj, attr, value)

    events = [i for i in audit_events if i[0] == "capellambse.setattr"]
    assert len(events) == 1
    _, actual_obj, actual_attr, actual_value = events[0]
    assert actual_obj is obj
    assert actual_attr == attr
    assert actual_value == value


@pytest.mark.parametrize(
    ["obj_id", "attr", "args_factory", "accessor_type"],
    [
        pytest.param(
            "0d2edb8f-fa34-4e73-89ec-fb9a63001440",
            "components",
            lambda m: {
                "name": "Unfair advantages",
                "allocated_functions": [
                    m.by_uuid("c1a42acc-1f53-42bb-8404-77a5c08c414b")
                ],
            },
            common.DirectProxyAccessor,
            id="DirectProxyAccessor",
        ),
        pytest.param(
            "85d41db2-9e17-438b-95cf-49342452ddf3",
            "relations",
            lambda m: {
                "target": m.by_uuid("4c1f2b5d-0641-42c7-911f-7a42928580b8"),
            },
            reqif.RequirementsRelationAccessor,
            id="RequirementsRelationAccessor",
        ),
    ],
)
def test_creating_objects_fires_exactly_one_create_event(
    model: capellambse.MelodyModel,
    audit_events: list[tuple[t.Any, ...]],
    obj_id: str,
    attr: str,
    args_factory: cabc.Callable[[capellambse.MelodyModel], dict[str, t.Any]],
    accessor_type: type,
) -> None:
    obj = model.by_uuid(obj_id)
    descriptor = getattr(type(obj), attr, None)
    assert descriptor is not None, f"{type(obj).__name__} has no {attr}"
    assert isinstance(descriptor, accessor_type), "Bad descriptor type"
    create_args = args_factory(model)
    target = getattr(obj, attr)
    audit_events.clear()

    with prohibit_events("capellambse.insert", "capellambse.setattr"):
        new_obj = target.create(**create_args)

    event_filter = {
        "capellambse.create",
        "capellambse.insert",
        "capellambse.setattr",
    }
    events = [i for i in audit_events if i[0] in event_filter]
    eventnames = [i[0] for i in events]
    assert eventnames == ["capellambse.create"]
    _, *ev = events[0]
    assert ev[0] == obj
    assert ev[1] == attr
    assert ev[2] is new_obj


@pytest.mark.parametrize(
    ["obj_id", "attr", "accessor_type"],
    [
        pytest.param(
            "0d2edb8f-fa34-4e73-89ec-fb9a63001440",
            "components",
            common.DirectProxyAccessor,
            id="DirectProxyAccessor",
        ),
        pytest.param(
            "90517d41-da3e-430c-b0a9-e3badf416509",
            "exchanges",
            common.LinkAccessor,
            id="LinkAccessor",
        ),
        pytest.param(
            "0c7b7899-49a7-4e41-ab11-eb7d9c2becf6",
            "do_activity",
            common.AttrProxyAccessor,
            id="AttrProxyAccessor",
        ),
        pytest.param(
            "85d41db2-9e17-438b-95cf-49342452ddf3",
            "relations",
            reqif.RequirementsRelationAccessor,
            id="RequirementsRelationAccessor",
        ),
    ],
)
def test_deleting_an_object_from_a_list_fires_one_delete_event_for_the_object(
    model: capellambse.MelodyModel,
    audit_events: list[tuple[t.Any, ...]],
    obj_id: str,
    attr: str,
    accessor_type: type,
) -> None:
    obj = model.by_uuid(obj_id)
    descriptor = getattr(type(obj), attr, None)
    assert descriptor is not None, f"{type(obj).__name__} has no {attr}"
    assert isinstance(descriptor, accessor_type), "Bad descriptor type"
    audit_events.clear()
    target = getattr(obj, attr)

    del target[0]

    events = [
        args
        for e, o, *args in audit_events
        if e == "capellambse.delete" and o == obj
    ]
    assert len(events) == 1
    (*ev,) = events[0]
    assert ev[0] == attr
    assert ev[1] == 0


@pytest.mark.parametrize(
    ["obj_id", "attr", "accessor_type"],
    [
        pytest.param(
            "0d2edb8f-fa34-4e73-89ec-fb9a63001440",
            "components",
            common.DirectProxyAccessor,
            id="DirectProxyAccessor",
        ),
        pytest.param(
            "90517d41-da3e-430c-b0a9-e3badf416509",
            "exchanges",
            common.LinkAccessor,
            id="LinkAccessor",
        ),
        pytest.param(
            "0c7b7899-49a7-4e41-ab11-eb7d9c2becf6",
            "do_activity",
            common.AttrProxyAccessor,
            id="AttrProxyAccessor",
        ),
        pytest.param(
            "85d41db2-9e17-438b-95cf-49342452ddf3",
            "relations",
            reqif.RequirementsRelationAccessor,
            id="RequirementsRelationAccessor",
        ),
    ],
)
def test_deleting_an_entire_list_attribute_fires_one_delete_event(
    model: capellambse.MelodyModel,
    audit_events: list[tuple[t.Any, ...]],
    obj_id: str,
    attr: str,
    accessor_type: type,
) -> None:
    obj = model.by_uuid(obj_id)
    descriptor = getattr(type(obj), attr, None)
    assert descriptor is not None, f"{type(obj).__name__} has no {attr}"
    assert isinstance(descriptor, accessor_type), "Bad descriptor type"
    audit_events.clear()

    delattr(obj, attr)

    events = [
        args
        for e, o, *args in audit_events
        if e == "capellambse.delete" and o == obj
    ]
    assert len(events) == 1
    (*ev,) = events[0]
    assert ev[0] == attr
    assert ev[1] is None
