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

import typing as t

import markupsafe
import pytest

import capellambse
from capellambse.model import MelodyModel, modeltypes
from capellambse.model.crosslayer.capellacommon import (
    Region,
    State,
    StateTransition,
)
from capellambse.model.crosslayer.capellacore import Constraint
from capellambse.model.crosslayer.information import Class
from capellambse.model.layers.ctx import SystemComponentPkg
from capellambse.model.layers.la import CapabilityRealization
from capellambse.model.layers.oa import OperationalCapability

from . import TEST_ROOT


def test_model_info_contains_capella_version(model: MelodyModel):
    assert hasattr(model.info, "capella_version")


def test_model_info_dict_has_capella_version(model: MelodyModel):
    model_info = model.info.as_dict()
    assert model_info.get("capella_version") == "5.0.0"


def test_loading_version_5_succeeds():
    MelodyModel(TEST_ROOT / "5_0" / "MelodyModelTest.aird")


def test_loading_version_one_succeeds():
    MelodyModel(TEST_ROOT / "1_3" / "MelodyModelTest.aird")


def test_ElementList_filter_by_name(model: MelodyModel):
    cap = model.oa.all_capabilities.by_name("Eat food")
    assert cap.uuid == "3b83b4ba-671a-4de8-9c07-a5c6b1d3c422"
    assert cap.name == "Eat food"


def test_ElementList_filter_contains(model: MelodyModel):
    caps = model.oa.all_capabilities
    assert "3b83b4ba-671a-4de8-9c07-a5c6b1d3c422" in caps.by_uuid
    assert "Eat food" in caps.by_name
    assert "This capability does not exist" not in caps.by_name

    involvements = model.oa.all_processes.by_uuid(
        "d588e41f-ec4d-4fa9-ad6d-056868c66274"
    ).involved
    assert "OperationalActivity" in involvements.by_type
    assert "OperationalCapability" not in involvements.by_type
    assert "LogicalComponent" not in involvements.by_type


def test_ElementList_filter_iter(model: MelodyModel):
    caps = model.oa.all_capabilities
    assert sorted(i.name for i in caps) == sorted(caps.by_name)


def test_ElementList_filter_by_type(model: MelodyModel):
    diags = model.diagrams.by_type("OCB")
    assert len(diags) == 1
    assert diags[0].type is modeltypes.DiagramType.OCB


def test_MixedElementList_filter_by_type(model: MelodyModel):
    process = model.oa.all_processes.by_uuid(
        "d588e41f-ec4d-4fa9-ad6d-056868c66274"
    )
    involvements = process.involved
    acts = involvements.by_type("OperationalActivity")
    fexs = involvements.by_type("FunctionalExchange")
    assert len(involvements) == 7
    assert len(acts) == 4
    assert len(fexs) == 3


@pytest.mark.parametrize(
    ["key", "value"],
    [
        ("uuid", "3b83b4ba-671a-4de8-9c07-a5c6b1d3c422"),
        ("xtype", "org.polarsys.capella.core.data.oa:OperationalCapability"),
        ("name", "Eat food"),
        (
            "description",
            "<p>Actors with this capability are able to ingest edibles.</p>\n",
        ),
        ("summary", "You need to eat food in order to write good code!"),
        ("progress_status", "TO_BE_DISCUSSED"),
    ],
)
def test_GenericElement_attrs(model: MelodyModel, key: str, value: str):
    elm = model.oa.all_capabilities.by_name("Eat food")
    assert getattr(elm, key) == value


def test_GenericElement_has_diagrams(model: MelodyModel):
    elm = model.oa.all_capabilities.by_name("Eat food")
    assert hasattr(elm, "diagrams")
    assert len(elm.diagrams) == 0


def test_GenericElement_has_pvmt(model: MelodyModel):
    elm = model.oa.all_capabilities.by_name("Eat food")
    with pytest.raises(
        AttributeError,
        match="^Cannot access PVMT: extension is not loaded$",
    ):
        elm.pvmt


def test_GenericElement_has_progress_status(model: MelodyModel):
    elm = model.oa.all_capabilities[0]
    assert elm.progress_status == "NOT_SET"


def test_Capabilities_have_constraints(model: MelodyModel):
    elm = model.oa.all_capabilities.by_name("Eat food")
    assert hasattr(elm, "constraints")
    assert len(elm.constraints) == 3


def test_SystemCapability_has_realized_capabilities(model: MelodyModel):
    elm: CapabilityRealization = model.by_uuid(  # type: ignore[assignment]
        "9390b7d5-598a-42db-bef8-23677e45ba06"
    )

    assert hasattr(elm, "realized_capabilities")
    assert len(elm.realized_capabilities) == 2
    assert elm.realized_capabilities[0].xtype.endswith("OperationalCapability")


