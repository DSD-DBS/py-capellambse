# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""CLI for the diagram cache updating feature."""

from __future__ import annotations

import subprocess
import sys
import warnings

from capellambse._diagram_cache import IndexEntry as IndexEntry


def _main() -> None:
    name = "export-diagrams"
    warnings.warn(
        f"This CLI entry point is deprecated, use 'capellambse {name}' instead",
        FutureWarning,
        stacklevel=2,
    )

    cmd = [sys.executable, "-mcapellambse", name, *sys.argv[1:]]
    raise SystemExit(subprocess.run(cmd, check=False).returncode)


if __name__ == "__main__":
    _main()
