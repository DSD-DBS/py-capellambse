# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import io

from capellambse import decl, helpers


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