def test_Capability_of_logical_layer_has_realized_capabilities(
    model: MelodyModel,
):
    elm: CapabilityRealization = model.by_uuid(  # type: ignore[assignment]
        "b80b3141-a7fc-48c7-84b2-1467dcef5fce"
    )

    assert hasattr(elm, "realized_capabilities")
    assert len(elm.realized_capabilities) == 1
    assert elm.realized_capabilities[0].xtype.endswith("Capability")


def test_Capabilities_conditions_markup_escapes(model: MelodyModel):
    elm: OperationalCapability = model.by_uuid(  # type: ignore[assignment]
        "53c58b24-3938-4d6a-b84a-bb9bff355a41"
    )
    expected = (
        "The actor lives in a world where predators exist\r\n"
        "AND\r\n"
        'A <a href="hlink://e6e4d30c-4d80-4899-8d8d-1350239c15a7">Predator</a> is near the actor'
    )

    assert markupsafe.escape(elm.precondition.specification) == expected


@pytest.mark.parametrize(
    "uuid,real_uuid,real_attr",
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
    model: MelodyModel, uuid: str, real_uuid: str, real_attr: str
):
    elm = model.by_uuid(uuid)
    real = model.by_uuid(real_uuid)

    assert hasattr(elm, real_attr)
    assert real in getattr(elm, real_attr)


class TestStateMachines:
    def test_stm_accessible_from_component_pkg(self, model: MelodyModel):
        comp: SystemComponentPkg = model.by_uuid(  # type: ignore[assignment]
            "ecb687c1-c540-4de6-8b1d-024d1ed0178f"
        )
        stm = comp.state_machines.by_uuid(
            "9806df59-397c-4505-918f-3b1288638251"
        )

        assert stm.name == "RootStateMachine"

    def test_stm_has_regions(self, model: MelodyModel):
        entity = model.oa.all_entities.by_name("Functional Human Being")
        state_machine = entity.state_machines[0]

        assert hasattr(state_machine, "regions")
        assert len(state_machine.regions) == 1

    def test_stm_region(self, model: MelodyModel):
        entity = model.oa.all_entities.by_name("Functional Human Being")
        region = entity.state_machines[0].regions[0]

        assert len(region.states) == 6
        assert len(region.modes) == 0
        assert len(region.transitions) == 14

    def test_stm_state_mode_regions_well_defined(self, model: MelodyModel):
        mode = (
            model.oa.all_entities.by_name("Environment")
            .entities.by_name("Weather")
            .state_machines[0]
            .regions[0]
            .modes.by_name("Day")
        )

        assert hasattr(mode, "regions")
        assert len(mode.regions) == 1
        assert len(mode.regions[0].modes) > 0

    def test_stm_transition_attributes_well_defined(self, model: MelodyModel):
        transition = (
            model.oa.all_entities.by_name("Functional Human Being")
            .state_machines[0]
            .regions[0]
            .transitions.by_uuid("a78cf778-0476-4e08-a3a3-c115dca55dd1")
        )

        assert hasattr(transition, "source")
        assert transition.source is not None
        assert transition.source.name == "Cooking"

        assert hasattr(transition, "destination")
        assert transition.destination is not None
        assert transition.destination.name == "Eating"

        assert hasattr(transition, "guard")
        assert transition.guard is not None
        assert transition.guard.specification["LinkedText"] == "Food is cooked"

        assert hasattr(transition, "triggers")
        assert transition.triggers is not None
        assert len(transition.triggers) == 1

    def test_stm_transition_multiple_guards(self, model: MelodyModel):
        transition: StateTransition = model.by_uuid("6781fb18-6dd1-4b01-95f7-2f896316e46c")  # type: ignore[assignment]

        assert transition.guard is not None
        assert (
            transition.guard.specification["LinkedText"]
            == "Actor feels hungry"
        )
        assert transition.guard.specification["Python"] == "self.hunger >= 0.8"

    def test_stm_region_has_access_to_diagrams(self, model: MelodyModel):
        default_region: Region = model.by_uuid(  # type: ignore[assignment]
            "eeeb98a7-6063-4115-8b4b-40a51cc0df49"
        )
        state: State = default_region.states.by_uuid(  # type: ignore[assignment]
            "0c7b7899-49a7-4e41-ab11-eb7d9c2becf6"
        )
        sleep_region = state.regions[0]

        assert default_region.diagrams
        assert (
            default_region.diagrams[0].name
            == "[MSM] States of Functional Human Being"
        )

        assert sleep_region.diagrams
        assert sleep_region.diagrams[0].name == "[MSM] Keep the sleep schedule"


