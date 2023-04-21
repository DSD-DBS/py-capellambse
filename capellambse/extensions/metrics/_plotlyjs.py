# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

import logging
import pathlib
import shutil
import subprocess

import capellambse

LOGGER = logging.getLogger(__name__)
NODE_HOME = pathlib.Path(
    capellambse.dirs.user_cache_dir, "metrics", "node_modules"
)


class NodeInstallationError(RuntimeError):
    """Installation of the node.js package failed."""


def npm_install_plotly_orca() -> None:
    packages = ["electron@6.1.4", "orca"]
    LOGGER.debug(
        "Installing packages %r into %s", " and ".join(packages), NODE_HOME
    )
    proc = subprocess.run(
        ["npm", "install", "--prefix", str(NODE_HOME.parent), "-g", *packages],
        executable=shutil.which("npm"),
        capture_output=True,
        check=False,
        text=True,
    )
    if proc.returncode:
        LOGGER.getChild("node").error("%s", proc.stderr)
        raise NodeInstallationError(" and ".join(packages))
