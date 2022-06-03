# Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

import pathlib
import re

TEST_ROOT = pathlib.Path(__file__).parent / "data" / "melodymodel"
TEST_MODEL = "Melody Model Test.aird"
RE_VALID_IDREF = re.compile(
    r"([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})"
)