class TestClasses:
    def test_classes_have_access_to_stm(self, model: MelodyModel):
        elm: Class = model.by_uuid("959b5222-7717-4ee9-bd3a-f8a209899464")  # type: ignore[assignment]

        assert elm.xtype.endswith("Class")
        assert hasattr(elm, "state_machines")
        assert len(elm.state_machines) == 1

    @pytest.mark.parametrize(
        "uuid,super_uuid",
        [
            pytest.param(
                "0fef2887-04ce-4406-b1a1-a1b35e1ce0f3",
                "8164ae8b-36d5-4502-a184-5ec064db4ec3",
                id="Same Layer",
            ),
            pytest.param(
                "959b5222-7717-4ee9-bd3a-f8a209899464",
                "bbc296e1-ed4c-40cf-b37d-c8eb8613228a",
                id="Cross Layer",
            ),
        ],
    )
    def test_classes_inheritance(
        self, model: MelodyModel, uuid: str, super_uuid: str
    ):
        elm: Class = model.by_uuid(uuid)  # type: ignore[assignment]
        super_class = model.by_uuid(super_uuid)

        assert elm.xtype.endswith("Class")
        assert hasattr(elm, "inheritance")
        assert elm.inheritance.super == super_class


def test_exchange_items_on_logical_function_exchanges(
    model: MelodyModel,
):
    exchange = model.la.all_function_exchanges.by_uuid(
        "cdc69c5e-ddd8-4e59-8b99-f510400650aa"
    )
    exchange_item = exchange.exchange_items.by_name("ExchangeItem 3")

    assert exchange_item.type == "SHARED_DATA"
    assert exchange in exchange_item.exchanges


def test_exchange_items_on_logical_actor_exchanges(
    model: MelodyModel,
):
    aex = model.la.actor_exchanges.by_uuid(
        "9cbdd233-aff5-47dd-9bef-9be1277c77c3"
    )
    cex_item = aex.exchange_items.by_name("ExchangeItem 2")

    assert "FLOW" == cex_item.type
    assert aex in cex_item.exchanges


def test_exchange_items_on_logical_component_exchanges(
    model: MelodyModel,
):
    cex = model.la.component_exchanges.by_uuid(
        "c31491db-817d-44b3-a27c-67e9cc1e06a2"
    )
    cex_item = cex.exchange_items.by_name("ExchangeItem 1")

    assert "EVENT" == cex_item.type
    assert cex in cex_item.exchanges


@pytest.mark.parametrize(
    ["name", "is_actor", "is_human"],
    [
        ("Prof. S. Snape", True, True),
        ("Whomping Willow", False, True),
        ("Harry J. Potter", True, False),
        ("Hogwarts", False, False),
    ],
)
def test_component_is_human_is_actor(
    name: str, is_actor: bool, is_human: bool, model: MelodyModel
) -> None:
    actor = model.la.all_components.by_name(name)

    assert actor.is_actor == is_actor
    assert actor.is_human == is_human


def test_constraint_links_to_constrained_elements(model: MelodyModel) -> None:
    con = model.by_uuid("039b1462-8dd0-4bfd-a52d-0c6f1484aa6e")
    celt = model.by_uuid("3b83b4ba-671a-4de8-9c07-a5c6b1d3c422")

    assert isinstance(con, capellambse.model.crosslayer.capellacore.Constraint)
    assert len(con.constrained_elements) == 1
    assert con.constrained_elements[0] == celt


def test_constraint_specification_has_linked_object_name_in_body(
    model: MelodyModel,
) -> None:
    con = model.by_uuid("039b1462-8dd0-4bfd-a52d-0c6f1484aa6e")

    assert isinstance(con, capellambse.model.crosslayer.capellacore.Constraint)
    assert (
        con.specification["LinkedText"]
        == '<a href="hlink://dd2d0dab-a35f-4104-91e5-b412f35cba15">Hunted animal</a>'
    )


def test_setting_specification_linked_text_transforms_the_value_to_internal_linkedText(
    model: MelodyModel,
) -> None:
    c1: Constraint = model.by_uuid("039b1462-8dd0-4bfd-a52d-0c6f1484aa6e")  # type: ignore[assignment]
    c2: Constraint = model.by_uuid("0b546f8b-408c-4520-9f6a-f77efe97640b")  # type: ignore[assignment]

    c2.specification["LinkedText"] = c1.specification["LinkedText"]

    assert isinstance(c1, capellambse.model.crosslayer.capellacore.Constraint)
    assert isinstance(c2, capellambse.model.crosslayer.capellacore.Constraint)
    assert (
        next(c1.specification._element.iterchildren("bodies")).text
        == next(c2.specification._element.iterchildren("bodies")).text
    )


