# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import functools
import os
import sys

import pytest
from lxml import etree

from capellambse.loader import exs

LF = os.linesep

SERIALIZERS = [
    pytest.param(
        functools.partial(
            exs._native_serialize,
            line_length=sys.maxsize,
            siblings=True,
            file=None,
        ),
        id="native",
        marks=pytest.mark.skipif(
            not exs.HAS_NATIVE, reason="native module not available"
        ),
    ),
    pytest.param(
        functools.partial(
            exs._python_serialize,
            encoding="utf-8",
            errors="strict",
            line_length=sys.maxsize,
            siblings=True,
            file=None,
        ),
        id="python",
    ),
]


@pytest.mark.parametrize("serializer", SERIALIZERS)
@pytest.mark.parametrize(
    "string",
    [
        pytest.param(
            f"""<p title="&#x9;&amp;Hello, &lt;&quot;World&quot;>!"/>{LF}""",
            id="attribute",
        ),
        pytest.param(
            f"""<p>\t&amp;Hello, &lt;&quot;World&quot;>!</p>{LF}""",
            id="text",
        ),
        pytest.param(
            f"""{LF}<!--\t&Hello, <"World"&gt;!-->{LF}<p/>{LF}""",
            id="comment",
        ),
    ],
)
def test_escaping(serializer, string):
    tree = etree.fromstring(string)
    expected = string.encode("utf-8")

    actual = serializer(tree)

    assert actual == expected
