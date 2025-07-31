# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import operator
import os
import typing as t

import markupsafe
import pytest

import capellambse.metamodel as mm
import capellambse.model as m

from .conftest import Models  # type: ignore


def test_model_info_contains_capella_version(model: m.MelodyModel):
    assert hasattr(model.info, "capella_version")


@pytest.mark.parametrize(
    "aird",
    [
        pytest.param(Models.test7_0, id="7.0"),
    ],
)
def test_model_compatibility(aird: str) -> None:
    m.MelodyModel(aird)


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        (
            "a8c42033-fdf2-458f-bae9-1cfd1207c49f",
            [
                ("1bba6377-90b7-42d6-ad03-6c536e5519fd", "involved", None),
                ("2d86d2fe-577f-4dfe-8f6b-b029df3e2056", "source", None),
                ("3da0cc89-f82f-4b67-9386-453fd06ba7c7", "source", None),
                ("432e5fce-24cd-4288-9096-6795f985b75d", "source", None),
                ("523cf480-183f-4527-8d37-20b823a127e0", "source", None),
                (
                    "53c58b24-3938-4d6a-b84a-bb9bff355a41",
                    "involved_entities",
                    2,
                ),
                ("55c6adbe-63a5-4d1f-8319-e2f768b79fbf", "involved", None),
                ("6638ccd2-61cc-481e-bb23-4c1b147e1dbc", "target", None),
                ("70e4d2ca-7895-484f-b4f2-a86628fa0262", "source", None),
                ("7a6657e7-0973-441c-8634-0802c7bfcadd", "source", None),
                (
                    "83d1334f-6180-46c4-a80d-6839341df688",
                    "involved_entities",
                    0,
                ),
                ("9ac82bfc-1aa6-4773-9a99-91f910389668", "type", None),
                ("dbc6b4b0-82a1-4c28-bb48-073df1437e43", "source", None),
                ("e37510b9-3166-4f80-a919-dfaac9b696c7", "entities", 3),
            ],
        ),
        (
            "91dc2eec-c878-4fdb-91d8-8f4a4527424e",
            [
                ("88d7f9a7-1fae-4884-8233-7582153cc5a7", "target", None),
                ("a94806d8-71bb-4eb8-987b-bdce6ca99cb8", "involved_states", 0),
                ("a94806d8-71bb-4eb8-987b-bdce6ca99cb8", "states", 0),
                ("d0ea4afa-4231-4a3d-b1db-03655738dab8", "source", None),
            ],
        ),
    ],
)
def test_find_references_finds_all_references(
    model: m.MelodyModel, target, expected
) -> None:
    target_obj = model.by_uuid(target)

    found_with_uuid = sorted(
        (getattr(obj, "uuid", None), attr, idx)
        for obj, attr, idx in model.find_references(target)
    )
    found_with_object = sorted(
        (getattr(obj, "uuid", None), attr, idx)
        for obj, attr, idx in model.find_references(target_obj)
    )

    assert found_with_uuid == found_with_object
    assert target not in found_with_uuid
    assert found_with_uuid == expected


def test_ElementList_filter_by_name(model: m.MelodyModel):
    cap = model.oa.all_capabilities.by_name("Eat food")
    assert cap.uuid == "3b83b4ba-671a-4de8-9c07-a5c6b1d3c422"
    assert cap.name == "Eat food"


def test_ElementList_filter_contains(model: m.MelodyModel):
    caps = model.oa.all_capabilities
    assert "3b83b4ba-671a-4de8-9c07-a5c6b1d3c422" in caps.by_uuid
    assert "Eat food" in caps.by_name
    assert "This capability does not exist" not in caps.by_name

    involvements = model.oa.all_processes.by_uuid(
        "d588e41f-ec4d-4fa9-ad6d-056868c66274"
    ).involved
    assert "OperationalActivity" in involvements.by_class
    assert "OperationalCapability" not in involvements.by_class
    assert "LogicalComponent" not in involvements.by_class


def test_ElementList_filter_iter(model: m.MelodyModel):
    caps = model.oa.all_capabilities
    assert sorted(i.name for i in caps) == sorted(caps.by_name)


def test_ElementList_filter_by_type(model: m.MelodyModel):
    diags = model.diagrams.by_type("OCB")
    assert len(diags) == 1
    assert diags[0].type is m.DiagramType.OCB


@pytest.mark.parametrize(
    "filter_arg",
    [
        pytest.param(mm.oa.Entity, id="type-object"),
        pytest.param("Entity", id="type-name"),
        pytest.param((mm.oa.NS, "Entity"), id="classname-tuple"),
    ],
)
def test_filtering_lists_by_the_only_contained_class_doesnt_change_the_content(
    model: m.MelodyModel, filter_arg
) -> None:
    pkg = model.oa.entity_pkg
    assert pkg is not None
    base = pkg.entities
    base_ids = [i.uuid for i in base]
    assert all(type(i) is mm.oa.Entity for i in base)

    filtered = base.by_class(filter_arg)
    filtered_ids = [i.uuid for i in filtered]

    assert filtered_ids == base_ids


def test_filtering_dotted_names_filters_on_nested_attributes(
    model: m.MelodyModel,
) -> None:
    base = model.la.all_component_exchanges
    assert len(base) > 1
    expected = [
        "c31491db-817d-44b3-a27c-67e9cc1e06a2",  # Care
    ]
    assert {i.uuid for i in base} >= set(expected)

    filtered = base.by_target.parent.name("Whomping Willow")

    assert isinstance(filtered, m.ElementList)
    found = [i.uuid for i in filtered]
    assert found == expected


def test_filtering_on_list_attributes_returns_match_if_any_member_matches(
    model: m.MelodyModel,
) -> None:
    base = model.la.all_components
    willow = model.by_uuid("3bdd4fa2-5646-44a1-9fa6-80c68433ddb7")
    expected = [willow.parent.uuid]

    filtered = base.by_components(willow)

    assert isinstance(filtered, m.ElementList)
    found = [i.uuid for i in filtered]
    assert found == expected


