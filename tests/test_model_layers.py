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
import sys
import textwrap

import pytest

import capellambse
from capellambse.model import MelodyModel, modeltypes

from . import TEST_MODEL, TEST_ROOT


@pytest.mark.parametrize(
    "path",
    [
        str(TEST_ROOT / "5_0" / TEST_MODEL),
        str(TEST_ROOT / "5_0" / TEST_MODEL).encode(
            sys.getfilesystemencoding()
        ),
        TEST_ROOT / "5_0" / TEST_MODEL,
    ],
)
def test_model_loading(path):
    capellambse.MelodyModel(path)


def test_model_loading_badpath():
    badpath = TEST_ROOT / "TestFile.airdfragment"
    with pytest.raises(FileNotFoundError):
        capellambse.MelodyModel(badpath)


def test_model_info_contains_capella_version(model):
    assert hasattr(model.info, "capella_version")


def test_model_info_dict_has_capella_version(model):
    model_info = model.info.as_dict()
    assert model_info.get("capella_version") == "5.0.0"


def test_loading_version_5_succeeds():
    capellambse.MelodyModel(TEST_ROOT / "5_0" / "MelodyModelTest.aird")


def test_loading_version_one_succeeds():
    capellambse.MelodyModel(TEST_ROOT / "1_3" / "MelodyModelTest.aird")


def test_ElementList_filter_by_name(model):
    cap = model.oa.all_capabilities.by_name("Eat food")
    assert cap.uuid == "3b83b4ba-671a-4de8-9c07-a5c6b1d3c422"
    assert cap.name == "Eat food"


def test_ElementList_filter_contains(model):
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


def test_ElementList_filter_iter(model):
    caps = model.oa.all_capabilities
    assert sorted(i.name for i in caps) == sorted(caps.by_name)


def test_ElementList_filter_by_type(model):
    diags = model.diagrams.by_type("OCB")
    assert len(diags) == 1
    assert diags[0].type is modeltypes.DiagramType.OCB


def test_MixedElementList_filter_by_type(model):
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
def test_GenericElement_attrs(model, key, value):
    elm = model.oa.all_capabilities.by_name("Eat food")
    assert getattr(elm, key) == value


def test_GenericElement_has_diagrams(model):
    elm = model.oa.all_capabilities.by_name("Eat food")
    assert hasattr(elm, "diagrams")
    assert len(elm.diagrams) == 0


def test_GenericElement_has_pvmt(model):
    elm = model.oa.all_capabilities.by_name("Eat food")
    with pytest.raises(
        AttributeError,
        match="^Cannot access PVMT: extension is not loaded$",
    ):
        elm.pvmt


def test_GenericElement_has_progress_status(model):
    elm = model.oa.all_capabilities[0]
    assert elm.progress_status == "NOT_SET"


def test_Capabilities_have_constraints(model):
    elm = model.oa.all_capabilities.by_name("Eat food")
    assert hasattr(elm, "constraints")
    assert len(elm.constraints) == 3


def test_stm(model):
    entity = model.oa.all_entities.by_name("Functional Human Being")
    state_machine = entity.state_machines[0]
    assert hasattr(state_machine, "regions")
    assert len(state_machine.regions) == 1


def test_stm_region(model):
    entity = model.oa.all_entities.by_name("Functional Human Being")
    region = entity.state_machines[0].regions[0]
    assert len(region.states) == 6
    assert len(region.modes) == 0
    assert len(region.transitions) == 14


def test_stm_state_mode(model):
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


def test_stm_transition(model):
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
    assert transition.guard.specification.text == "Food is cooked"

    assert hasattr(transition, "triggers")
    assert transition.triggers is not None
    assert len(transition.triggers) == 1


def test_stm_transition_multiple_guards(model):
    transition = model.by_uuid("6781fb18-6dd1-4b01-95f7-2f896316e46c")

    assert transition.guard is not None
    assert transition.guard.specification.text == "Actor feels hungry"
    assert transition.guard.specification["Python"] == "self.hunger >= 0.8"


def test_path_nesting(model):
    modules = model.oa.requirement_modules
    assert 1 == len(modules)
    assert 1 == len(modules[0].folders)
    assert 1 == len(modules[0].folders[0].folders)
    assert 1 == len(modules[0].folders[0].folders[0].requirements)


