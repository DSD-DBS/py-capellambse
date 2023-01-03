#!/usr/bin/env python


# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

import os
import sys

if __name__ == "__main__":
    if "username" in sys.argv[1].lower():
        print(os.environ["GIT_USERNAME"])
    elif "password" in sys.argv[1].lower():
        print(os.environ["GIT_PASSWORD"])
    else:
        raise SystemExit(1)
