#!/usr/bin/env python
# Copyright 2021 DB Netz AG
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

if __name__ == "__main__":
    if "username" in sys.argv[1].lower():
        print(os.environ["GIT_USERNAME"])
    elif "password" in sys.argv[1].lower():
        print(os.environ["GIT_PASSWORD"])
    else:
        raise SystemExit(1)
