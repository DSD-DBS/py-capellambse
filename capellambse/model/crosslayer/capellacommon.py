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
"""Classes handling Mode/State-Machines and related content."""
from .. import common as c
from . import capellacore

XT_TRAFO = "org.polarsys.capella.core.data.capellacommon:TransfoLink"
XT_PSEUDOSTATES = frozenset(
    {
        "org.polarsys.capella.core.data.capellacommon:DeepHistoryPseudoState",
        "org.polarsys.capella.core.data.capellacommon:FinalState",
        "org.polarsys.capella.core.data.capellacommon:ForkPseudoState",
        "org.polarsys.capella.core.data.capellacommon:InitialPseudoState",
        "org.polarsys.capella.core.data.capellacommon:JoinPseudoState",
        "org.polarsys.capella.core.data.capellacommon:ShallowHistoryPseudoState",
        "org.polarsys.capella.core.data.capellacommon:TerminatePseudoState",
    }
)


@c.xtype_handler(None)
class Region(c.GenericElement):
    """A region inside a state machine or state/mode."""

    _xmltag = "ownedRegions"

    states: c.Accessor
    modes: c.Accessor
    transitions: c.Accessor


class AbstractStateMode(c.GenericElement):
    """Common code for states and modes."""

    regions = c.ProxyAccessor(Region, aslist=c.ElementList)
    functions: c.Accessor


@c.xtype_handler(None)
class State(AbstractStateMode):
    """A state."""

    _xmltag = "ownedStates"


@c.xtype_handler(None)
class Mode(AbstractStateMode):
    """A mode."""

    _xmltag = "ownedStates"


@c.xtype_handler(None, *XT_PSEUDOSTATES)
class OASTMROther(AbstractStateMode):
    """Placeholder for unhandled states and modes."""


@c.xtype_handler(None)
class StateMachine(c.GenericElement):
    """A state machine."""

    _xmltag = "ownedStateMachines"

    regions = c.ProxyAccessor(Region, aslist=c.ElementList)


@c.xtype_handler(None)
class StateTransition(c.GenericElement):
    r"""A transition between :class:`State`\ s or :class:`Mode`\ s."""

    _xmltag = "ownedTransitions"

    source = c.AttrProxyAccessor(c.GenericElement, "source")
    destination = c.AttrProxyAccessor(c.GenericElement, "target")
    triggers = c.AttrProxyAccessor(
        c.GenericElement, "triggers", aslist=c.MixedElementList
    )
    guard = c.AttrProxyAccessor(capellacore.Constraint, "guard")


c.set_accessor(Region, "states", c.ProxyAccessor(State, aslist=c.ElementList))
c.set_accessor(Region, "modes", c.ProxyAccessor(Mode, aslist=c.ElementList))
c.set_accessor(
    Region,
    "transitions",
    c.ProxyAccessor(StateTransition, aslist=c.ElementList),
)
