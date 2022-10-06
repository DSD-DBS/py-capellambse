# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import io

import pytest

import capellambse
from capellambse import decl, helpers

ROOT_COMPONENT = helpers.UUIDString("0d2edb8f-fa34-4e73-89ec-fb9a63001440")
ROOT_FUNCTION = helpers.UUIDString("f28ec0f8-f3b3-43a0-8af7-79f194b29a2d")


class TestDumpLoad:
    @staticmethod
    def test_promises_are_serialized_with_promise_tag():
        id = "some-future-object"
        data = [{"parent": decl.Promise(id)}]
        expected = f"- parent: !promise {id!r}\n"

        actual = decl.dump(data)

        assert actual == expected

    @staticmethod
    def test_uuid_references_are_serialized_with_uuid_tag():
        uuid = helpers.UUIDString("00000000-0000-0000-0000-000000000000")
        data = [{"parent": decl.UUIDReference(uuid)}]
        expected = f"- parent: !uuid {uuid!r}\n"

        actual = decl.dump(data)

        assert actual == expected

    @staticmethod
    def test_promise_tags_are_deserialized_as_promise():
        id = "some-future-object"
        yaml = f"- parent: !promise {id!r}\n"
        expected = [{"parent": decl.Promise(id)}]

        actual = decl.load(io.StringIO(yaml))

        assert actual == expected

    @staticmethod
    def test_uuid_tags_are_deserialized_as_uuidreference():
        uuid = helpers.UUIDString("00000000-0000-0000-0000-000000000000")
        yaml = f"- parent: !uuid {uuid!r}\n"
        expected = [{"parent": decl.UUIDReference(uuid)}]

        actual = decl.load(io.StringIO(yaml))

        assert actual == expected


class TestApplyCreate:
    @staticmethod
    def test_decl_errors_on_unknown_operations(
        model: capellambse.MelodyModel,
    ) -> None:
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              invalid_operation: {{}}
            """

        with pytest.raises(ValueError, match="invalid_operation"):
            decl.apply(model, io.StringIO(yml))

    @staticmethod
    @pytest.mark.parametrize(
        ["parent_str", "parent_getter"],
        [
            pytest.param(
                f"!uuid {ROOT_FUNCTION}",
                lambda m: m.by_uuid(ROOT_FUNCTION),
                id="!uuid",
            ),
        ],
    )
    def test_decl_finds_parent_to_act_on(
        model: capellambse.MelodyModel, parent_str, parent_getter
    ) -> None:
        funcname = "pass the unit test"
        yml = f"""\
            - parent: {parent_str}
              create:
                functions:
                  - name: {funcname!r}
            """
        expected_len = len(model.search()) + 1
        assert funcname not in parent_getter(model).functions.by_name

        decl.apply(model, io.StringIO(yml))

        actual_len = len(model.search())
        assert actual_len == expected_len
        assert funcname in parent_getter(model).functions.by_name

    @staticmethod
    def test_decl_creates_each_object_in_a_list(
        model: capellambse.MelodyModel,
    ) -> None:
        parent_obj = model.by_uuid(ROOT_FUNCTION)
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              create:
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
        model: capellambse.MelodyModel,
    ) -> None:
        root = model.by_uuid(ROOT_FUNCTION)
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              create:
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


class TestApplyPromises:
    @staticmethod
    def test_promises_can_backwards_reference_objects(
        model: capellambse.MelodyModel,
    ) -> None:
        root_func = model.by_uuid(ROOT_FUNCTION)
        root_comp = model.by_uuid(ROOT_COMPONENT)
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              create:
                functions:
                  - name: pass the unit test
                    promise_id: pass-test
            - parent: !uuid {ROOT_COMPONENT}
              create:
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
        model: capellambse.MelodyModel,
    ) -> None:
        root_func = model.by_uuid(ROOT_FUNCTION)
        root_comp = model.by_uuid(ROOT_COMPONENT)
        yml = f"""\
            - parent: !uuid {ROOT_COMPONENT}
              create:
                allocated_functions:
                  - !promise pass-test
            - parent: !uuid {ROOT_FUNCTION}
              create:
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
        model: capellambse.MelodyModel, order
    ) -> None:
        root_func = model.by_uuid(ROOT_FUNCTION)
        snippets = (
            f"""
            - parent: !uuid {ROOT_FUNCTION}
              create:
                inputs:
                  - name: My input
                    promise_id: inport
                outputs:
                  - name: My output
                    promise_id: outport
            """,
            f"""
            - parent: !uuid {ROOT_FUNCTION}
              create:
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
        model: capellambse.MelodyModel,
    ) -> None:
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              create:
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
        model: capellambse.MelodyModel,
    ) -> None:
        yml = f"""\
            - parent: !uuid {ROOT_COMPONENT}
              create:
                allocated_functions:
                  - !promise pass-test
            """

        with pytest.raises(decl.UnfulfilledPromisesError, match="^pass-test$"):
            decl.apply(model, io.StringIO(yml))


class TestApplyModify:
    @staticmethod
    def test_modify_operations_change_model_objects_in_place(
        model: capellambse.MelodyModel,
    ) -> None:
        newname = "Coffee machine"
        root_component = model.by_uuid(ROOT_COMPONENT)
        assert root_component.name != newname
        yml = f"""\
            - parent: !uuid {ROOT_COMPONENT}
              modify:
                name: {newname}
            """

        decl.apply(model, io.StringIO(yml))

        assert root_component.name == newname

    @staticmethod
    def test_modify_can_set_attributes_to_promises(
        model: capellambse.MelodyModel,
    ) -> None:
        root_component = model.by_uuid(ROOT_COMPONENT)
        yml = f"""\
            - parent: !uuid {ROOT_COMPONENT}
              modify:
                allocated_functions:
                  - !promise make-coffee
            - parent: !uuid {ROOT_FUNCTION}
              create:
                functions:
                  - name: make coffee
                    promise_id: make-coffee
            """
        assert "make coffee" not in root_component.allocated_functions.by_name

        decl.apply(model, io.StringIO(yml))

        assert "make coffee" in root_component.allocated_functions.by_name

    @staticmethod
    def test_modify_can_set_attributes_to_uuid_references(
        model: capellambse.MelodyModel,
    ) -> None:
        root_component = model.by_uuid(ROOT_COMPONENT)
        root_function = model.by_uuid(ROOT_FUNCTION)
        yml = f"""\
            - parent: !uuid {ROOT_COMPONENT}
              modify:
                allocated_functions:
                  - !uuid {ROOT_FUNCTION}
            """
        assert root_function not in root_component.allocated_functions

        decl.apply(model, io.StringIO(yml))

        assert root_function in root_component.allocated_functions

    @staticmethod
    def test_modifying_to_a_list_removes_all_previous_list_members(
        model: capellambse.MelodyModel,
    ) -> None:
        root_function = model.by_uuid(ROOT_FUNCTION)
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              modify:
                functions:
                  - name: survive
            """
        assert len(root_function.functions) > 0

        decl.apply(model, io.StringIO(yml))

        assert len(root_function.functions) == 1
        assert root_function.functions[0].name == "survive"