def test_constraint_without_specification_raises_AttributeError(
    model: MelodyModel,
) -> None:
    con = model.by_uuid("0336eae7-21f2-4a73-8d71-c7d5ff550229")
    assert isinstance(con, capellambse.model.crosslayer.capellacore.Constraint)

    with pytest.raises(AttributeError, match="^No specification found$"):
        con.specification


@pytest.mark.parametrize(
    "searchkey",
    [Class, "org.polarsys.capella.core.data.information:Class", "Class"],
)
def test_model_search_finds_elements(
    model: capellambse.MelodyModel, searchkey
):
    expected = [
        model.by_uuid("8164ae8b-36d5-4502-a184-5ec064db4ec3"),
        model.by_uuid("0fef2887-04ce-4406-b1a1-a1b35e1ce0f3"),
        model.by_uuid("959b5222-7717-4ee9-bd3a-f8a209899464"),
        model.by_uuid("bbc296e1-ed4c-40cf-b37d-c8eb8613228a"),
    ]

    assert model.search(searchkey) == expected


def test_CommunicationMean(model: capellambse.MelodyModel) -> None:
    comm = model.by_uuid("6638ccd2-61cc-481e-bb23-4c1b147e1dbc")
    env = model.by_uuid("e37510b9-3166-4f80-a919-dfaac9b696c7")
    fhb = model.by_uuid("a8c42033-fdf2-458f-bae9-1cfd1207c49f")
    wood = model.by_uuid("eaf42597-4327-419f-b9f2-d04957f93f47")
    cmd = model.by_uuid("571d093a-a87e-4dfc-9f46-62eb7c374f44")

    assert comm.source == env
    assert comm.target == fhb
    assert wood in comm.allocated_interactions
    assert cmd in comm.allocated_exchange_items


class TestArchitectureLayers:
    @pytest.mark.parametrize(
        "layer,definitions",
        [
            pytest.param(
                "oa",
                [
                    "root_entity",
                    "root_activity",
                    "activity_package",
                    "capability_package",
                    "interface_package",
                    "data_package",
                    "entity_package",
                    "all_activities",
                    "all_processes",
                    "all_capabilities",
                    "all_interfaces",
                    "all_classes",
                    "all_actors",
                    "all_entities",
                    # TODO: actor_exchanges
                    # TODO: component_exchanges
                    "all_activity_exchanges",
                    "all_entity_exchanges",
                ],
                id="OperationalArchitectureLayer",
            ),
            pytest.param(
                "sa",
                [
                    "root_component",
                    "root_function",
                    "function_package",
                    "capability_package",
                    "interface_package",
                    "data_package",
                    "component_package",
                    "mission_package",
                    "all_functions",
                    "all_capabilities",
                    "all_interfaces",
                    "all_classes",
                    "all_actors",
                    "all_components",
                    "all_missions",
                    "actor_exchanges",
                    "component_exchanges",
                    "all_function_exchanges",
                    "all_component_exchanges",
                ],
                id="SystemArchitectureLayer",
            ),
            pytest.param(
                "la",
                [
                    "root_component",
                    "root_function",
                    "function_package",
                    "capability_package",
                    "interface_package",
                    "data_package",
                    "component_package",
                    "all_functions",
                    "all_capabilities",
                    "all_interfaces",
                    "all_classes",
                    "all_actors",
                    "all_components",
                    "actor_exchanges",
                    "component_exchanges",
                    "all_function_exchanges",
                    "all_component_exchanges",
                ],
                id="LogicalArchitectureLayer",
            ),
            pytest.param(
                "pa",
                [
                    "root_component",
                    "root_function",
                    "function_package",
                    # TODO: CapabilityRealizations from la
                    "interface_package",
                    "data_package",
                    "component_package",
                    "all_functions",
                    # TODO: all_capabilities from la
                    "all_interfaces",
                    "all_classes",
                    "all_actors",
                    "all_components",
                    # TODO: actor_exchanges
                    # TODO: component_exchanges
                    "all_physical_exchanges",
                    "all_physical_links",
                ],
                id="PhysicalArchitectureLayer",
            ),
        ],
    )
    def test_ArchitectureLayers_have_root_definitions(
        self,
        model: capellambse.MelodyModel,
        layer: str,
        definitions: t.Sequence[str],
    ) -> None:
        layer = getattr(model, layer)

        for attr in definitions:
            assert hasattr(layer, attr)

        assert hasattr(layer, "diagrams")
