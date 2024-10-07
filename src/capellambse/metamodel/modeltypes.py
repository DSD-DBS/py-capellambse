# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Enumeration types used by the MelodyModel."""

import warnings

warnings.warn(
    (
        "The 'modeltypes' module is deprecated,"
        " use the enums from their respective source module instead"
    ),
    DeprecationWarning,
    stacklevel=2,
)

from .activity import ObjectNodeKind as ObjectNodeKind
from .activity import ObjectNodeOrderingKind as ObjectNodeOrderingKind
from .capellacommon import ChangeEventKind as ChangeEventKind
from .capellacommon import TimeEventKind as TimeEventKind
from .capellacommon import TransitionKind as TransitionKind
from .capellacore import VisibilityKind as VisibilityKind
from .epbs import ConfigurationItemKind as ConfigurationItemKind
from .fa import ComponentExchangeKind as ComponentExchangeKind
from .fa import ComponentPortKind as ComponentPortKind
from .fa import ControlNodeKind as ControlNodeKind
from .fa import FunctionalChainKind as FunctionalChainKind
from .fa import FunctionKind as FunctionKind
from .fa import OrientationPortKind as OrientationPortKind
from .information import AggregationKind as AggregationKind
from .information import CollectionKind as CollectionKind
from .information import ElementKind as ElementKind
from .information import ExchangeMechanism as ExchangeMechanism
from .information import ParameterDirection as ParameterDirection
from .information import PassingMode as PassingMode
from .information import SynchronismKind as SynchronismKind
from .information import UnionKind as UnionKind
from .information.communication import (
    CommunicationLinkKind as CommunicationLinkKind,
)
from .information.communication import (
    CommunicationLinkProtocol as CommunicationLinkProtocol,
)
from .information.datatype import NumericTypeKind as NumericTypeKind
from .information.datavalue import BinaryOperator as BinaryOperator
from .information.datavalue import UnaryOperator as UnaryOperator
from .interaction import InteractionOperatorKind as InteractionOperatorKind
from .interaction import MessageKind as MessageKind
from .interaction import ScenarioKind as ScenarioKind
from .libraries import AccessPolicy as AccessPolicy
from .modellingcore import ParameterEffectKind as ParameterEffectKind
from .modellingcore import RateKind as RateKind
from .pa import PhysicalComponentKind as PhysicalComponentKind
from .pa import PhysicalComponentNature as PhysicalComponentNature
from .re import CatalogElementKind as CatalogElementKind
