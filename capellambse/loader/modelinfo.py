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
from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class ModelInfo:
    branch: str | None = None
    title: str | None = None
    url: str | None = None
    revision: str | None = None
    rev_hash: str | None = None
    capella_version: str | None = None

    def __post_init__(self) -> None:
        self.set_project_url()
        self.version_url = self.derive_version_url()

    def derive_version_url(self) -> str | None:
        if self.url and self.rev_hash:
            return "/".join(
                (
                    self.url,
                    "-",
                    "commit",
                    self.rev_hash,
                )
            )
        return None

    def set_project_url(self) -> None:
        """Set self.url to repository URL if the url is an HTTPS URL.
        Otherweise set it to None.
        """
        if self.url:
            if self.url.endswith(".git"):
                self.url = self.url[: -len(".git")]

            if not self.url.startswith("https://"):
                self.url = None

    def as_dict(self) -> dict[str, str | None]:
        return dataclasses.asdict(self)
