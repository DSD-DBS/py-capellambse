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
XT_ABSTRACT_STATE_REAL = (
    "org.polarsys.capella.core.data.capellacommon:AbstractStateRealization"
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

    _xmltag = "ownedStates"

    regions = c.ProxyAccessor(Region, aslist=c.ElementList)

    functions: c.Accessor


@c.xtype_handler(None)
class State(AbstractStateMode):
    """A state."""


@c.xtype_handler(None)
class Mode(AbstractStateMode):
    """A mode."""


@c.xtype_handler(None)
class DeepHistoryPseudoState(AbstractStateMode):
    """A deep history pseudo state."""


@c.xtype_handler(None)
class FinalState(AbstractStateMode):
    """A final state."""


@c.xtype_handler(None)
class ForkPseudoState(AbstractStateMode):
    """A fork pseudo state."""


@c.xtype_handler(None)
class InitialPseudoState(AbstractStateMode):
    """An initial pseudo state."""


@c.xtype_handler(None)
class JoinPseudoState(AbstractStateMode):
    """A join pseudo state."""


@c.xtype_handler(None)
class ShallowHistoryPseudoState(AbstractStateMode):
    """A shallow history pseudo state."""


@c.xtype_handler(None)
class TerminatePseudoState(AbstractStateMode):
    """A terminate pseudo state."""


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


c.set_accessor(
    AbstractStateMode,
    "realized_states",
    c.ProxyAccessor(
        c.GenericElement,
        XT_ABSTRACT_STATE_REAL,
        follow="targetElement",
        aslist=c.ElementList,
    ),
)
for cls in [
    State,
    Mode,
    DeepHistoryPseudoState,
    FinalState,
    ForkPseudoState,
    InitialPseudoState,
    JoinPseudoState,
    ShallowHistoryPseudoState,
    TerminatePseudoState,
]:
    c.set_accessor(
        cls,
        "realizing_states",
        c.ReferenceSearchingAccessor(
            cls, "realized_states", aslist=c.ElementList
        ),
    )

c.set_accessor(
    Region,
    "states",
    c.RoleTagAccessor(AbstractStateMode._xmltag, aslist=c.ElementList),
)
c.set_accessor(Region, "modes", c.ProxyAccessor(Mode, aslist=c.ElementList))
c.set_accessor(
    Region,
    "transitions",
    c.ProxyAccessor(StateTransition, aslist=c.ElementList),
)
