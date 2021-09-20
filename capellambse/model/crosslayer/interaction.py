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
from .. import common as c

XT_CAP2PROC = "org.polarsys.capella.core.data.interaction:FunctionalChainAbstractCapabilityInvolvement"
XT_CAP2ACT = "org.polarsys.capella.core.data.interaction:AbstractFunctionAbstractCapabilityInvolvement"
XT_CAP_GEN = "org.polarsys.capella.core.data.interaction:AbstractCapabilityGeneralization"
XT_SCENARIO = "org.polarsys.capella.core.data.interaction:Scenario"
XT_CAP_REAL = (
    "org.polarsys.capella.core.data.interaction:AbstractCapabilityRealization"
)


@c.xtype_handler(None)
class Scenario(c.GenericElement):
    """A scenario that holds instance roles."""