def test_ElementList_dictlike_getitem(model: m.MelodyModel):
    obj = model.search("LogicalComponent").by_name("Whomping Willow")
    assert isinstance(obj, mm.la.LogicalComponent)

    result = obj.property_value_groups["Stats"]["WIS"]

    assert result == 150


def test_ElementList_dictlike_setitem(model: m.MelodyModel):
    obj = model.search("LogicalComponent").by_name("Whomping Willow")
    assert isinstance(obj, mm.la.LogicalComponent)
    pv_obj = obj.property_values.by_name("cars_defeated")

    obj.property_values["cars_defeated"] += 1

    assert pv_obj.value == 2


def test_MixedElementList_filter_by_type(model: m.MelodyModel):
    process = model.by_uuid("d588e41f-ec4d-4fa9-ad6d-056868c66274")
    assert isinstance(process, mm.oa.OperationalProcess)

    involvements = process.involved
    acts = involvements.by_class("OperationalActivity")
    fexs = involvements.by_class("FunctionalExchange")

    assert len(involvements) == 7
    assert len(acts) == 4
    assert len(fexs) == 3


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("uuid", "3b83b4ba-671a-4de8-9c07-a5c6b1d3c422"),
        ("__class__", mm.oa.OperationalCapability),
        ("name", "Eat food"),
        (
            "description",
            "<p>Actors with this capability are able to ingest edibles.</p>\n",
        ),
        ("summary", "You need to eat food in order to write good code!"),
        ("progress_status", "TO_BE_DISCUSSED"),
    ],
)
def test_ModelElement_attrs(model: m.MelodyModel, key: str, value: str):
    elm = model.oa.all_capabilities.by_name("Eat food")
    assert getattr(elm, key) == value


def test_ModelElement_has_diagrams(model: m.MelodyModel):
    elm = model.oa.all_capabilities.by_name("Eat food")
    assert isinstance(elm, mm.oa.OperationalCapability)
    assert hasattr(elm, "diagrams")
    assert len(elm.diagrams) == 0


def test_ModelElement_has_pvmt(model: m.MelodyModel):
    elm = model.oa.all_capabilities.by_name("Eat food")

    elm.pvmt  # noqa: B018


def test_ModelElement_has_progress_status(model: m.MelodyModel):
    elm = model.oa.all_capabilities[0]
    assert elm.progress_status == "NOT_SET"


def test_Capabilities_have_constraints(model: m.MelodyModel):
    elm = model.oa.all_capabilities.by_name("Eat food")
    assert isinstance(elm, mm.oa.OperationalCapability)
    assert hasattr(elm, "constraints")
    assert len(elm.constraints) == 3


def test_SystemCapability_has_realized_capabilities(model: m.MelodyModel):
    elm = model.by_uuid("9390b7d5-598a-42db-bef8-23677e45ba06")
    assert isinstance(elm, mm.sa.Capability)

    assert hasattr(elm, "realized_capabilities")
    assert len(elm.realized_capabilities) == 2
    cap = elm.realized_capabilities[0]
    assert type(cap) is mm.oa.OperationalCapability


def test_Capability_of_logical_layer_has_realized_capabilities(
    model: m.MelodyModel,
):
    elm = model.by_uuid("b80b3141-a7fc-48c7-84b2-1467dcef5fce")
    assert isinstance(elm, mm.la.CapabilityRealization)

    assert hasattr(elm, "realized_capabilities")
    assert len(elm.realized_capabilities) == 1
    cap = elm.realized_capabilities[0]
    assert type(cap) is mm.sa.Capability


def test_Capabilities_conditions_markup_escapes(model: m.MelodyModel):
    elm = model.by_uuid("53c58b24-3938-4d6a-b84a-bb9bff355a41")
    assert isinstance(elm, mm.oa.OperationalCapability)
    expected = (
        f"The actor lives in a world where predators exist{os.linesep}"
        f"AND{os.linesep}"
        'A <a href="hlink://e6e4d30c-4d80-4899-8d8d-1350239c15a7">Predator</a>'
        " is near the actor"
    )

    assert elm.precondition is not None
    spec = elm.precondition.specification
    assert markupsafe.escape(spec) == expected


@pytest.mark.parametrize(
    "uuid",
    [
        pytest.param(
            "53c58b24-3938-4d6a-b84a-bb9bff355a41", id="OperationalCapability"
        ),
        pytest.param(
            "b80b3141-a7fc-48c7-84b2-1467dcef5fce", id="CapabilityRealization"
        ),
        pytest.param("9390b7d5-598a-42db-bef8-23677e45ba06", id="Capability"),
        pytest.param(
            "22b9c1d6-a754-4614-9fcb-fa4f53837d9a", id="FunctionalChain"
        ),
        pytest.param(
            "d588e41f-ec4d-4fa9-ad6d-056868c66274", id="OperationalProcess"
        ),
        pytest.param("d32922dc-2686-4434-a5f5-9374c124b88c", id="Scenario"),
    ],
)
def test_model_elements_have_pre_or_post_conditions(
    model: m.MelodyModel, uuid: str
):
    elm = model.by_uuid(uuid)

    condition = elm.precondition or elm.postcondition

    assert condition
    spec = condition.specification
    assert spec["capella:linkedText"]


@pytest.mark.parametrize(
    ("uuid", "trg_uuid"),
    [
        pytest.param(
            "3b83b4ba-671a-4de8-9c07-a5c6b1d3c422",
            "83d1334f-6180-46c4-a80d-6839341df688",
            id="oa",
        ),
        pytest.param(
            "9390b7d5-598a-42db-bef8-23677e45ba06",
            "562c5128-5acd-45cc-8b49-1d8d686f450a",
            id="sa",
        ),
    ],
)
def test_CapabilityExtend(model: m.MelodyModel, uuid: str, trg_uuid: str):
    cap = model.by_uuid(uuid)
    assert isinstance(cap, mm.interaction.AbstractCapability)
    expected = model.by_uuid(trg_uuid)
    assert isinstance(expected, mm.interaction.AbstractCapability)

    actual = [i.extended for i in cap.extends]

    assert expected in actual


