# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

import pathlib

import pytest

from capellambse import helpers


def test_paths_relative_to_root_are_not_changed():
    actual = helpers.normalize_pure_path("foo", base="/")
    expected = pathlib.PurePosixPath("foo")
    assert actual == expected


def test_paths_relative_to_a_given_base_are_made_relative_to_root():
    actual = helpers.normalize_pure_path("bar", base="/foo")
    expected = pathlib.PurePosixPath("foo/bar")
    assert actual == expected


def test_absolute_paths_are_made_relative_to_root():
    actual = helpers.normalize_pure_path("/foo/bar")
    expected = pathlib.PurePosixPath("foo/bar")
    assert actual == expected


def test_base_is_ignored_for_absolute_paths():
    actual = helpers.normalize_pure_path("/foo", base="/bar")
    expected = pathlib.PurePosixPath("foo")
    assert actual == expected


def test_doubledot_removes_the_preceding_component():
    actual = helpers.normalize_pure_path("/foo/../bar")
    expected = pathlib.PurePosixPath("bar")
    assert actual == expected


def test_leading_doubledots_are_ignored():
    actual = helpers.normalize_pure_path("/../../../foo")
    expected = pathlib.PurePosixPath("foo")
    assert actual == expected


@pytest.mark.parametrize(
    "input,expected_output",
    [("&gt;", ">"), ("&lt;", "<"), ("&quot;", '"'), ("&apos;", "'")],
)
def test_flatten_html_unescapes_special_char(
    input: str, expected_output: str
) -> None:
    assert helpers.flatten_html_string(input) == expected_output


def test_flatten_html_strips_images() -> None:
    input = """<img src="data:<>">"""
    assert helpers.flatten_html_string(input) == ""


@pytest.mark.parametrize(
    "input,expected",
    [
        ("First<br>Second", "First\nSecond"),
        ("<p>First</p>Second", "First\nSecond"),
        (
            "<p>First<img>Second<br>Third</p>Fourth",
            "FirstSecond\nThird\nFourth",
        ),
    ],
)
def test_flatten_html_blocks_and_hardbreaks_to_newline(
    input: str, expected: str
) -> None:
    assert helpers.flatten_html_string(input) == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        (
            "<ul><li>item 1</li><li>item 2</li></ul>",
            "             • item 1\n             • item 2",
        ),
        (
            "\n<ul>\n\t<li>item 1</li>\n\t<li>item 2</li></ul>",
            "             • item 1\n             • item 2",
        ),
    ],
)
def test_flatten_html_formats_unordered_lists(
    input: str, expected: str
) -> None:
    assert helpers.flatten_html_string(input) == expected
