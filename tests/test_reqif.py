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
# pylint: disable=no-self-use
from __future__ import annotations

import datetime
import operator
import textwrap
import typing as t

import pytest

import capellambse
from capellambse.extensions import reqif

from . import RE_VALID_IDREF

long_req_text = textwrap.dedent(
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


def test_extension_was_loaded():
    assert hasattr(capellambse.model.common.GenericElement, "requirements")
    for layer in (
        capellambse.model.layers.oa.OperationalAnalysis,
        capellambse.model.layers.ctx.SystemAnalysis,
        capellambse.model.layers.la.LogicalArchitecture,
        capellambse.model.layers.pa.PhysicalArchitecture,
    ):
        assert hasattr(layer, "requirement_modules")
        assert hasattr(layer, "all_requirements")


def test_path_nesting(model: capellambse.MelodyModel) -> None:
    modules = model.oa.requirement_modules
    assert len(modules) == 2
    assert len(modules[0].folders) == 1
    assert len(modules[0].folders[0].folders) == 1
    assert len(modules[0].folders[0].folders[0].requirements) == 1


@pytest.mark.parametrize(
    "_repr",
    [
        pytest.param(
            "<RequirementsModule 'Test Module' (f8e2195d-b5f5-4452-a12b-79233d943d5e)>",
            id="Module",
        ),
        pytest.param(
            "<RequirementsFolder 'Test Module/This is a folder.' (e16f5cc1-3299-43d0-b1a0-82d31a137111)>",
            id="Folder",
        ),
        pytest.param(
            "<RequirementsFolder 'Test Module/This is a folder./Subfolder' (e179d6ff-5301-42a6-bf6f-4fec79b18827)>",
            id="Sub-Folder",
        ),
        pytest.param(
            "<Requirement 'Test Module/This is a folder./Subfolder/TestReq3' (79291c33-5147-4543-9398-9077d582576d)>",
            id="Requirement",
        ),
        pytest.param(
            "<RequirementsOutRelation from <Requirement 'Test Module/This is a folder./<p>Test requirement 1 really l o n g text that is&nbsp;way too long to display here as that</p>\\n\\n<p>&lt; &gt; &quot; &#39;</p>\\n\\n<ul>\\n\\t<li>This&nbsp;is a list</li>\\n\\t<li>an unordered one</li>\\n</ul>\\n\\n<ol>\\n\\t<li>Ordered list</li>\\n\\t<li>Ok</li>\\n</ol>\\n' (3c2d312c-37c9-41b5-8c32-67578fa52dc3)> to <LogicalComponent 'Hogwarts' (0d2edb8f-fa34-4e73-89ec-fb9a63001440)> (57033242-3766-4961-8091-ce3d9326ed67)>",
            id="Relation",
        ),
        pytest.param(
            "<DateValueAttribute [AttrDef] (7351093e-2c1c-4b1a-bb47-43443f530e8d)>",
            id="Attribute",
        ),
        pytest.param(
            "<EnumerationValueAttribute [MultiEnum] (148bdf2f-6dc2-4a83-833b-596886ce5b07)>",
            id="Enum Attribute",
        ),
        pytest.param(
            "<RequirementsTypesFolder 'Types' (67bba9cf-953c-4f0b-9986-41991c68d241)>",
            id="Type Folder",
        ),
        pytest.param(
            "<DataTypeDefinition 'DataTypeDef' (3b7ec38a-e26a-4c23-9fa3-275af3f629ee)>",
            id="Data Type Definition",
        ),
        pytest.param(
            "<EnumDataTypeDefinition 'EnumDataTypeDef' (637caf95-3229-4607-99a0-7d7b990bc97f)>",
            id="Enum Data Type Definition",
        ),
        pytest.param(
            "<ModuleType 'ModuleType' (a67e7f43-4b49-425c-a6a7-d44e1054a488)>",
            id="Module Type",
        ),
        pytest.param(
            "<RelationType 'RelationType' (f1aceb81-5f70-4469-a127-94830eb9be04)>",
            id="Relation Type",
        ),
        pytest.param(
            "<RequirementType 'ReqType' (db47fca9-ddb6-4397-8d4b-e397e53d277e)>",
            id="Requirement Type",
        ),
        pytest.param(
            "<AttributeDefinition 'AttrDef' (682bd51d-5451-4930-a97e-8bfca6c3a127)>",
            id="Attribute Definition",
        ),
        pytest.param(
            "<AttributeDefinitionEnumeration 'AttrDefEnum' (c316ab07-c5c3-4866-a896-92e34733055c)>",
            id="Enumeration Attribute Definition",
        ),
        pytest.param(
            "<BooleanValueAttribute [] (dcb8614e-2d1c-4cb3-aa0c-667a297e7489)>",
            id="Attribute with Undefined definition",
        ),
    ],
)
def test_appearances(model: capellambse.MelodyModel, _repr: str) -> None:
    uuid = RE_VALID_IDREF.findall(_repr)[-1]
    assert _repr == repr(model.by_uuid(uuid))


class TestRequirementAttributes:
    @pytest.mark.parametrize(
        "attributes",
        [
            pytest.param(
                {
                    "uuid": "e16f5cc1-3299-43d0-b1a0-82d31a137111",
                    "name": "Folder",
                    "long_name": "Folder1",
                    "prefix": "F",
                    "chapter_name": "C",
                    "description": "This is a requirements folder.",
                    "foreign_id": 11,
                    "identifier": "1",
                    "type": reqif.RequirementType,
                    "type.long_name": "ReqType",
                },
                id="Folder",
            ),
            pytest.param(
                {
                    "uuid": "f8e2195d-b5f5-4452-a12b-79233d943d5e",
                    "long_name": "Module",
                    "identifier": "1",
                    "name": "Test Module",
                    "prefix": "T",
                    "description": "This is a test requirement module.",
                    "type": reqif.ModuleType,
                    "type.long_name": "ModuleType",
                },
                id="Module",
            ),
            pytest.param(
                {
                    "uuid": "3c2d312c-37c9-41b5-8c32-67578fa52dc3",
                    "name": "TestReq1",
                    "long_name": "1",
                    "chapter_name": "2",
                    "prefix": "3",
                    "description": "This is a test requirement of kind 1.",
                    "text": long_req_text,
                    "identifier": "REQTYPE-1",
                    "foreign_id": 1,
                },
                id="Requirement",
            ),
            pytest.param(
                {
                    "uuid": "6af6ff84-8957-481f-8684-2405ffa15804",
                    "long_name": "Test Relation",
                    "xtype": "CapellaRequirements:CapellaOutgoingRelation",
                    "description": "This is a relation.",
                    "identifier": "1",
                    "source": reqif.Requirement,
                    "source.name": "TypedReq1",
                    "target": capellambse.model.layers.ctx.SystemFunction,
                    "target.name": "Sysexfunc",
                    "type": reqif.RelationType,
                    "type.long_name": "RelationType",
                },
                id="Relation",
            ),
        ],
    )
    def test_well_defined_generics(
        self,
        model: capellambse.MelodyModel,
        attributes: dict[str, str | int | type],
    ) -> None:
        obj = model.by_uuid(attributes["uuid"])  # type: ignore[arg-type]
        for attr_name, value in attributes.items():
            if isinstance(value, type):
                assert isinstance(operator.attrgetter(attr_name)(obj), value)
            else:
                assert operator.attrgetter(attr_name)(obj) == value

    def test_well_defined_on_modules(
        self, model: capellambse.MelodyModel
    ) -> None:
        module = model.by_uuid("f8e2195d-b5f5-4452-a12b-79233d943d5e")
        assert isinstance(module, reqif.RequirementsModule)
        attr = module.attributes[0]

        assert len(module.attributes) == 1
        assert isinstance(attr, reqif.EnumerationValueAttribute)
        assert attr.xtype.rsplit(":")[-1] == "EnumerationValueAttribute"
        assert isinstance(
            attr.definition, reqif.AttributeDefinitionEnumeration
        )
        assert attr.definition.long_name == "AttrDefEnum"
        assert attr.values[0].long_name == "enum_val2"

    def test_well_defined_on_requirements(
        self, model: capellambse.MelodyModel
    ) -> None:
        req = model.by_uuid("3c2d312c-37c9-41b5-8c32-67578fa52dc3")
        req2 = model.by_uuid("0a9a68b1-ba9a-4793-b2cf-4448f0b4b8cc")
        assert isinstance(req, reqif.Requirement)
        assert isinstance(req2, reqif.Requirement)

        bool_attr = req.attributes[0]
        undefined_attr = req.attributes[-1]

        assert len(req.attributes) == 6
        assert undefined_attr.value is False
        assert isinstance(bool_attr.value, bool)
        for attr, typ in zip(req.attributes[2:-1], [int, float, str]):
            assert isinstance(attr.value, typ)

        actual_values = [req.long_name for req in req2.attributes[0].values]
        assert actual_values == ["enum_val1", "enum_val2"]


class TestRequirementRelations:
    def test_well_defined_source_target_and_type(
        self, model: capellambse.MelodyModel
    ) -> None:
        rel = model.by_uuid("078b2c69-4352-4cf9-9ea5-6573b75e5eec")
        source = model.by_uuid("3c2d312c-37c9-41b5-8c32-67578fa52dc3")
        target = model.by_uuid("4bf0356c-89dd-45e9-b8a6-e0332c026d33")
        assert isinstance(rel, reqif.AbstractRequirementsRelation)

        assert rel.source == source
        assert rel.target == target
        assert isinstance(rel.type, reqif.RelationType)
        assert rel.type.long_name == "RelationType"

    def test_well_defined_on_requirements(
        self, model: capellambse.MelodyModel
    ) -> None:
        req = model.by_uuid("3c2d312c-37c9-41b5-8c32-67578fa52dc3")
        assert isinstance(req, reqif.Requirement)

        assert len(req.relations) == 4

    def test_well_defined_on_generic_elements(
        self, model: capellambse.MelodyModel
    ) -> None:
        ge = model.by_uuid("00e7b925-cf4c-4cb0-929e-5409a1cd872b")

        assert isinstance(ge.requirements, reqif.RelationsList)  # type: ignore[attr-defined]
        assert len(ge.requirements) == 3  # type: ignore[attr-defined]

    def test_filtering_by_relation_type(self, model: capellambse.MelodyModel):
        ge = model.by_uuid("00e7b925-cf4c-4cb0-929e-5409a1cd872b")
        rel_type = model.by_uuid("f1aceb81-5f70-4469-a127-94830eb9be04")

        assert len(ge.requirements.by_relation_type(rel_type.name)) == 1  # type: ignore[attr-defined]

    @pytest.mark.parametrize(
        ("obj_uuid", "target_uuids"),
        [
            (
                "3c2d312c-37c9-41b5-8c32-67578fa52dc3",
                {
                    "078b2c69-4352-4cf9-9ea5-6573b75e5eec",
                    "24c824ef-b187-4725-a051-a68707e82d70",
                    "57033242-3766-4961-8091-ce3d9326ed67",
                    "7de4c1a5-e106-4171-902a-502b816b60b0",
                },
            ),
            (
                "79291c33-5147-4543-9398-9077d582576d",
                {"41e1b786-a6a1-46cb-9b9c-b302d9278c1c"},
            ),
        ],
    )
    def test_requirement_relations(
        self, model: capellambse.MelodyModel, obj_uuid, target_uuids
    ):
        obj = model.by_uuid(obj_uuid)
        assert isinstance(obj, reqif.Requirement)

        relations = obj.relations

        assert all(
            isinstance(i, reqif.AbstractRequirementsRelation)
            for i in relations
        )
        assert {i.uuid for i in relations} == target_uuids


class TestReqIFAccess:
    def test_module_attributes(self, model: capellambse.MelodyModel):
        mod = model.by_uuid("f8e2195d-b5f5-4452-a12b-79233d943d5e")
        assert isinstance(mod, reqif.RequirementsModule)

        assert len(mod.folders) == 1
        assert len(mod.requirements) == 1
        assert mod.type.long_name == "ModuleType"
        for attr, expected in {
            "identifier": "1",
            "long_name": "Module",
            "name": "Test Module",
            "prefix": "T",
            "description": "This is a test requirement module.",
        }.items():
            assert getattr(mod, attr) == expected

    def test_folder_attributes(self, model: capellambse.MelodyModel):
        folder = model.by_uuid("e16f5cc1-3299-43d0-b1a0-82d31a137111")
        assert isinstance(folder, reqif.RequirementsFolder)

        assert len(folder.folders) == 1
        assert len(folder.requirements) == 2
        assert folder.type.long_name == "ReqType"
        for attr, expected in {
            "identifier": "1",
            "long_name": "Folder1",
            "name": "Folder",
            "prefix": "F",
            "chapter_name": "C",
            "foreign_id": 11,
            "text": "This is a folder.",
            "description": "This is a requirements folder.",
        }.items():
            assert getattr(folder, attr) == expected

    def test_requirement_attributes(self, model: capellambse.MelodyModel):
        req = model.by_uuid("3c2d312c-37c9-41b5-8c32-67578fa52dc3")
        assert isinstance(req, reqif.Requirement)
        assert req.type.long_name == "ReqType"

        for attr, expected in {
            "chapter_name": "2",
            "description": "This is a test requirement of kind 1.",
            "foreign_id": 1,
            "identifier": "REQTYPE-1",
            "long_name": "1",
            "name": "TestReq1",
            "prefix": "3",
            "text": textwrap.dedent(
                """\
                <p>Test requirement 1 really l o n g text that is\xA0way too long to display here as that</p>

                <p>&lt; &gt; " '</p>

                <ul>
                \t<li>This\xA0is a list</li>
                \t<li>an unordered one</li>
                </ul>

                <ol>
                \t<li>Ordered list</li>
                \t<li>Ok</li>
                </ol>
                """
            ),
        }.items():
            assert getattr(req, attr) == expected

    def test_relations(self, model: capellambse.MelodyModel):
        req_with_relations = model.by_uuid(
            "3c2d312c-37c9-41b5-8c32-67578fa52dc3"
        )
        assert isinstance(req_with_relations, reqif.Requirement)

        relations = req_with_relations.relations
        assert len(relations) == 4

    def test_requirement_without_relations(
        self, model: capellambse.MelodyModel
    ):
        req_without_relations = model.by_uuid(
            "0a9a68b1-ba9a-4793-b2cf-4448f0b4b8cc"
        )
        assert isinstance(req_without_relations, reqif.Requirement)
        assert len(req_without_relations.relations) == 0

    def test_outgoing_and_internal_relations(
        self, model: capellambse.MelodyModel
    ):
        req_with_oir = model.by_uuid("85d41db2-9e17-438b-95cf-49342452ddf3")
        assert isinstance(req_with_oir, reqif.Requirement)
        assert len(req_with_oir.relations) == 2

    def test_requirement_types_attribute_definitions(
        self, model: capellambse.MelodyModel
    ):
        reqtype = model.by_uuid("db47fca9-ddb6-4397-8d4b-e397e53d277e")
        attr_def = model.by_uuid("682bd51d-5451-4930-a97e-8bfca6c3a127")
        enum_def = model.by_uuid("c316ab07-c5c3-4866-a896-92e34733055c")

        assert attr_def in reqtype.attribute_definitions
        assert enum_def in reqtype.attribute_definitions


class TestReqIFModification:
    def test_created_requirements_can_be_found_in_the_model(
        self, model: capellambse.MelodyModel
    ):
        mod = model.oa.requirement_modules[0]
        new_req = mod.requirements.create("Requirement")

        assert model.by_uuid(new_req.uuid) == new_req
        assert new_req in mod.requirements

    def test_deleted_requirements_vanish_from_model(
        self, model: capellambse.MelodyModel
    ):
        mod = model.oa.requirement_modules[0]
        old_req = mod.requirements[0]

        del mod.requirements[0]

        assert old_req not in mod.requirements
        with pytest.raises(KeyError):
            model.by_uuid(old_req.uuid)

    @pytest.mark.parametrize(
        "relcls",
        [
            pytest.param("CapellaIncomingRelation", id="IncRelation"),
            pytest.param("CapellaOutgoingRelation", id="OutRelation"),
            pytest.param("InternalRelation", id="IntRelation"),
        ],
    )
    def test_creating_requirements_raises_TypeError(
        self, model: capellambse.MelodyModel, relcls: str
    ):
        req = model.by_uuid("3c2d312c-37c9-41b5-8c32-67578fa52dc3")
        assert isinstance(req, reqif.Requirement)

        with pytest.raises(TypeError):
            req.relations.create(relcls)
        with pytest.raises(TypeError):
            req.relations.create(
                relcls, target="e16f5cc1-3299-43d0-b1a0-82d31a137111"
            )
        with pytest.raises(TypeError):
            req.relations.create(relcls, type="RelationType")
        with pytest.raises(TypeError):
            req.relations.create(relcls, target=req.attributes[0].definition)

    def test_created_requirements_are_found_from_both_sides(
        self, model: capellambse.MelodyModel
    ):
        req = model.by_uuid("3c2d312c-37c9-41b5-8c32-67578fa52dc3")
        target = model.by_uuid("79291c33-5147-4543-9398-9077d582576d")
        assert isinstance(req, reqif.Requirement)
        assert isinstance(target, reqif.Requirement)

        reltype = model.by_uuid("f1aceb81-5f70-4469-a127-94830eb9be04")
        new_rel = req.relations.create(target=target, type=reltype)

        assert new_rel in req.relations
        assert new_rel in target.relations

    @pytest.mark.parametrize(
        "type_hint,def_uuid",
        [
            pytest.param(
                "Int",
                "682bd51d-5451-4930-a97e-8bfca6c3a127",
                id="IntegerAttributeValue",
            ),
            pytest.param(
                "Str",
                "682bd51d-5451-4930-a97e-8bfca6c3a127",
                id="StringAttributeValue",
            ),
            pytest.param(
                "Float",
                "682bd51d-5451-4930-a97e-8bfca6c3a127",
                id="RealAttributeValue",
            ),
            pytest.param(
                "Date",
                "682bd51d-5451-4930-a97e-8bfca6c3a127",
                id="DateValueAttributeValue",
            ),
            pytest.param(
                "Bool",
                "682bd51d-5451-4930-a97e-8bfca6c3a127",
                id="BooleanAttributeValue",
            ),
        ],
    )
    def test_create_requirements_attributes(
        self,
        model: capellambse.MelodyModel,
        type_hint: str,
        def_uuid: str,
    ):
        req = model.by_uuid("79291c33-5147-4543-9398-9077d582576d")
        assert isinstance(req, reqif.Requirement)

        assert not req.attributes
        definition = model.by_uuid(def_uuid)
        attr = req.attributes.create(type_hint, definition=definition)

        assert len(req.attributes) == 1
        assert req.attributes[0] == attr
        assert attr.definition == definition
        assert isinstance(attr, reqif.RequirementsAttribute)

    def test_create_RequirementType_AttributeDefinition_creation(
        self, model: capellambse.MelodyModel
    ):
        reqtype = model.by_uuid("db47fca9-ddb6-4397-8d4b-e397e53d277e")
        definitions = reqtype.attribute_definitions

        attr_def = reqtype.attribute_definitions.create(
            "AttributeDefinition", long_name="First"
        )
        enum_def = reqtype.attribute_definitions.create(
            "AttributeDefinitionEnumeration", long_name="Second"
        )

        assert len(definitions) + 2 == len(reqtype.attribute_definitions)
        assert attr_def in reqtype.attribute_definitions
        assert enum_def in reqtype.attribute_definitions

    def test_create_value_attribute_on_requirements_without_definition(
        self, model: capellambse.MelodyModel
    ):
        req = model.by_uuid("79291c33-5147-4543-9398-9077d582576d")
        assert isinstance(req, reqif.Requirement)

        assert not req.attributes
        attr = req.attributes.create("Int")

        assert len(req.attributes) == 1
        assert req.attributes[0] == attr
        assert attr.definition is None
        assert isinstance(attr, reqif.RequirementsAttribute)

    def test_create_enum_value_attribute_on_requirements(
        self, model: capellambse.MelodyModel
    ):
        req = model.by_uuid("79291c33-5147-4543-9398-9077d582576d")
        definition = model.by_uuid("c316ab07-c5c3-4866-a896-92e34733055c")
        assert isinstance(req, reqif.Requirement)

        assert not req.attributes
        attr = req.attributes.create("Enum", definition=definition)

        assert len(req.attributes) == 1
        assert req.attributes[0] == attr
        assert attr.definition == definition
        assert isinstance(attr, reqif.EnumerationValueAttribute)

    def test_create_requirement_attribute_with_wrong_type_hint_raises_ValueError(
        self, model: capellambse.MelodyModel
    ):
        req = model.by_uuid("79291c33-5147-4543-9398-9077d582576d")
        assert isinstance(req, reqif.Requirement)

        with pytest.raises(ValueError):
            req.attributes.create("Gibberish")

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param(True, id="Boolean Attribute"),
            pytest.param(1, id="Integer Attribute"),
            pytest.param(
                datetime.datetime(
                    2021, 7, 23, 13, 0, 0, tzinfo=datetime.timezone.utc
                ),
                id="DateValue Attribute",
            ),
            pytest.param(1.9, id="Float/Real Attribute"),
            pytest.param("Test1", id="String Attribute"),
        ],
    )
    def test_setting_attribute_values_on_requirement(
        self,
        model: capellambse.MelodyModel,
        value: t.Any,
    ):
        req = model.by_uuid("3c2d312c-37c9-41b5-8c32-67578fa52dc3")
        definition = model.by_uuid("682bd51d-5451-4930-a97e-8bfca6c3a127")
        assert isinstance(req, reqif.Requirement)

        attributes = req.attributes.by_definition(definition)
        attr = next(
            attr for attr in attributes if type(attr.value) is type(value)
        )
        attr.value = value

        assert attr.value == value

    @pytest.mark.parametrize(
        "default_value",
        [
            pytest.param(False, id="Boolean Attribute"),
            pytest.param(0, id="Integer Attribute"),
            pytest.param(None, id="DateValue Attribute"),
            pytest.param(0.0, id="Float/Real Attribute"),
            pytest.param("", id="String Attribute"),
        ],
    )
    def test_setting_default_attribute_values_removes_value_on_xml_element(
        self,
        model: capellambse.MelodyModel,
        default_value: t.Any,
    ):
        """Accessed value is there but on xml element there is no written value."""
        req = model.by_uuid("3c2d312c-37c9-41b5-8c32-67578fa52dc3")
        definition = model.by_uuid("682bd51d-5451-4930-a97e-8bfca6c3a127")
        assert isinstance(req, reqif.Requirement)

        attributes = req.attributes.by_definition(definition)
        try:
            attr = next(
                attr
                for attr in attributes
                if type(attr.value) is type(default_value)
            )
        except StopIteration:
            assert default_value is None
            attr = attributes[1]

        attr.value = default_value

        assert attr.value == default_value
        assert "value" not in attr._element.attrib

    @pytest.mark.parametrize(
        "uuid,value",
        [
            pytest.param(
                "9c692405-b8aa-4caa-b988-51d27db5cd1b", None, id="NoneType"
            ),
            pytest.param("b97c09b5-948a-46e8-a656-69d764ddce7d", 1, id="Int"),
        ],
    )
    def test_setting_attribute_value_with_wrong_value_type_fails_with_TypeError(
        self, model: capellambse.MelodyModel, uuid: str, value: t.Any
    ):
        attr = model.by_uuid(uuid)
        assert isinstance(attr, reqif.RequirementsAttribute)

        with pytest.raises(TypeError):
            attr.value = value  # type: ignore[arg-type]