@pytest.mark.parametrize(
    ("uuid", "trg_uuid"),
    [
        pytest.param(
            "53c58b24-3938-4d6a-b84a-bb9bff355a41",
            "83d1334f-6180-46c4-a80d-6839341df688",
            id="oa",
        ),
        pytest.param(
            "9390b7d5-598a-42db-bef8-23677e45ba06",
            "9390b7d5-598a-42db-bef8-23677e45ba06",
            id="sa",
        ),
    ],
)
def test_CapabilityInclude(model: m.MelodyModel, uuid: str, trg_uuid: str):
    cap = model.by_uuid(uuid)
    assert isinstance(cap, mm.interaction.AbstractCapability)
    expected = model.by_uuid(trg_uuid)
    assert isinstance(expected, mm.interaction.AbstractCapability)

    actual = [i.included for i in cap.includes]

    assert expected in actual


@pytest.mark.parametrize(
    ("uuid", "trg_uuid"),
    [
        pytest.param(
            "30bd2c21-b170-40d3-b476-7c2016b58031",
            "84adfa3f-11c9-43d1-801c-b1535fcba802",
            id="oa",
        ),
        pytest.param(
            "9390b7d5-598a-42db-bef8-23677e45ba06",
            "562c5128-5acd-45cc-8b49-1d8d686f450a",
            id="sa",
        ),
    ],
)
def test_CapabilityGeneralization(
    model: m.MelodyModel, uuid: str, trg_uuid: str
):
    cap = model.by_uuid(uuid)
    assert isinstance(cap, mm.interaction.AbstractCapability)
    expected = model.by_uuid(trg_uuid)
    assert isinstance(expected, mm.interaction.AbstractCapability)

    actual = [i.super for i in cap.generalizations]

    assert expected in actual


@pytest.mark.parametrize(
    ("uuid", "real_uuid", "real_attr"),
    [
        pytest.param(
            "99df05af-71bf-4233-9035-bcd3d4439182",
            "1eee3b81-41ef-4b56-8018-b8e421a5a2bc",
            "realizing_system_functions",
            id="Realizing SystemFunctions",
        ),
        pytest.param(
            "00e7b925-cf4c-4cb0-929e-5409a1cd872b",
            "f708bc29-d69f-42a0-90cc-11fc01054cd0",
            "realizing_logical_functions",
            id="Realizing LogicalFunctions",
        ),
        pytest.param(
            "b805a725-4b13-4b77-810e-b0ba002d5d98",
            "d4a22478-5717-4ca7-bfc9-9a193e6218a8",
            "realizing_system_components",
            id="Realizing SystemComponents",
        ),
        pytest.param(
            "230c4621-7e0a-4d0a-9db2-d4ba5e97b3df",
            "0d2edb8f-fa34-4e73-89ec-fb9a63001440",
            "realizing_logical_components",
            id="Realizing LogicalComponents",
        ),
        pytest.param(
            "83d1334f-6180-46c4-a80d-6839341df688",
            "9390b7d5-598a-42db-bef8-23677e45ba06",
            "realizing_capabilities",
            id="Realizing SystemCapabilities",
        ),
        pytest.param(
            "562c5128-5acd-45cc-8b49-1d8d686f450a",
            "b80b3141-a7fc-48c7-84b2-1467dcef5fce",
            "realizing_capabilities",
            id="Realizing LogicalCapabilities",
        ),
    ],
)
def test_realizing_links(
    model: m.MelodyModel, uuid: str, real_uuid: str, real_attr: str
):
    elm = model.by_uuid(uuid)
    real = model.by_uuid(real_uuid)

    assert hasattr(elm, real_attr)
    assert real in getattr(elm, real_attr)


class TestStateMachines:
    def test_stm_accessible_from_component_pkg(self, model: m.MelodyModel):
        comp = model.by_uuid("ecb687c1-c540-4de6-8b1d-024d1ed0178f")
        assert isinstance(comp, mm.sa.SystemComponentPkg)
        stm = comp.state_machines.by_uuid(
            "9806df59-397c-4505-918f-3b1288638251"
        )

        assert stm.name == "RootStateMachine"

    def test_stm_has_regions(self, model: m.MelodyModel):
        entity = model.oa.all_entities.by_name("Functional Human Being")
        assert isinstance(entity, mm.oa.Entity)
        state_machine = entity.state_machines[0]

        assert hasattr(state_machine, "regions")
        assert len(state_machine.regions) == 1

    def test_stm_region(self, model: m.MelodyModel):
        entity = model.oa.all_entities.by_name("Functional Human Being")
        assert isinstance(entity, mm.oa.Entity)
        region = entity.state_machines[0].regions[0]

        assert len(region.states) == 12
        assert len(region.transitions) == 14

    def test_stm_state_mode_regions_well_defined(self, model: m.MelodyModel):
        mode = model.by_uuid("91dc2eec-c878-4fdb-91d8-8f4a4527424e")
        assert isinstance(mode, mm.capellacommon.Mode)

        assert hasattr(mode, "regions")
        assert len(mode.regions) == 1
        assert len(mode.regions[0].states) > 0

    def test_stm_transition_attributes_well_defined(
        self, model: m.MelodyModel
    ):
        transition = model.by_uuid("a78cf778-0476-4e08-a3a3-c115dca55dd1")
        assert isinstance(transition, mm.capellacommon.StateTransition)

        assert hasattr(transition, "source")
        assert transition.source is not None
        assert transition.source.name == "Cooking"

        assert hasattr(transition, "target")
        assert transition.target is not None
        assert transition.target.name == "Eating"

        assert hasattr(transition, "guard")
        assert transition.guard is not None
        assert isinstance(
            transition.guard.specification,
            mm.information.datavalue.OpaqueExpression,
        )
        assert transition.guard.specification["LinkedText"] == "Food is cooked"

        assert hasattr(transition, "triggers")
        assert transition.triggers is not None
        assert len(transition.triggers) == 1

        assert hasattr(transition, "effect")
        assert transition.effect is not None
        assert list(transition.effect.by_name) == ["good advise", "Make Food"]

    def test_stm_transition_multiple_guards(self, model: m.MelodyModel):
        transition = model.by_uuid("6781fb18-6dd1-4b01-95f7-2f896316e46c")
        assert isinstance(transition, mm.capellacommon.StateTransition)

        assert transition.guard is not None
        assert isinstance(
            transition.guard.specification,
            mm.information.datavalue.OpaqueExpression,
        )
        assert (
            transition.guard.specification["LinkedText"]
            == "Actor feels hungry"
        )
        assert transition.guard.specification["Python"] == "self.hunger >= 0.8"

    def test_stm_region_has_access_to_diagrams(self, model: m.MelodyModel):
        default_region = model.by_uuid("eeeb98a7-6063-4115-8b4b-40a51cc0df49")
        assert isinstance(default_region, mm.capellacommon.Region)
        state = default_region.states.by_uuid(
            "0c7b7899-49a7-4e41-ab11-eb7d9c2becf6"
        )
        assert isinstance(state, mm.capellacommon.State)

        assert default_region.diagrams
        assert isinstance(default_region.diagrams, m.ElementList)
        assert (
            default_region.diagrams[0].name
            == "[MSM] States of Functional Human Being"
        )


