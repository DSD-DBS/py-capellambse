#!/usr/bin/env -S python -Xdev -Xfrozen_modules=off
# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

import subprocess
import sys
import warnings


def main() -> None:
    name = "repl"
    warnings.warn(
        f"This CLI entry point is deprecated, use 'capellambse {name}' instead",
        FutureWarning,
        stacklevel=2,
    )

    cmd = [
        sys.executable,
        "-Xdev",
        "-Xfrozen_modules=off",
        "-mcapellambse",
        name,
        *sys.argv[1:],
    ]
    raise SystemExit(subprocess.run(cmd, check=False).returncode)


if __name__ == "__main__":
    main()
