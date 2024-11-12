# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import io
import pathlib
import shutil
import subprocess
import sys
import textwrap

import pytest

import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import decl, helpers
from capellambse.extensions import reqif
from capellambse.filehandler import git

from .conftest import (  # type: ignore[import-untyped]
    INSTALLED_PACKAGE,
    TEST_MODEL,
    TEST_ROOT,
)

DATAPATH = pathlib.Path(__file__).parent / "data" / "decl"
MODELPATH = pathlib.Path(TEST_ROOT / "5_0")

ROOT_COMPONENT = helpers.UUIDString("0d2edb8f-fa34-4e73-89ec-fb9a63001440")
ROOT_FUNCTION = helpers.UUIDString("f28ec0f8-f3b3-43a0-8af7-79f194b29a2d")
TEACH_POTIONS_FUNC = helpers.UUIDString("83ba0220-54f2-48f7-bca1-cd87e39639f2")


class TestDumpLoad:
    @staticmethod
    def test_promises_are_serialized_with_promise_tag() -> None:
        id = "some-future-object"
        data = [{"parent": decl.Promise(id)}]
        expected = f"- parent: !promise {id!r}\n"

        actual = decl.dump(data)

        assert actual == expected

    @staticmethod
    def test_uuid_references_are_serialized_with_uuid_tag() -> None:
        uuid = helpers.UUIDString("00000000-0000-0000-0000-000000000000")
        data = [{"parent": decl.UUIDReference(uuid)}]
        expected = f"- parent: !uuid {uuid!r}\n"

        actual = decl.dump(data)

        assert actual == expected

    @staticmethod
    def test_promise_tags_are_deserialized_as_promise() -> None:
        id = "some-future-object"
        yaml = f"- parent: !promise {id!r}\n"
        expected = [{"parent": decl.Promise(id)}]

        actual = decl.load(io.StringIO(yaml))

        assert actual == expected

    @staticmethod
    def test_uuid_tags_are_deserialized_as_uuidreference() -> None:
        uuid = helpers.UUIDString("00000000-0000-0000-0000-000000000000")
        yaml = f"- parent: !uuid {uuid!r}\n"
        expected = [{"parent": decl.UUIDReference(uuid)}]

        actual = decl.load(io.StringIO(yaml))

        assert actual == expected

    @staticmethod
    def test_loading_with_metadata():
        yml = textwrap.dedent(
            """\
            written_by:
              capellambse_version: 1.0.0
              generator: Example 1.0.0
            model:
              version: "12345678"
              url: https://example.invalid
              entrypoint: path/to/model.aird
            ---
            []
            """
        )
        expected = {
            "written_by": {
                "capellambse_version": "1.0.0",
                "generator": "Example 1.0.0",
            },
            "model": {
                "url": "https://example.invalid",
                "version": "12345678",
                "entrypoint": "path/to/model.aird",
            },
        }

        actual, _ = decl.load_with_metadata(io.StringIO(yml))

        assert actual == expected