def test_exchange_items_of_a_function_port(model: m.MelodyModel):
    port = model.by_uuid("db64f0c9-ea1c-4962-b043-1774547c36f7")
    assert "good advise" in port.exchange_items.by_name
    assert "not so good advise" in port.exchange_items.by_name
    assert len(port.exchange_items) == 2


def test_exchange_items_on_logical_function_exchanges(model: m.MelodyModel):
    exchange = model.la.all_function_exchanges.by_uuid(
        "cdc69c5e-ddd8-4e59-8b99-f510400650aa"
    )
    assert isinstance(exchange, mm.fa.FunctionalExchange)
    item = exchange.exchanged_items.by_name("ExchangeItem 3")
    assert isinstance(item, mm.information.ExchangeItem)

    assert item.exchange_mechanism.name == "SHARED_DATA"
    assert exchange in item.exchanges


def test_exchange_items_on_logical_actor_exchanges(model: m.MelodyModel):
    aex = model.la.all_actor_exchanges.by_uuid(
        "9cbdd233-aff5-47dd-9bef-9be1277c77c3"
    )
    cex_item = aex.exchange_items.by_name("ExchangeItem 2")

    assert cex_item.exchange_mechanism.name == "FLOW"
    assert aex in cex_item.exchanges


def test_exchange_items_on_logical_component_exchanges(model: m.MelodyModel):
    cex = model.la.all_component_exchanges.by_uuid(
        "c31491db-817d-44b3-a27c-67e9cc1e06a2"
    )
    cex_item = cex.exchange_items.by_name("ExchangeItem 1")

    assert cex_item.exchange_mechanism.name == "EVENT"
    assert cex in cex_item.exchanges


@pytest.mark.parametrize(
    ("name", "is_actor", "is_human"),
    [
        ("Prof. S. Snape", True, True),
        ("Whomping Willow", False, True),
        ("Harry J. Potter", True, False),
        ("Hogwarts", False, False),
    ],
)
def test_component_is_human_is_actor(
    name: str, is_actor: bool, is_human: bool, model: m.MelodyModel
) -> None:
    actor = model.la.all_components.by_name(name)

    assert actor.is_actor == is_actor
    assert actor.is_human == is_human


def test_constraint_links_to_constrained_elements(
    model: m.MelodyModel,
) -> None:
    con = model.by_uuid("039b1462-8dd0-4bfd-a52d-0c6f1484aa6e")
    celt = model.by_uuid("3b83b4ba-671a-4de8-9c07-a5c6b1d3c422")

    assert isinstance(con, mm.capellacore.Constraint)
    assert len(con.constrained_elements) == 1
    assert con.constrained_elements[0] == celt


def test_constraint_specification_has_linked_object_name_in_body(
    model: m.MelodyModel,
) -> None:
    uuid = "dd2d0dab-a35f-4104-91e5-b412f35cba15"
    con = model.by_uuid("039b1462-8dd0-4bfd-a52d-0c6f1484aa6e")
    expected_linked_text = f'<a href="hlink://{uuid}">Hunted animal</a>'

    assert isinstance(con, mm.capellacore.Constraint)
    assert isinstance(
        con.specification, mm.information.datavalue.OpaqueExpression
    )
    assert con.specification["LinkedText"] == expected_linked_text


class TestAttrProxyAccessor:
    @staticmethod
    def test_function_is_available_in_state(model: m.MelodyModel) -> None:
        function = model.by_uuid("957c5799-1d4a-4ac0-b5de-33a65bf1519c")

        states = function.available_in_states

        assert "Open" in states.by_name
        assert len(states) == 1

    @staticmethod
    def test_available_in_states_can_be_modified(model: m.MelodyModel) -> None:
        function = model.by_uuid("957c5799-1d4a-4ac0-b5de-33a65bf1519c")
        new_state = model.by_uuid("53cab5f0-fe2f-4553-8223-fbe5ea9e4d42")
        assert len(function.available_in_states) == 1

        old_state = function.available_in_states.pop()
        function.available_in_states.append(new_state)

        assert len(function.available_in_states) == 1
        assert new_state in function.available_in_states
        assert old_state not in function.available_in_states


def test_specification_linkedText_to_internal_linkedText_transformation(
    model: m.MelodyModel,
) -> None:
    c1 = model.by_uuid("039b1462-8dd0-4bfd-a52d-0c6f1484aa6e")
    assert isinstance(c1, mm.capellacore.Constraint)
    c2 = model.by_uuid("0b546f8b-408c-4520-9f6a-f77efe97640b")
    assert isinstance(c2, mm.capellacore.Constraint)
    assert isinstance(
        c1.specification, mm.information.datavalue.OpaqueExpression
    )
    assert isinstance(
        c2.specification, mm.information.datavalue.OpaqueExpression
    )

    c2.specification["LinkedText"] = c1.specification["LinkedText"]

    assert (
        next(c1.specification._element.iterchildren("bodies")).text
        == next(c2.specification._element.iterchildren("bodies")).text
    )


