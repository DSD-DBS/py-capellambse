# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

import errno
import logging
import pathlib
import re
import sys

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


if sys.platform.startswith("win"):
    import msvcrt

    def test_flock_locks_and_unlocks_again(monkeypatch, tmpdir):
        calls = []

        def mock_locking(_1, mode, _2):
            nonlocal calls
            calls.append(mode)

        monkeypatch.setattr(msvcrt, "locking", mock_locking)
        tmpfile = pathlib.Path(tmpdir, "capellambse.lock")

        with helpers.flock(tmpfile):
            pass

        assert calls == [msvcrt.LK_LOCK, msvcrt.LK_UNLCK]

    def test_flock_retries_after_EDEADLOCK(monkeypatch, tmpdir):
        locks = 0

        def mock_locking(_1, mode, _2):
            nonlocal locks
            if mode == msvcrt.LK_LOCK:
                locks += 1
                if locks < 2:
                    raise OSError(errno.EDEADLOCK, "First non-blocking call")

        monkeypatch.setattr(msvcrt, "locking", mock_locking)
        tmpfile = pathlib.Path(tmpdir, "capellambse.lock")

        with helpers.flock(tmpfile):
            pass

        assert locks == 2

else:
    import fcntl

    def test_flock_blocks_indefinitely(monkeypatch, tmpdir, caplog):
        call_order = []

        def mock_flock(_, flags):
            nonlocal call_order
            if flags & fcntl.LOCK_NB == fcntl.LOCK_NB:
                call_order.append("nonblock")
                raise OSError(errno.EAGAIN, "Non-blocking flock mocks failure")
            else:
                call_order.append("blocking")

        caplog.set_level(logging.DEBUG)
        monkeypatch.setattr(fcntl, "flock", mock_flock)
        tmpfile = pathlib.Path(tmpdir, "capellambse.lock")

        with helpers.flock(tmpfile):
            pass

        logs = [
            i.message
            for i in caplog.records
            if i.name == "capellambse.helpers"
        ]
        assert any(
            re.fullmatch(r"Waiting for lock file /.*/capellambse\.lock", i)
            for i in logs
        )
        assert call_order == ["nonblock", "blocking"]
