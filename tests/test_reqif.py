# pylint: disable=no-self-use
import textwrap

import pytest

import capellambse
from capellambse.extensions import reqif


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


class TestReqIFAccess:
    def test_module_attributes(self, model: capellambse.MelodyModel):
        mod = model.by_uuid("f8e2195d-b5f5-4452-a12b-79233d943d5e")
        assert isinstance(mod, reqif.RequirementsModule)

        assert len(mod.folders) == 1
        assert len(mod.requirements) == 1
        for attr, expected in {
            "identifier": "1",
            "long_name": "Module",
            "name": "Test Module",
            "prefix": "T",
            "description": "This is a test requirement module.",
            "type": "ModuleType",
        }.items():
            assert getattr(mod, attr) == expected

    def test_folder_attributes(self, model: capellambse.MelodyModel):
        folder = model.by_uuid("e16f5cc1-3299-43d0-b1a0-82d31a137111")
        assert isinstance(folder, reqif.RequirementsFolder)

        assert len(folder.folders) == 1
        assert len(folder.requirements) == 2
        for attr, expected in {
            "identifier": "1",
            "long_name": "Folder1",
            "name": "Folder",
            "prefix": "F",
            "chapter_name": "C",
            "foreign_id": 11,
            "text": "This is a folder.",
            "description": "This is a requirements folder.",
            "type": "ReqType",
        }.items():
            assert getattr(folder, attr) == expected

    def test_requirement_attributes(self, model: capellambse.MelodyModel):
        req = model.by_uuid("3c2d312c-37c9-41b5-8c32-67578fa52dc3")
        assert isinstance(req, reqif.Requirement)

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
            "type": "ReqType",
        }.items():
            assert getattr(req, attr) == expected

    def test_relations(self, model: capellambse.MelodyModel):
        req_with_relations = model.by_uuid(
            "3c2d312c-37c9-41b5-8c32-67578fa52dc3"
        )
        assert isinstance(req_with_relations, reqif.Requirement)

        relations = req_with_relations.relations
        assert len(relations) == 5

    def test_requirement_without_relations(
        self, model: capellambse.MelodyModel
    ):
        req_without_relations = model.by_uuid(
            "0a9a68b1-ba9a-4793-b2cf-4448f0b4b8cc"
        )
        assert isinstance(req_without_relations, reqif.Requirement)
        assert len(req_without_relations.relations) == 0

    def test_outgoing_internal_relations(self, model: capellambse.MelodyModel):
        req_with_oir = model.by_uuid("85d41db2-9e17-438b-95cf-49342452ddf3")
        assert isinstance(req_with_oir, reqif.Requirement)
        assert len(req_with_oir.relations) == 1


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
            "CapellaIncomingRelation",
            "CapellaOutgoingRelation",
            "InternalRelation",
        ],
    )
    def test_creating_requirements_requires_a_target_and_type(
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

    def test_created_requirements_are_found_from_both_sides(
        self, model: capellambse.MelodyModel
    ):
        req = model.by_uuid("3c2d312c-37c9-41b5-8c32-67578fa52dc3")
        target = model.by_uuid("79291c33-5147-4543-9398-9077d582576d")
        assert isinstance(req, reqif.Requirement)
        assert isinstance(target, reqif.Requirement)

        new_rel = req.relations.create(target=target, type="RelationType")

        assert new_rel in req.relations
        assert new_rel in target.relations