@pytest.mark.parametrize(
    "searchkey",
    [
        mm.information.Class,
        "org.polarsys.capella.core.data.information:Class",
        "Class",
    ],
)
def test_model_search_finds_elements(
    session_shared_model: m.MelodyModel, searchkey
):
    expected = {
        # Classes
        "0fef2887-04ce-4406-b1a1-a1b35e1ce0f3",
        "1adf8097-18f9-474e-b136-6c845fc6d9e9",
        "2a923851-a4ca-4fd2-a4b3-302edb8ac178",
        "2b34c799-769c-42f2-8a1b-4533dba209a0",
        "3eb1833e-7a42-4297-8ee0-88cdc5fd6025",
        "7a3bdb81-b58f-46c7-a639-18298acc1a53",
        "8164ae8b-36d5-4502-a184-5ec064db4ec3",
        "959b5222-7717-4ee9-bd3a-f8a209899464",
        "a7ecc231-c55e-4ab9-ae14-9558e3ec2a34",
        "ad876857-33d3-4f2e-9fe2-71545a78352d",
        "bbc296e1-ed4c-40cf-b37d-c8eb8613228a",
        "c371cebb-8021-4a38-8706-4525734de76d",
        "c3c96805-d6f6-4092-b9f4-df7970651cdc",
        "c5ea0585-7657-4764-9eb2-3a6584980ce6",
        "c710f1c2-ede6-444e-9e2b-0ff30d7fd040",
        "c89849fd-0643-4708-a4da-74c9ea9ca7b1",
        "ca79bf38-5e82-4104-8c49-e6e16b3748e9",
        "d2b4a93c-73ef-4f01-8b59-f86c074ec521",
        "ed272baf-43f2-4fa1-ad50-49c00563258b",
        # Unions
        "246ab250-2a80-487f-b022-1123c02e33ff",
        "2f34192f-088b-4511-95ea-b1a29fb6028b",
        "31c5c280-64e1-4d11-b874-412966aa547c",
        "be06f4a0-aff2-4475-a8a8-766e5fa26006",
    }

    found = session_shared_model.search(searchkey)
    actual = {i.uuid for i in found}

    assert actual == expected


def test_model_search_below_filters_elements_by_ancestor(
    session_shared_model: m.MelodyModel,
):
    parent = session_shared_model.by_uuid(
        "6583b560-6d2f-4190-baa2-94eef179c8ea"
    )
    expected = {
        "3bdd4fa2-5646-44a1-9fa6-80c68433ddb7",
        "a58821df-c5b4-4958-9455-0d30755be6b1",
    }

    nested = session_shared_model.search("LogicalComponent", below=parent)

    actual = {i.uuid for i in nested}
    assert actual == expected


def test_model_search_does_not_contain_duplicates(
    session_shared_model: m.MelodyModel,
) -> None:
    results = session_shared_model.search()
    uuids = sorted(i.uuid for i in results)
    uuids_dedup = sorted(set(uuids))

    assert len(uuids) > 0
    assert len(uuids) == len(uuids_dedup)


def test_CommunicationMean(model: m.MelodyModel) -> None:
    comm = model.by_uuid("6638ccd2-61cc-481e-bb23-4c1b147e1dbc")
    env = model.by_uuid("e37510b9-3166-4f80-a919-dfaac9b696c7")
    fhb = model.by_uuid("a8c42033-fdf2-458f-bae9-1cfd1207c49f")
    wood = model.by_uuid("eaf42597-4327-419f-b9f2-d04957f93f47")
    cmd = model.by_uuid("571d093a-a87e-4dfc-9f46-62eb7c374f44")

    assert comm.source == env
    assert comm.target == fhb
    assert wood in comm.allocated_interactions
    assert cmd in comm.convoyed_informations


@pytest.mark.parametrize(
    ("chain_uuid", "link_uuid", "target_uuid"),
    [
        pytest.param(
            "d588e41f-ec4d-4fa9-ad6d-056868c66274",
            "41e2ff3c-bc49-4eb1-ace9-66920b21179d",
            "55b90f9a-c5af-47fc-9c1c-48090414d1f1",
            id="OperationalProcess",
        ),
        pytest.param(
            "dfc4341d-253a-4ae9-8a30-63a9d9faca39",
            "7311e58e-9500-4c72-9620-aac32e4a1458",
            "1a414995-f4cd-488c-8152-486e459fb9de",
            id="FunctionalChain",
        ),
    ],
)
def test_FunctionalChainInvolvementLink_has_items_and_context(
    model: m.MelodyModel,
    chain_uuid: str,
    link_uuid: str,
    target_uuid: str,
) -> None:
    chain = model.by_uuid(chain_uuid)
    link = model.by_uuid(link_uuid)
    target = model.by_uuid(target_uuid)
    ex_item_uuids = [ex.uuid for ex in link.exchanged_items]
    expected_uuids = ["1ca7b206-be29-4315-a036-0b532b26a191"]
    expected_context = "This is a test context."

    assert link in chain.involvements
    assert ex_item_uuids == expected_uuids
    spec = markupsafe.escape(link.exchange_context.specification)
    assert spec.startswith(expected_context)
    assert link.involved == target


@pytest.mark.parametrize(
    ("trace_uuid", "target_uuid"),
    [
        (
            "9f84f273-1af4-49c2-a9f1-143e94ab816b",
            "ed272baf-43f2-4fa1-ad50-49c00563258b",
        ),
        (
            "0880af85-4f96-4a77-b588-2e7a0385629d",
            "01788b49-ccef-4a37-93d2-119287f8dd53",
        ),
    ],
)
def test_ModelElement_has_GenericTraces(
    model: m.MelodyModel, trace_uuid: str, target_uuid: str
) -> None:
    cls = model.by_uuid("ad876857-33d3-4f2e-9fe2-71545a78352d")
    trace = model.by_uuid(trace_uuid)

    assert trace in cls.traces
    assert trace.target.uuid == target_uuid