class TestApplyExtend:
    @staticmethod
    def test_decl_errors_on_unknown_operations(
        model: m.MelodyModel,
    ) -> None:
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              invalid_operation: {{}}
            """

        with pytest.raises(ValueError, match="invalid_operation"):
            decl.apply(model, io.StringIO(yml))

    @staticmethod
    @pytest.mark.parametrize(
        "parent_str",
        [
            pytest.param(f"!uuid {TEACH_POTIONS_FUNC}", id="!uuid"),
            pytest.param(
                "!find {_type: LogicalFunction, name: teach Potions}",
                id="!find",
            ),
        ],
    )
    def test_decl_finds_parent_to_act_on(
        model: m.MelodyModel, parent_str
    ) -> None:
        parent = model.by_uuid(TEACH_POTIONS_FUNC)
        funcname = "pass the unit test"
        yml = f"""\
            - parent: {parent_str}
              extend:
                functions:
                  - name: {funcname!r}
            """
        expected_len = len(model.search()) + 1
        assert funcname not in parent.functions.by_name

        decl.apply(model, io.StringIO(yml))

        actual_len = len(model.search())
        assert actual_len == expected_len
        assert funcname in parent.functions.by_name

    @staticmethod
    def test_decl_creates_each_object_in_a_list(
        model: m.MelodyModel,
    ) -> None:
        parent_obj = model.by_uuid(ROOT_FUNCTION)
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              extend:
                functions:
                  - name: pass the first test
                  - name: pass the second test
                  - name: pass the third test
            """
        expected_len = len(model.search()) + 3
        for i in ("first", "second", "third"):
            assert f"pass the {i} test" not in parent_obj.functions.by_name

        decl.apply(model, io.StringIO(yml))

        actual_len = len(model.search())
        assert actual_len == expected_len
        for i in ("first", "second", "third"):
            assert f"pass the {i} test" in parent_obj.functions.by_name

    @staticmethod
    def test_decl_creates_nested_complex_objects_where_they_belong(
        model: m.MelodyModel,
    ) -> None:
        root = model.by_uuid(ROOT_FUNCTION)
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              extend:
                functions:
                  - name: pass the unit test
                    functions:
                      - name: run the test function
                      - name: make assertions
            """
        expected_len = len(model.search()) + 3

        decl.apply(model, io.StringIO(yml))

        actual_len = len(model.search())
        assert actual_len == expected_len
        assert "pass the unit test" in root.functions.by_name
        parent = root.functions.by_name("pass the unit test", single=True)
        assert "run the test function" in parent.functions.by_name
        assert "make assertions" in parent.functions.by_name

    @staticmethod
    @pytest.mark.parametrize(
        "type",
        ["AttributeDefinition", "AttributeDefinitionEnumeration"],
    )
    def test_decl_can_disambiguate_creations_with_type_hints(
        model: m.MelodyModel, type: str
    ) -> None:
        module_id = "db47fca9-ddb6-4397-8d4b-e397e53d277e"
        module = model.by_uuid(module_id)
        yml = f"""\
            - parent: !uuid {module_id}
              extend:
                attribute_definitions:
                  - long_name: New attribute
                    _type: {type}
            """
        assert "New attribute" not in module.attribute_definitions.by_long_name

        decl.apply(model, io.StringIO(yml))

        attrdefs = module.attribute_definitions
        assert "New attribute" in attrdefs.by_long_name
        newdef = attrdefs.by_long_name("New attribute", single=True)
        assert newdef.xtype.endswith(f":{type}")

    @staticmethod
    def test_decl_can_create_simple_objects_by_passing_plain_strings(
        model: m.MelodyModel,
    ) -> None:
        attrdef_id = "637caf95-3229-4607-99a0-7d7b990bc97f"
        attrdef = model.by_uuid(attrdef_id)
        yml = f"""\
            - parent: !uuid {attrdef_id}
              extend:
                values:
                  - NewGame++
            """
        assert "NewGame++" not in attrdef.values

        decl.apply(model, io.StringIO(yml))

        assert "NewGame++" in attrdef.values

    @staticmethod
    def test_extend_operations_change_model_objects_in_place(
        model: m.MelodyModel,
    ) -> None:
        root_function = model.by_uuid(ROOT_FUNCTION)
        fnc = model.by_uuid("8833d2dc-b862-4a50-b26c-6f7e0f17faef")
        old_parent = fnc.parent
        assert old_parent != root_function
        assert fnc not in root_function.functions
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              extend:
                functions:
                  - !uuid {fnc.uuid}
            """

        decl.apply(model, io.StringIO(yml))

        assert fnc in root_function.functions
        assert root_function == fnc.parent

    @staticmethod
    def test_extend_operations_with_promises_change_model_objects_in_place(
        model: m.MelodyModel,
    ) -> None:
        root_component = model.by_uuid(ROOT_COMPONENT)
        fnc_name = "The promised one"
        assert fnc_name not in root_component.allocated_functions.by_name
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              extend:
                functions:
                  - name: {fnc_name}
                    promise_id: promised-fnc
            - parent: !uuid {ROOT_COMPONENT}
              extend:
                allocated_functions:
                  - !promise promised-fnc
            """

        decl.apply(model, io.StringIO(yml))

        assert fnc_name in root_component.allocated_functions.by_name

    @staticmethod
    def test_extend_operations_on_faulty_attribute_cause_an_exception(
        model: m.MelodyModel,
    ) -> None:
        non_existing_attr = "Thought up"
        yml = f"""\
            - parent: !uuid {ROOT_COMPONENT}
              extend:
                {non_existing_attr}:
                  - !uuid {ROOT_FUNCTION}
            """

        with pytest.raises(TypeError, match=non_existing_attr):
            decl.apply(model, io.StringIO(yml))

    @staticmethod
    def test_promises_are_resolved_during_the_second_attempt(
        model: m.MelodyModel,
    ) -> None:
        PHYS_COMPONENT = "b327d900-abd2-4138-a111-9ff0684739d8"
        cmp = model.by_uuid(PHYS_COMPONENT)
        previous_ports = len(cmp.ports)
        yml = f"""\
            - parent: !uuid {PHYS_COMPONENT}
              extend:
                physical_links:
                  - name: My new link
                    exchanges:
                      - !promise my_exchange
            - parent: !uuid {PHYS_COMPONENT}
              extend:
                exchanges:
                  - source: !promise first-port
                    target: !promise second-port
                    promise_id: my_exchange
            - parent: !uuid {PHYS_COMPONENT}
              extend:
                ports:
                  - name: First port
                    promise_id: first-port
                  - name: Second port
                    promise_id: second-port
            """

        decl.apply(model, io.StringIO(yml))

        assert len(cmp.ports) == previous_ports + 2
        ex = cmp.physical_links.by_name("My new link")
        assert len(ex.exchanges) == 1
        assert ex.exchanges[0].source.name == "First port"


class TestApplyPromises:
    @staticmethod
    def test_promises_can_backwards_reference_objects(
        model: m.MelodyModel,
    ) -> None:
        root_func = model.by_uuid(ROOT_FUNCTION)
        root_comp = model.by_uuid(ROOT_COMPONENT)
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              extend:
                functions:
                  - name: pass the unit test
                    promise_id: pass-test
            - parent: !uuid {ROOT_COMPONENT}
              extend:
                allocated_functions:
                  - !promise pass-test
            """
        expected_len = len(root_comp.allocated_functions) + 1

        decl.apply(model, io.StringIO(yml))

        actual_len = len(root_comp.allocated_functions)
        assert actual_len == expected_len
        assert "pass the unit test" in root_func.functions.by_name
        assert "pass the unit test" in root_comp.allocated_functions.by_name

    @staticmethod
    def test_promises_can_forward_reference_objects(
        model: m.MelodyModel,
    ) -> None:
        root_func = model.by_uuid(ROOT_FUNCTION)
        root_comp = model.by_uuid(ROOT_COMPONENT)
        yml = f"""\
            - parent: !uuid {ROOT_COMPONENT}
              extend:
                allocated_functions:
                  - !promise pass-test
            - parent: !uuid {ROOT_FUNCTION}
              extend:
                functions:
                  - name: pass the unit test
                    promise_id: pass-test
            """
        expected_len = len(root_comp.allocated_functions) + 1

        decl.apply(model, io.StringIO(yml))

        actual_len = len(root_comp.allocated_functions)
        assert actual_len == expected_len
        assert "pass the unit test" in root_func.functions.by_name
        assert "pass the unit test" in root_comp.allocated_functions.by_name

    @staticmethod
    @pytest.mark.parametrize(
        "order",
        [
            pytest.param((0, 1), id="backward"),
            pytest.param((1, 0), id="forward"),
        ],
    )
    def test_promises_on_simple_attributes_can_reference_objects(
        model: m.MelodyModel, order
    ) -> None:
        root_func = model.by_uuid(ROOT_FUNCTION)
        snippets = (
            f"""
            - parent: !uuid {ROOT_FUNCTION}
              extend:
                inputs:
                  - name: My input
                    promise_id: inport
                outputs:
                  - name: My output
                    promise_id: outport
            """,
            f"""
            - parent: !uuid {ROOT_FUNCTION}
              extend:
                exchanges:
                  - name: Test exchange
                    source: !promise outport
                    target: !promise inport
            """,
        )
        yml = snippets[order[0]] + snippets[order[1]]

        decl.apply(model, io.StringIO(yml))

        assert "Test exchange" in root_func.exchanges.by_name
        exc = root_func.exchanges.by_name("Test exchange")
        assert exc.source == root_func.outputs.by_name("My output")
        assert exc.target == root_func.inputs.by_name("My input")

    @staticmethod
    def test_reused_promise_ids_cause_an_exception(
        model: m.MelodyModel,
    ) -> None:
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              extend:
                functions:
                  - name: pass the first unit test
                    promise_id: colliding-promise-id
                  - name: pass the second unit test
                    promise_id: colliding-promise-id
            """

        with pytest.raises(ValueError, match=r"\bcolliding-promise-id\b"):
            decl.apply(model, io.StringIO(yml))

    @staticmethod
    def test_unfulfilled_promises_raise_an_exception(
        model: m.MelodyModel,
    ) -> None:
        yml = f"""\
            - parent: !uuid {ROOT_COMPONENT}
              extend:
                allocated_functions:
                  - !promise pass-test
            """

        with pytest.raises(decl.UnfulfilledPromisesError, match="^pass-test$"):
            decl.apply(model, io.StringIO(yml))

    @staticmethod
    def test_promises_are_resolved_for_parent_objects(
        model: m.MelodyModel,
    ) -> None:
        yml = f"""\
            - parent: !promise pass-test
              set:
                name: pass the unit test
            - parent: !uuid {ROOT_FUNCTION}
              extend:
                functions:
                  - promise_id: pass-test
            - parent: !promise pass-test
              set:
                description: Makes sure that the test passes.
            """

        resolved = decl.apply(model, io.StringIO(yml))

        assert decl.Promise("pass-test") in resolved
        func = resolved[decl.Promise("pass-test")]
        assert isinstance(func, mm.la.LogicalFunction)
        assert func.name == "pass the unit test"
        assert func.description == "Makes sure that the test passes."


class TestApplyModify:
    @staticmethod
    def test_modify_operations_change_model_objects_in_place(
        model: m.MelodyModel,
    ) -> None:
        newname = "Coffee machine"
        root_component = model.by_uuid(ROOT_COMPONENT)
        assert root_component.name != newname
        yml = f"""\
            - parent: !uuid {ROOT_COMPONENT}
              set:
                name: {newname}
            """

        decl.apply(model, io.StringIO(yml))

        assert root_component.name == newname

    @staticmethod
    def test_modify_can_set_attributes_to_promises(
        model: m.MelodyModel,
    ) -> None:
        root_component = model.by_uuid(ROOT_COMPONENT)
        yml = f"""\
            - parent: !uuid {ROOT_COMPONENT}
              set:
                allocated_functions:
                  - !promise make-coffee
            - parent: !uuid {ROOT_FUNCTION}
              extend:
                functions:
                  - name: make coffee
                    promise_id: make-coffee
            """
        assert "make coffee" not in root_component.allocated_functions.by_name

        decl.apply(model, io.StringIO(yml))

        assert "make coffee" in root_component.allocated_functions.by_name

    @staticmethod
    def test_modify_can_set_attributes_to_uuid_references(
        model: m.MelodyModel,
    ) -> None:
        root_component = model.by_uuid(ROOT_COMPONENT)
        root_function = model.by_uuid(ROOT_FUNCTION)
        yml = f"""\
            - parent: !uuid {ROOT_COMPONENT}
              set:
                allocated_functions:
                  - !uuid {ROOT_FUNCTION}
            """
        assert root_function not in root_component.allocated_functions

        decl.apply(model, io.StringIO(yml))

        assert root_function in root_component.allocated_functions

    @staticmethod
    def test_modifying_to_a_list_removes_all_previous_list_members(
        model: m.MelodyModel,
    ) -> None:
        root_function = model.by_uuid(ROOT_FUNCTION)
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              set:
                functions:
                  - name: survive
            """
        assert len(root_function.functions) > 0

        decl.apply(model, io.StringIO(yml))

        assert len(root_function.functions) == 1
        assert root_function.functions[0].name == "survive"


