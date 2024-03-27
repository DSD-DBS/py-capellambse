# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

import capellambse
from capellambse.filehandler import git


def test_gitfilehandler_can_read_remote_files_no_revision():
    fh = capellambse.get_filehandler(
        "git+https://github.com/DSD-DBS/py-capellambse.git"
    )
    assert isinstance(fh, git.GitFileHandler)
    assert fh.revision == "refs/heads/master"


def test_gitfilehandler_can_read_remote_files_with_revision():
    fh = capellambse.get_filehandler(
        "git+https://github.com/DSD-DBS/py-capellambse.git",
        revision="gh-pages",
    )

    assert isinstance(fh, git.GitFileHandler)
    assert fh.revision == "refs/heads/gh-pages"