@pytest.mark.parametrize(
    ("chain_uuid", "fnc_uuid", "target_uuid"),
    [
        pytest.param(
            "d588e41f-ec4d-4fa9-ad6d-056868c66274",
            "8e732f5a-a760-468c-b862-ba1a276206d1",
            "8bcb11e6-443b-4b92-bec2-ff1d87a224e7",
            id="OperationalProcess",
        ),
        pytest.param(
            "dfc4341d-253a-4ae9-8a30-63a9d9faca39",
            "28208081-40b1-4030-b341-f75374095717",
            "ceffa011-7b66-4b3c-9885-8e075e312ffa",
            id="FunctionalChain",
        ),
    ],
)
def test_FunctionalChainInvolvementFunction_appears_in_chain_involvements(
    model: m.MelodyModel,
    chain_uuid: str,
    fnc_uuid: str,
    target_uuid: str,
) -> None:
    chain = model.by_uuid(chain_uuid)
    fnc = model.by_uuid(fnc_uuid)
    target = model.by_uuid(target_uuid)

    assert fnc in chain.involvements
    assert fnc.involved == target


@pytest.mark.parametrize(
    ("chain_uuid", "nodes"),
    [
        pytest.param(
            "d588e41f-ec4d-4fa9-ad6d-056868c66274",
            [
                "b4df5cd8-b2c9-4abb-ba72-c93fb92c9e5c",
                "3fde4705-3ecf-4b7a-ab0e-b983174c5880",
                "e097eaf9-ca3d-4c3e-a4b3-bd1a5430bd8b",
            ],
            id="OperationalProcess",
        ),
        pytest.param(
            "dfc4341d-253a-4ae9-8a30-63a9d9faca39",
            [
                "764c65e0-f522-4be7-80fa-52f43ccb92bd",
                "75490975-8468-41a0-889b-e37e02296fbd",
                "b26d943c-e201-4636-90d3-937ddb6b3fbe",
                "9075d109-ccaf-436f-bc75-f55030808f0b",
                "8078ec3c-44e4-47da-a4e8-213324a617f5",
                "1a67b667-a1f7-4a2b-9b10-0a82842fe1d6",
                "4efb0021-4588-4e9a-8720-75e884a0f3ac",
                "31f0ac22-ade5-4e77-802e-d920e143ddd8",
                "ef27c81a-6f51-4c73-9768-ef99d0f2f806",
            ],
            id="FunctionalChain",
        ),
    ],
)
def test_FunctionalChainInvolvement_has_sequence_nodes(
    model: m.MelodyModel, chain_uuid: str, nodes: list[str]
) -> None:
    chain = model.by_uuid(chain_uuid)

    actual = list(chain.sequence_nodes.by_uuid)

    assert actual == nodes