class TestApplyDelete:
    @staticmethod
    def test_delete_operations_remove_child_objects_from_the_model(
        model: m.MelodyModel,
    ) -> None:
        root_function = model.by_uuid(ROOT_FUNCTION)
        assert len(root_function.functions) > 0
        subfunc: str = root_function.functions[0].uuid
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              delete:
                functions:
                  - !uuid {subfunc}
            """
        assert subfunc in root_function.functions.by_uuid
        expected_len = len(root_function.functions) - 1

        decl.apply(model, io.StringIO(yml))

        assert len(root_function.functions) == expected_len
        assert subfunc not in root_function.functions.by_uuid
        with pytest.raises(KeyError, match=subfunc):
            model.by_uuid(subfunc)

    @staticmethod
    def test_delete_operations_delete_attributes_if_no_list_of_uuids_was_given(
        model: m.MelodyModel,
    ) -> None:
        root_function = model.by_uuid(ROOT_FUNCTION)
        assert len(root_function.functions) > 0
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              delete:
                functions:
            """

        decl.apply(model, io.StringIO(yml))

        assert len(root_function.functions) == 0


class TestApplySync:
    @staticmethod
    def test_sync_operation_without_find_key_raises_an_error(
        model: m.MelodyModel,
    ) -> None:
        yml = f"""\
        - parent: !uuid {ROOT_FUNCTION}
          sync:
            functions:
              - set:
                  name: "The new name"
        """
        with pytest.raises(ValueError, match="find"):
            decl.apply(model, io.StringIO(yml))

    @staticmethod
    def test_sync_operation_finds_and_modifies_existing_objects_in_the_list(
        model: m.MelodyModel,
    ) -> None:
        root_function = model.by_uuid(ROOT_FUNCTION)
        new_description = "This is a function."
        assert root_function.functions[0].description != new_description
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              sync:
                functions:
                  - find:
                      name: {root_function.functions[0].name}
                    set:
                      description: {new_description!r}
            """

        decl.apply(model, io.StringIO(yml))

        assert root_function.functions[0].description == new_description

    @staticmethod
    def test_sync_operation_honors_type_hints(
        model: m.MelodyModel,
    ) -> None:
        yml = """\
            - parent: !uuid 3c2d312c-37c9-41b5-8c32-67578fa52dc3
              sync:
                attributes:
                  - find:
                      _type: StringValueAttribute
                    promise_id: obj
            """

        promises = decl.apply(model, io.StringIO(yml))

        assert decl.Promise("obj") in promises
        obj = promises[decl.Promise("obj")]
        assert isinstance(obj, reqif.StringValueAttribute)
        assert obj.uuid == "ee8a69ef-61b9-4db9-9a0f-628e5d4704e1"

    @staticmethod
    def test_sync_set_overwrites_iterables(
        model: m.MelodyModel,
    ) -> None:
        root_function = model.by_uuid(ROOT_FUNCTION)
        subfunc = root_function.functions[0]
        old_port = subfunc.inputs.create(name="Water port")
        new_port_name = "Power port"
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              sync:
                functions:
                  - find:
                      name: {root_function.functions[0].name}
                    set:
                      inputs:
                        - name: {new_port_name}
            """

        decl.apply(model, io.StringIO(yml))

        assert new_port_name in subfunc.inputs.by_name
        assert old_port not in subfunc.inputs

    @staticmethod
    def test_sync_extend_does_not_overwrite_iterables(
        model: m.MelodyModel,
    ) -> None:
        root_function = model.by_uuid(ROOT_FUNCTION)
        subfunc = root_function.functions[0]
        old_port = subfunc.inputs.create(name="Water port")
        new_port_name = "Power port"
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              sync:
                functions:
                  - find:
                      name: {subfunc.name}
                    extend:
                      inputs:
                        - name: {new_port_name}
            """

        decl.apply(model, io.StringIO(yml))

        assert new_port_name in subfunc.inputs.by_name
        assert old_port in subfunc.inputs

    @staticmethod
    def test_sync_operation_recursive(model: m.MelodyModel) -> None:
        root_package = model.la.data_package
        package_name = "The new package"
        subpackage_name = "The new subpackage"
        assert package_name not in root_package.packages.by_name
        yml = f"""\
            - parent: !uuid {root_package.uuid}
              sync:
                packages:
                  - find:
                      name: "{package_name}"
                    sync:
                      packages:
                        - find:
                            name: {subpackage_name}

            """

        decl.apply(model, io.StringIO(yml))
        assert package_name in root_package.packages.by_name
        package = root_package.packages.by_name(package_name)
        assert subpackage_name in package.packages.by_name

    @staticmethod
    def test_sync_operation_no_duplicates(
        model: m.MelodyModel,
    ) -> None:
        root_package = model.la.data_package
        class_name = "The new class"
        property_name = "The new property"
        assert class_name not in root_package.classes.by_name
        yml = f"""\
            - parent: !uuid {root_package.uuid}
              sync:
                classes:
                  - find:
                      name: "{class_name}"
                    sync:
                      properties:
                        - find:
                            name: "{property_name}"
                          set:
                            kind: COMPOSITION
                            max_card: !new_object
                              _type: LiteralNumericValue
                              value: '1'
                            min_card: !new_object
                              _type: LiteralNumericValue
                              value: '1'
                            type: !promise 'datatype.string'
                datatypes:
                  - find:
                      name: "String"
                      _type: StringType
                    promise_id: datatype.string
            """

        decl.apply(model, io.StringIO(yml))
        actual_class = root_package.classes.by_name(class_name)

        assert len(actual_class.properties) == 1

    @staticmethod
    def test_sync_operation_creates_a_new_object_if_it_didnt_find_a_match(
        model: m.MelodyModel,
    ) -> None:
        root_function = model.by_uuid(ROOT_FUNCTION)
        new_name = "The new function"
        new_description = "This is a new function."
        assert new_name not in root_function.functions.by_name
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              sync:
                functions:
                  - find:
                      name: {new_name}
                    set:
                      description: {new_description!r}
            """

        decl.apply(model, io.StringIO(yml))

        assert new_name in root_function.functions.by_name
        func = root_function.functions.by_name(new_name, single=True)
        assert func.description == new_description

    @staticmethod
    def test_sync_operation_resolves_promises_with_newly_created_objects(
        model: m.MelodyModel,
    ) -> None:
        newname = "The new function"
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              sync:
                functions:
                  - find:
                      name: {newname}
                    promise_id: my_function
            """

        resolved = decl.apply(model, io.StringIO(yml))

        assert resolved
        assert decl.Promise("my_function") in resolved
        new_func = resolved[decl.Promise("my_function")]
        assert isinstance(new_func, mm.la.LogicalFunction)
        assert new_func.name == newname

    @staticmethod
    def test_sync_operation_resolves_promises_with_existing_objects(
        model: m.MelodyModel,
    ) -> None:
        root_function = model.by_uuid(ROOT_FUNCTION)
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              sync:
                functions:
                  - find:
                      name: {root_function.functions[0].name}
                    promise_id: my_function
            """

        resolved = decl.apply(model, io.StringIO(yml))

        assert resolved == {
            decl.Promise("my_function"): root_function.functions[0]
        }

    @staticmethod
    def test_sync_operation_can_resolve_multiple_promises_with_one_object(
        model: m.MelodyModel,
    ) -> None:
        function = model.by_uuid(ROOT_FUNCTION).functions[0]
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              sync:
                functions:
                  - find:
                      name: {function.name}
                    promise_id: promise-1
                  - find:
                      name: {function.name}
                    promise_id: promise-2
            """

        resolved = decl.apply(model, io.StringIO(yml))

        assert resolved == {
            decl.Promise("promise-1"): function,
            decl.Promise("promise-2"): function,
        }


class TestStrictMetadata:
    @staticmethod
    def test_strict_apply_requires_nonempty_metadata(model: m.MelodyModel):
        yml = textwrap.dedent(
            """\
            {}
            ---
            []
            """
        )

        with pytest.raises(ValueError, match="^No metadata found"):
            decl.apply(model, io.StringIO(yml), strict=True)

    @staticmethod
    def test_capellambse_version_outdated(model: m.MelodyModel, monkeypatch):
        modelinfo = m.ModelInfo(
            url="git+https://decl-yaml.invalid/ignored-anyway.git",
            title="Testmodel",
            entrypoint=pathlib.PurePosixPath("testmodel.aird"),
            resources={
                "\x00": git.GitHandlerInfo(
                    url="git+https://decl-yaml.invalid/testmodel.git",
                    branch="master",
                    revision="Baseline-1.0",
                    rev_hash="0000000000000000000000000000000000000000",
                )
            },
            capella_version="5.0.0",
            viewpoints={"org.polarsys.capella.core.viewpoint": "5.0.0"},
            diagram_cache=None,
        )
        monkeypatch.setattr(m.MelodyModel, "info", modelinfo)

        yml = textwrap.dedent(
            """\
            written_by:
              capellambse: '99999.99.99'
            model:
              url: 'git+https://decl-yaml.invalid/testmodel.git'
              revision: '0000000000000000000000000000000000000000'
              entrypoint: 'testmodel.aird'
            ---
            []
            """
        )

        with pytest.raises(ValueError, match=r"99999\.99\.99"):
            decl.apply(model, io.StringIO(yml), strict=True)

    @staticmethod
    def test_declared_capellambse_version_malformed(
        model: m.MelodyModel, monkeypatch
    ):
        modelinfo = m.ModelInfo(
            url="git+https://decl-yaml.invalid/ignored-anyway.git",
            title="Testmodel",
            entrypoint=pathlib.PurePosixPath("testmodel.aird"),
            resources={
                "\x00": git.GitHandlerInfo(
                    url="git+https://decl-yaml.invalid/testmodel.git",
                    branch="master",
                    revision="Baseline-1.0",
                    rev_hash="0000000000000000000000000000000000000000",
                )
            },
            capella_version="5.0.0",
            viewpoints={"org.polarsys.capella.core.viewpoint": "5.0.0"},
            diagram_cache=None,
        )
        monkeypatch.setattr(m.MelodyModel, "info", modelinfo)

        yml = textwrap.dedent(
            """\
            written_by:
              capellambse: 'this-is-not-a-pep440-version'
            model:
              url: 'git+https://decl-yaml.invalid/testmodel.git'
              revision: '0000000000000000000000000000000000000000'
              entrypoint: 'testmodel.aird'
            ---
            []
            """
        )

        with pytest.raises(ValueError, match="this-is-not-a-pep440-version"):
            decl.apply(model, io.StringIO(yml), strict=True)

    @staticmethod
    def test_url_mismatch(model: m.MelodyModel, monkeypatch):
        modelinfo = m.ModelInfo(
            url="git+https://decl-yaml.invalid/ignored-anyway.git",
            title="Testmodel",
            entrypoint=pathlib.PurePosixPath("testmodel.aird"),
            resources={
                "\x00": git.GitHandlerInfo(
                    url="git+https://decl-yaml.invalid/testmodel.git",
                    branch="master",
                    revision="Baseline-1.0",
                    rev_hash="0000000000000000000000000000000000000000",
                )
            },
            capella_version="5.0.0",
            viewpoints={"org.polarsys.capella.core.viewpoint": "5.0.0"},
            diagram_cache=None,
        )
        monkeypatch.setattr(m.MelodyModel, "info", modelinfo)

        yml = textwrap.dedent(
            """\
            written_by:
              capellambse: '0.0.1'
            model:
              url: 'git+https://decl-yaml.invalid/other.git'
              revision: '0000000000000000000000000000000000000000'
              entrypoint: 'testmodel.aird'
            ---
            []
            """
        )

        with pytest.raises(ValueError, match=r"/other\.git"):
            decl.apply(model, io.StringIO(yml), strict=True)

    @staticmethod
    def test_entrypoint_mismatch(model: m.MelodyModel, monkeypatch):
        modelinfo = m.ModelInfo(
            url="git+https://decl-yaml.invalid/ignored-anyway.git",
            title="Testmodel",
            entrypoint=pathlib.PurePosixPath("testmodel.aird"),
            resources={
                "\x00": git.GitHandlerInfo(
                    url="git+https://decl-yaml.invalid/testmodel.git",
                    branch="master",
                    revision="Baseline-1.0",
                    rev_hash="0000000000000000000000000000000000000000",
                )
            },
            capella_version="5.0.0",
            viewpoints={"org.polarsys.capella.core.viewpoint": "5.0.0"},
            diagram_cache=None,
        )
        monkeypatch.setattr(m.MelodyModel, "info", modelinfo)

        yml = textwrap.dedent(
            """\
            written_by:
              capellambse: '0.0.1'
            model:
              url: git+https://decl-yaml.invalid/testmodel.git
              revision: '0000000000000000000000000000000000000000'
              entrypoint: othermodel.aird
            ---
            []
            """
        )

        with pytest.raises(ValueError, match=r"othermodel\.aird"):
            decl.apply(model, io.StringIO(yml), strict=True)

    @staticmethod
    def test_model_revision_doesnt_match(model: m.MelodyModel, monkeypatch):
        modelinfo = m.ModelInfo(
            url="git+https://decl-yaml.invalid/ignored-anyway.git",
            title="Testmodel",
            entrypoint=pathlib.PurePosixPath("testmodel.aird"),
            resources={
                "\x00": git.GitHandlerInfo(
                    url="git+https://decl-yaml.invalid/testmodel.git",
                    branch="master",
                    revision="Baseline-1.0",
                    rev_hash="0000000000000000000000000000000000000000",
                )
            },
            capella_version="5.0.0",
            viewpoints={"org.polarsys.capella.core.viewpoint": "5.0.0"},
            diagram_cache=None,
        )
        monkeypatch.setattr(m.MelodyModel, "info", modelinfo)

        yml = textwrap.dedent(
            """\
            written_by:
              capellambse: '0.0.1'
            model:
              url: git+https://decl-yaml.invalid/testmodel.git
              revision: 'ffffffffffffffffffffffffffffffffffffffff'
              entrypoint: testmodel.aird
            ---
            []
            """
        )

        with pytest.raises(ValueError, match=40 * "f"):
            decl.apply(model, io.StringIO(yml), strict=True)


@pytest.mark.parametrize("filename", ["coffee-machine.yml"])
def test_full_example(model: m.MelodyModel, filename: str):
    decl.apply(model, DATAPATH / filename)


def test_cli_applies_a_yaml_and_saves_the_model_back(tmp_path: pathlib.Path):
    shutil.copytree(MODELPATH, tmp_path / "model")
    model = tmp_path / "model" / TEST_MODEL
    semmodel = model.with_suffix(".capella")
    oldhash = hashlib.sha256(semmodel.read_bytes()).hexdigest()
    declfile = DATAPATH / "coffee-machine.yml"

    cli = subprocess.run(
        [sys.executable, "-mcapellambse.decl", f"--model={model}", declfile],
        cwd=INSTALLED_PACKAGE.parent,
        check=False,
    )

    assert cli.returncode == 0, "CLI process exited unsuccessfully"
    newhash = hashlib.sha256(semmodel.read_bytes()).hexdigest()
    assert newhash != oldhash, "Files on disk didn't change"