class TestRequirementsFiltering:
    uuids = frozenset(
        {
            "3c2d312c-37c9-41b5-8c32-67578fa52dc3",
            "0a9a68b1-ba9a-4793-b2cf-4448f0b4b8cc",
            "79291c33-5147-4543-9398-9077d582576d",
            "85d41db2-9e17-438b-95cf-49342452ddf3",
            "1092f69a-5f3a-4fe6-a8fd-b2dffde90650",
            "32d66740-e428-4600-be68-8410d9d568cc",
        }
    )

    def test_filtering_by_type_name(self, model: capellambse.MelodyModel):
        requirements = model.search(reqif.XT_REQUIREMENT)
        rt = model.by_uuid("db47fca9-ddb6-4397-8d4b-e397e53d277e")
        assert isinstance(rt, reqif.RequirementType)

        rtype_reqs = requirements.by_type(rt.long_name)

        uuids = {r.uuid for r in rtype_reqs}
        assert uuids & self.uuids == self.uuids

    def test_filtering_by_type_names(self, model: capellambse.MelodyModel):
        requirements = model.search(reqif.XT_REQUIREMENT)
        rt1 = model.by_uuid("db47fca9-ddb6-4397-8d4b-e397e53d277e")
        rt2 = model.by_uuid("00195554-8fae-4687-86ca-77c93330893d")
        assert isinstance(rt1, reqif.RequirementType)
        assert isinstance(rt2, reqif.RequirementType)

        rtype_reqs = requirements.by_type(rt1.long_name, rt2.long_name)
        expected_uuids = self.uuids | {"db4d4c74-b913-4d9a-8905-7d93d3360560"}

        uuids = {r.uuid for r in rtype_reqs}
        assert uuids & expected_uuids == expected_uuids

    def test_filtering_by_requirement_type(
        self, model: capellambse.MelodyModel
    ):
        requirements = model.search(reqif.XT_REQUIREMENT)
        rt = model.by_uuid("db47fca9-ddb6-4397-8d4b-e397e53d277e")

        uuids = {r.uuid for r in requirements.by_type(rt)}
        assert uuids & self.uuids == self.uuids

    def test_filtering_by_types(self, model: capellambse.MelodyModel):
        requirements = model.search(reqif.XT_REQUIREMENT)
        rt1 = model.by_uuid("db47fca9-ddb6-4397-8d4b-e397e53d277e")
        rt2 = model.by_uuid("00195554-8fae-4687-86ca-77c93330893d")
        expected_uuids = self.uuids | {"db4d4c74-b913-4d9a-8905-7d93d3360560"}

        uuids = {r.uuid for r in requirements.by_type(rt1, rt2)}
        assert uuids & expected_uuids == expected_uuids

    def test_filtering_by_name_and_type(self, model: capellambse.MelodyModel):
        requirements = model.search(reqif.XT_REQUIREMENT)
        rt1 = model.by_uuid("db47fca9-ddb6-4397-8d4b-e397e53d277e")
        rt2 = model.by_uuid("00195554-8fae-4687-86ca-77c93330893d")
        assert isinstance(rt1, reqif.RequirementType)
        assert isinstance(rt2, reqif.RequirementType)

        expected_uuids = self.uuids | {"db4d4c74-b913-4d9a-8905-7d93d3360560"}

        uuids = {r.uuid for r in requirements.by_type(rt1, rt2.long_name)}
        assert uuids & expected_uuids == expected_uuids

    def test_filtering_by_type_None_returns_requirements_with_undefined_type(
        self, model: capellambse.MelodyModel
    ):
        requirements = model.search(reqif.XT_REQUIREMENT)
        undefined_type_reqs = requirements.by_type(None)
        req = undefined_type_reqs[0]

        assert len(undefined_type_reqs) == 1
        assert req.long_name == "Undefined type"
        assert req.uuid == "7e8d0edf-67f0-48c5-82f6-ec9cdb809eee"

    @pytest.mark.parametrize(
        ("obj_uuid", "relation_class", "target_uuids"),
        [
            (
                "00e7b925-cf4c-4cb0-929e-5409a1cd872b",
                "outgoing",
                ["85d41db2-9e17-438b-95cf-49342452ddf3"],
            ),
            (
                "00e7b925-cf4c-4cb0-929e-5409a1cd872b",
                "incoming",
                [
                    "3c2d312c-37c9-41b5-8c32-67578fa52dc3",
                    "79291c33-5147-4543-9398-9077d582576d",
                ],
            ),
            ("00e7b925-cf4c-4cb0-929e-5409a1cd872b", "internal", []),
            (
                "3c2d312c-37c9-41b5-8c32-67578fa52dc3",
                "outgoing",
                ["0d2edb8f-fa34-4e73-89ec-fb9a63001440"],
            ),
            (
                "3c2d312c-37c9-41b5-8c32-67578fa52dc3",
                "incoming",
                [
                    "4bf0356c-89dd-45e9-b8a6-e0332c026d33",
                    "00e7b925-cf4c-4cb0-929e-5409a1cd872b",
                ],
            ),
            (
                "3c2d312c-37c9-41b5-8c32-67578fa52dc3",
                "internal",
                ["85d41db2-9e17-438b-95cf-49342452ddf3"],
            ),
        ],
    )
    def test_filtering_by_relation_class(
        self,
        model: capellambse.MelodyModel,
        obj_uuid: str,
        relation_class: str,
        target_uuids: t.Sequence[str],
    ):
        obj = model.by_uuid(obj_uuid)

        if isinstance(obj, reqif.Requirement):
            related = obj.related
        else:
            related = obj.requirements  # type: ignore[attr-defined]
        filtered_related = related.by_relation_class(relation_class)

        assert [i.uuid for i in filtered_related] == target_uuids

    def test_RelationsLists_slicing(self, model: capellambse.MelodyModel):
        req = model.by_uuid("3c2d312c-37c9-41b5-8c32-67578fa52dc3")
        assert isinstance(req, reqif.Requirement)
        related_objs = req.related

        assert len(related_objs[:]) == 4
        assert related_objs is not related_objs[:]