class TestArchitectureLayers:
    @pytest.mark.parametrize(
        ("layer", "definitions"),
        [
            pytest.param(
                "oa",
                [
                    "activity_pkg",
                    "capability_pkg",
                    "interface_pkg",
                    "data_pkg",
                    "entity_pkg",
                    "all_activities",
                    "all_processes",
                    "all_capabilities",
                    "all_interfaces",
                    "all_classes",
                    "all_actors",
                    "all_entities",
                    "all_activity_exchanges",
                    "all_entity_exchanges",
                ],
                id="oa",
            ),
            pytest.param(
                "sa",
                [
                    "root_component",
                    "root_function",
                    "function_pkg",
                    "capability_pkg",
                    "interface_pkg",
                    "data_pkg",
                    "component_pkg",
                    "mission_pkg",
                    "all_functions",
                    "all_capabilities",
                    "all_interfaces",
                    "all_classes",
                    "all_actors",
                    "all_components",
                    "all_missions",
                    "all_actor_exchanges",
                    "component_exchanges",
                    "all_component_exchanges",
                    "all_function_exchanges",
                    "all_component_exchanges",
                ],
                id="sa",
            ),
            pytest.param(
                "la",
                [
                    "root_component",
                    "root_function",
                    "function_pkg",
                    "capability_pkg",
                    "interface_pkg",
                    "data_pkg",
                    "component_pkg",
                    "all_functions",
                    "all_capabilities",
                    "all_interfaces",
                    "all_classes",
                    "all_actors",
                    "all_components",
                    "all_actor_exchanges",
                    "all_component_exchanges",
                    "all_function_exchanges",
                    "all_component_exchanges",
                ],
                id="la",
            ),
            pytest.param(
                "pa",
                [
                    "root_component",
                    "root_function",
                    "function_pkg",
                    "capability_pkg",
                    "interface_pkg",
                    "data_pkg",
                    "component_pkg",
                    "all_functions",
                    "all_capabilities",
                    "all_interfaces",
                    "all_classes",
                    "all_actors",
                    "all_components",
                    "all_component_exchanges",
                    "all_function_exchanges",
                    "all_physical_exchanges",
                    "all_physical_links",
                    "all_physical_paths",
                ],
                id="pa",
            ),
        ],
    )
    def test_ArchitectureLayers_have_root_definitions(
        self,
        model: m.MelodyModel,
        layer: str,
        definitions: t.Sequence[str],
    ) -> None:
        layer = getattr(model, layer)

        for attr in definitions:
            assert hasattr(layer, attr)

        assert hasattr(layer, "diagrams")

    @pytest.mark.parametrize(
        ("nature", "uuid"),
        [
            ("UNSET", "b9f9a83c-fb02-44f7-9123-9d86326de5f1"),
            ("NODE", "8a6d68c8-ac3d-4654-a07e-ada7adeed09f"),
            ("BEHAVIOR", "7b188ad0-0d82-4b2c-9913-45292e537871"),
        ],
    )
    def test_PhysicalComponent_has_nature_attribute(
        self, model: m.MelodyModel, nature: str, uuid: str
    ) -> None:
        pcomp = model.by_uuid(uuid)

        assert hasattr(pcomp, "nature")
        assert pcomp.nature == nature

    @pytest.mark.parametrize(
        ("kind", "uuid"),
        [
            ("UNSET", "8a6d68c8-ac3d-4654-a07e-ada7adeed09f"),
            ("HARDWARE", "a2c7f619-b38a-4b92-94a5-cbaa631badfc"),
            ("PROCESSES", "9e7ab9da-a7e2-4d19-8629-22d2a7edf42f"),
            (
                "SOFTWARE_DEPLOYMENT_UNIT",
                "b327d900-abd2-4138-a111-9ff0684739d8",
            ),
            ("DATA", "23c47b69-7352-481d-be88-498fb351adbe"),
            ("HARDWARE_COMPUTER", "c78b5d7c-be0c-4ed4-9d12-d447cb39304e"),
            ("SERVICES", "7b188ad0-0d82-4b2c-9913-45292e537871"),
            (
                "SOFTWARE_EXECUTION_UNIT",
                "db2d86d7-48ee-478b-a6fc-d6387ab0032e",
            ),
            ("FACILITIES", "3d68852d-fcc0-452c-af12-a2fbe22f81fa"),
            ("MATERIALS", "f5d7980d-e1e9-4515-8bb0-be7e80ac5839"),
            ("SOFTWARE", "74067f56-33bf-47f5-bb8b-f3604097f653"),
            ("FIRMWARE", "793e6da2-d019-4716-a5c5-af8ad550ca5e"),
            ("PERSON", "8a6c6ec9-095d-4d8b-9728-69bc79af5f27"),
            ("SOFTWARE_APPLICATION", "e2acdad7-ef1d-4cbd-93ae-2dcfcbced6e5"),
        ],
    )
    def test_PhysicalComponent_has_kind_attribute(
        self, model: m.MelodyModel, kind: str, uuid: str
    ) -> None:
        pcomp = model.by_uuid(uuid)

        assert hasattr(pcomp, "kind")
        assert pcomp.kind == kind

    def test_PhysicalComponent_vehicle_component_chain(
        self, model: m.MelodyModel
    ) -> None:
        vehicle = model.by_uuid("b327d900-abd2-4138-a111-9ff0684739d8")
        sensor_comp = model.by_uuid("3f416925-9d8a-4e9c-99f3-e912efb23d2f")
        equip_comp = model.by_uuid("3d68852d-fcc0-452c-af12-a2fbe22f81fa")
        cam_ass = model.by_uuid("5bfc516b-c20d-4007-9a38-5ba0e889d0a4")
        net_switch = model.by_uuid("b51ccc6f-5f96-4e28-b90e-72463a3b50cf")
        server = model.by_uuid("9137f463-7497-40c2-b20a-897158fdba9a")
        cam_fw = model.by_uuid("db2d86d7-48ee-478b-a6fc-d6387ab0032e")
        switch_fw = model.by_uuid("c78b5d7c-be0c-4ed4-9d12-d447cb39304e")
        switch_conf = model.by_uuid("23c47b69-7352-481d-be88-498fb351adbe")
        comp_card1 = model.by_uuid("63be604e-883e-41ea-9023-fc74f29906fe")
        comp_card2 = model.by_uuid("3a982128-3281-4d37-8838-a6058b7a25d9")
        card_1_os = model.by_uuid("7b188ad0-0d82-4b2c-9913-45292e537871")
        cool_fan = model.by_uuid("65e82f3f-c5b7-44c1-bfea-8e20bb0230be")
        card_2_os = model.by_uuid("09e19313-c824-467f-9fb5-95ed8b4e2d51")
        cam_driver = model.by_uuid("74067f56-33bf-47f5-bb8b-f3604097f653")
        app1 = model.by_uuid("b80a6fcc-8d35-4675-a2e6-60efcbd61e27")
        app2 = model.by_uuid("ca5af12c-5259-4844-aaac-9ca9f84aa90b")

        assert sensor_comp in vehicle.related_components
        assert equip_comp in vehicle.related_components
        assert len(sensor_comp.related_components) == 1
        assert sensor_comp.related_components[0] == cam_ass
        assert net_switch in equip_comp.related_components
        assert server in equip_comp.related_components
        assert len(cam_ass.related_components) == 1
        assert cam_ass.related_components[0] == cam_fw
        assert switch_fw in net_switch.related_components
        assert switch_conf in net_switch.related_components
        assert comp_card1 in server.related_components
        assert comp_card2 in server.related_components
        assert card_1_os in comp_card1.related_components
        assert cool_fan in comp_card1.related_components
        assert len(comp_card2.related_components) == 1
        assert comp_card2.related_components[0] == card_2_os
        assert cam_driver in card_1_os.related_components
        assert app1 in card_1_os.related_components
        assert len(card_2_os.related_components) == 1
        assert card_2_os.related_components[0] == app2

    def test_PhysicalComponent_deploying_components(
        self, model: m.MelodyModel
    ) -> None:
        comp_card1 = model.by_uuid("63be604e-883e-41ea-9023-fc74f29906fe")
        card1_os = model.by_uuid("7b188ad0-0d82-4b2c-9913-45292e537871")

        assert card1_os in comp_card1.deployed_components
        assert comp_card1 in card1_os.deploying_components

    def test_physical_path_is_found(self, model: m.MelodyModel) -> None:
        expected_path = model.by_uuid("42c5ffb3-29b3-4580-a061-8f76833a3d37")
        assert expected_path in model.pa.all_physical_paths

    def test_pa_component_exchange_is_found(
        self, model: m.MelodyModel
    ) -> None:
        expected_exchange = model.by_uuid(
            "3aa006b1-f954-4e8f-a4e9-2e9cd38555de"
        )
        assert expected_exchange in model.pa.all_component_exchanges

    @pytest.mark.parametrize(
        ("uuid", "port_attr", "ports", "class_"),
        [
            pytest.param(
                "b51ccc6f-5f96-4e28-b90e-72463a3b50cf",
                "physical_ports",
                3,
                mm.cs.PhysicalPort,
                id="PP",
            ),
            pytest.param(
                "c78b5d7c-be0c-4ed4-9d12-d447cb39304e",
                "ports",
                3,
                mm.fa.ComponentPort,
                id="CP",
            ),
        ],
    )
    def test_PhysicalComponent_finds_ports(
        self,
        model: m.MelodyModel,
        uuid: str,
        port_attr: str,
        ports: int,
        class_: type,
    ) -> None:
        comp = model.by_uuid(uuid)
        port_list = getattr(comp, port_attr)

        assert ports == len(port_list)
        for p in port_list:
            assert isinstance(p, class_)

    def test_ComponentExchange_has_allocating_FunctionalExchange(
        self, model: m.MelodyModel
    ) -> None:
        fex = model.by_uuid("df56e23a-d5bd-470c-ac08-aab8d4dad211")
        cex = model.by_uuid("a8c0bb4c-6802-42a9-9ef7-abbd4371f5f8")

        assert fex.allocating_component_exchange == fex.owner == cex

    def test_ComponentExchange_has_allocating_PhysicalLink(
        self, model: m.MelodyModel
    ) -> None:
        cex = model.by_uuid("a647a577-0dc1-454f-917f-ce1c89089a2f")
        assert isinstance(cex, mm.fa.ComponentExchange)
        link = model.by_uuid("90517d41-da3e-430c-b0a9-e3badf416509")
        assert isinstance(link, mm.cs.PhysicalLink)

        assert link in cex.allocating_physical_links

    def test_ComponentExchange_has_allocating_PhysicalPath(
        self, model: m.MelodyModel
    ) -> None:
        path = model.by_uuid("42c5ffb3-29b3-4580-a061-8f76833a3d37")
        cex = model.by_uuid("3aa006b1-f954-4e8f-a4e9-2e9cd38555de")

        assert cex.allocating_physical_paths == [path]