def test_appearances(model):
    module_repr = (
        "<RequirementsModule 'Test Module'"
        " (f8e2195d-b5f5-4452-a12b-79233d943d5e)>"
    )
    folder_repr = (
        "<RequirementsFolder 'Test Module/This is a folder.'"
        " (e16f5cc1-3299-43d0-b1a0-82d31a137111)>"
    )
    subfolder_repr = (
        "<RequirementsFolder 'Test Module/This is a folder./Subfolder'"
        " (e179d6ff-5301-42a6-bf6f-4fec79b18827)>"
    )
    req_repr = (
        "<Requirement 'Test Module/This is a folder./Subfolder/TestReq3'"
        " (79291c33-5147-4543-9398-9077d582576d)>"
    )
    rel_repr = "<RequirementsOutRelation from <Requirement 'Test Module/This is a folder./<p>Test requirement 1 really l o n g text that is&nbsp;way too long to display here as that</p>\\n\\n<p>&lt; &gt; &quot; &#39;</p>\\n\\n<ul>\\n\\t<li>This&nbsp;is a list</li>\\n\\t<li>an unordered one</li>\\n</ul>\\n\\n<ol>\\n\\t<li>Ordered list</li>\\n\\t<li>Ok</li>\\n</ol>\\n' (3c2d312c-37c9-41b5-8c32-67578fa52dc3)> to <LogicalComponent 'Hogwarts' (0d2edb8f-fa34-4e73-89ec-fb9a63001440)> (57033242-3766-4961-8091-ce3d9326ed67)>"

    module = model.by_uuid("f8e2195d-b5f5-4452-a12b-79233d943d5e")
    assert module_repr == repr(module)

    folder = model.by_uuid("e16f5cc1-3299-43d0-b1a0-82d31a137111")
    assert folder_repr == repr(folder)

    subfolder = model.by_uuid("e179d6ff-5301-42a6-bf6f-4fec79b18827")
    assert subfolder_repr == repr(subfolder)

    requirement = model.by_uuid("79291c33-5147-4543-9398-9077d582576d")
    assert req_repr == repr(requirement)

    relation = model.by_uuid("57033242-3766-4961-8091-ce3d9326ed67")
    assert rel_repr == repr(relation)


def test_requirement_attributes(model):
    uuid = "3c2d312c-37c9-41b5-8c32-67578fa52dc3"
    test_req = model.oa.all_requirements.by_uuid(uuid)
    assert test_req.chapter_name == "2"
    assert test_req.description == "This is a test requirement of kind 1."
    assert test_req.foreign_id == 1
    assert test_req.identifier == "REQTYPE-1"
    assert test_req.long_name == "1"
    assert test_req.name == "TestReq1"
    assert test_req.prefix == "3"
    assert test_req.text == textwrap.dedent(
        """\
        <p>Test requirement 1 really l o n g text that is\xa0way too long to display here as that</p>

        <p>&lt; &gt; \" '</p>

        <ul>
        \t<li>This\xa0is a list</li>
        \t<li>an unordered one</li>
        </ul>

        <ol>
        \t<li>Ordered list</li>
        \t<li>Ok</li>
        </ol>
        """
    )
    assert test_req.type == "ReqType"

    assert len(test_req.relations) == 5
    test_rel = test_req.relations.by_xtype(
        "CapellaRequirements:CapellaOutgoingRelation"
    )[0]
    assert test_rel.source.name == "TestReq1"
    assert test_rel.target.name == "Sysexfunc"
    assert test_rel.type == "RelationType"


def test_module_attributes(model):
    test_mod = model.oa.requirement_modules.by_long_name("Module")[0]
    assert test_mod.long_name == "Module"
    assert test_mod.identifier == "1"
    assert test_mod.name == "Test Module"
    assert test_mod.prefix == "T"
    assert test_mod.description == "This is a test requirement module."
    assert test_mod.type == "ModuleType"
    assert len(test_mod.folders) == 1


def test_module_folders_attributes(model):
    test_folder = model.oa.requirement_modules.by_name(
        "Test Module"
    ).folders.by_name("Folder")
    assert test_folder.chapter_name == "C"
    assert test_folder.description == "This is a requirements folder."
    assert test_folder.foreign_id == 11
    assert test_folder.identifier == "1"
    assert test_folder.long_name == "Folder1"
    assert test_folder.name == "Folder"
    assert test_folder.prefix == "F"
    assert test_folder.text == "This is a folder."
    assert test_folder.type == "ReqType"


def test_exchange_items_on_logical_function_exchanges(model):
    exchange = model.la.all_function_exchanges.by_uuid(
        "cdc69c5e-ddd8-4e59-8b99-f510400650aa"
    )
    exchange_item = exchange.exchange_items.by_name("ExchangeItem 3")
    assert exchange_item.type == "SHARED_DATA"
    assert exchange in exchange_item.exchanges


def test_exchange_items_on_logical_actor_exchanges(model):
    aex = model.la.actor_exchanges.by_uuid(
        "9cbdd233-aff5-47dd-9bef-9be1277c77c3"
    )
    cex_item = aex.exchange_items.by_name("ExchangeItem 2")
    assert "FLOW" == cex_item.type
    assert aex in cex_item.exchanges


def test_exchange_items_on_logical_component_exchanges(model):
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
    assert isinstance(con, capellambse.model.crosslayer.capellacore.Constraint)
    celt = model.by_uuid("3b83b4ba-671a-4de8-9c07-a5c6b1d3c422")

    assert len(con.constrained_elements) == 1
    assert con.constrained_elements[0] == celt


def test_constraint_specification_has_linked_object_name_in_body(
    model: MelodyModel,
) -> None:
    con = model.by_uuid("039b1462-8dd0-4bfd-a52d-0c6f1484aa6e")
    assert isinstance(con, capellambse.model.crosslayer.capellacore.Constraint)
    assert (
        con.specification.text
        == '<a href="#dd2d0dab-a35f-4104-91e5-b412f35cba15">Hunted animal</a>'
    )


def test_constraint_without_specification_raises_AttributeError(
    model: MelodyModel,
) -> None:
    con = model.by_uuid("0336eae7-21f2-4a73-8d71-c7d5ff550229")
    assert isinstance(con, capellambse.model.crosslayer.capellacore.Constraint)

    with pytest.raises(AttributeError, match="^No specification found$"):
        con.specification
