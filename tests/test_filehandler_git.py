# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

import contextlib
import errno
import logging
import subprocess
from unittest import mock

import pytest

import capellambse
from capellambse.filehandler import git


def test_gitfilehandler_can_read_remote_files_no_revision():
    fh = capellambse.get_filehandler(
        "git+https://github.com/dbinfrago/py-capellambse.git"
    )
    assert isinstance(fh, git.GitFileHandler)
    assert fh.revision == "refs/heads/master"


def test_gitfilehandler_can_read_remote_files_with_revision():
    fh = capellambse.get_filehandler(
        "git+https://github.com/dbinfrago/py-capellambse.git",
        revision="gh-pages",
    )

    assert isinstance(fh, git.GitFileHandler)
    assert fh.revision == "refs/heads/gh-pages"


def test_GitFileHandler_locks_repo_during_tasks(monkeypatch, caplog):
    did_ls_files = False

    def mock_run(cmd, *args, encoding="", **kw):
        del args, kw
        nonlocal did_ls_files
        if len(cmd) >= 2 and cmd[1] == "ls-remote":
            assert not did_ls_files
            did_ls_files = True
            data = "0123456789abcdef0123456789abcdef01234567\thello"
            mock_return = mock.Mock()
            mock_return.stdout = data if encoding else data.encode("ascii")
            mock_return.stderr = "" if encoding else b""
            mock_return.returncode = 0
            return mock_return

        assert did_ls_files
        raise FileNotFoundError(errno.ENOENT, "--mocked end of test--")

    did_flock = False

    @contextlib.contextmanager
    def mock_flock(file):
        del file
        nonlocal did_flock
        assert not did_flock
        did_flock = True
        yield

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(capellambse.helpers, "flock", mock_flock)
    caplog.set_level(logging.DEBUG)
    caplog.clear()

    with pytest.raises(FileNotFoundError, match="--mocked end of test--$"):
        capellambse.get_filehandler(
            "git+https://domain.invalid/demo.git", revision="somebranch"
        )

    assert did_ls_files
    assert did_flock