@pytest.mark.parametrize(
    ("attr", "value"),
    [
        ("name", "[MSM] States of Functional Human Being"),
        (
            "description",
            (
                "<p>This diagram shows the states that a Functional Human"
                " Being can have, as well as how it transitions between"
                " them.</p>\n"
            ),
        ),
        (
            "filters",
            {"hide.computed.transitions.filter", "ModelExtensionFilter"},
        ),
        ("target.uuid", "eeeb98a7-6063-4115-8b4b-40a51cc0df49"),
        ("type", "MSM"),
        ("type", m.DiagramType.MSM),
        ("viewpoint", "Common"),
        ("xtype", "viewpoint:DRepresentationDescriptor"),
    ],
)
def test_diagram_attributes(
    model: m.MelodyModel, attr: str, value: t.Any
) -> None:
    diagram = model.diagrams.by_uuid("_7Ft7QKrxEeqOgqWuHJrXFA")
    get_attribute_under_test = operator.attrgetter(attr)

    actual = get_attribute_under_test(diagram)

    assert actual == value


def test_diagram_without_documentation_has_empty_description(
    model: m.MelodyModel,
) -> None:
    diagram = model.diagrams.by_uuid("_KLGoEKyJEeqCdMaqCWkrKg")
    expected = ""

    actual = diagram.description

    assert actual == expected


def test_lists_of_links_appear_to_contain_target_objects(model: m.MelodyModel):
    hogwarts = model.by_uuid("0d2edb8f-fa34-4e73-89ec-fb9a63001440")
    expected = [
        "0e71a0d3-0a18-4671-bba0-71b5f88f95dd",
        "264fb47d-67b7-4bdc-8d06-8a0e5139edbf",
    ]

    actual = [i.uuid for i in hogwarts.allocated_functions]

    assert actual == expected


def test_lists_of_links_cannot_create_objects(model: m.MelodyModel):
    hogwarts = model.by_uuid("0d2edb8f-fa34-4e73-89ec-fb9a63001440")

    with pytest.raises(TypeError, match="create"):
        hogwarts.allocated_functions.create(name="fall to the Death Eaters")


def test_lists_of_links_can_be_appended_to(model: m.MelodyModel):
    hogwarts = model.by_uuid("0d2edb8f-fa34-4e73-89ec-fb9a63001440")
    defend_the_stone = model.by_uuid("4a2a7f3c-d223-4d44-94a7-50dd2906a70c")

    hogwarts.allocated_functions.append(defend_the_stone)

    assert hogwarts.allocated_functions[-1] == defend_the_stone


def test_lists_of_links_can_be_inserted_into(model: m.MelodyModel):
    hogwarts = model.by_uuid("0d2edb8f-fa34-4e73-89ec-fb9a63001440")
    defend_the_stone = model.by_uuid("4a2a7f3c-d223-4d44-94a7-50dd2906a70c")

    hogwarts.allocated_functions.insert(0, defend_the_stone)

    assert hogwarts.allocated_functions[0] == defend_the_stone


def test_lists_of_links_can_be_removed_from(model: m.MelodyModel):
    hogwarts = model.by_uuid("0d2edb8f-fa34-4e73-89ec-fb9a63001440")
    protect_students = model.by_uuid("264fb47d-67b7-4bdc-8d06-8a0e5139edbf")
    assert protect_students in hogwarts.allocated_functions

    hogwarts.allocated_functions.remove(protect_students)

    assert protect_students not in hogwarts.allocated_functions


def test_lists_of_links_reorder_existing_members_when_appending_duplicates(
    model: m.MelodyModel,
):
    parent = model.by_uuid("3b83b4ba-671a-4de8-9c07-a5c6b1d3c422")
    target = model.by_uuid("dfaf473d-257f-4455-90fd-fe9489dac617")
    assert target in parent.involved_activities
    assert target != parent.involved_activities[-1]
    links_before = set(parent.involved_activities._elements)

    parent.involved_activities.append(target)

    count = sum(1 for ia in parent.involved_activities if ia == target)
    assert count == 1
    assert parent.involved_activities[-1] == target
    links_after = set(parent.involved_activities._elements)
    assert links_before == links_after


def test_scenarios_on_functions(model: m.MelodyModel):
    fnc = model.by_uuid("04babdbf-6cf6-4846-a207-bf27cfc8eb32")
    assert isinstance(fnc, mm.oa.OperationalActivity)

    assert fnc.scenarios


def test_related_functions_on_scenarios(model: m.MelodyModel):
    scenario = model.by_uuid("6daa8cf7-6a23-461e-9bf3-abdd8f36c4bc")
    assert isinstance(scenario, mm.interaction.Scenario)

    assert scenario.related_functions
