# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import enum
import typing as t

import capellambse.model as m

from .. import behavior, capellacore
from .. import namespaces as ns
from . import datavalue

NS = ns.INFORMATION_COMMUNICATION


@m.stringy_enum
@enum.unique
class CommunicationLinkKind(enum.Enum):
    """Enumeration listing the various possibilities of communication links."""

    UNSET = "UNSET"
    """The CommunicationLink protocol is not yet set."""
    PRODUCE = "PRODUCE"
    """The CommunicationLink describes a production of ExchangeItem."""
    CONSUME = "CONSUME"
    """The CommunicationLink describes a comsumption of ExchangeItem."""
    SEND = "SEND"
    """The CommunicationLink describes a sending of ExchangeItem."""
    RECEIVE = "RECEIVE"
    """The CommunicationLink describes a reception of ExchangeItem."""
    CALL = "CALL"
    """The CommunicationLink describes a call of ExchangeItem."""
    EXECUTE = "EXECUTE"
    """The CommunicationLink describes an execution of ExchangeItem."""
    WRITE = "WRITE"
    """The CommunicationLink describes a writing of ExchangeItem."""
    ACCESS = "ACCESS"
    """The CommunicationLink describes an access to the ExchangeItem."""
    ACQUIRE = "ACQUIRE"
    """The CommunicationLink describes an acquisition of ExchangeItem."""
    TRANSMIT = "TRANSMIT"
    """The CommunicationLink describes a transmission of ExchangeItem."""


@m.stringy_enum
@enum.unique
class CommunicationLinkProtocol(enum.Enum):
    """The various possibilities for the protocol of the communication link."""

    UNSET = "UNSET"
    """The CommunicationLink protocol is not yet set."""
    UNICAST = "UNICAST"
    """Describes sending an ExchangeItem using the unicast protocol."""
    MULTICAST = "MULTICAST"
    """Describes sending an ExchangeItem using the multicast protocol."""
    BROADCAST = "BROADCAST"
    """Describes sending an ExchangeItem using the broadcast protocol."""
    SYNCHRONOUS = "SYNCHRONOUS"
    """Describes a call of the ExchangeItem using the synchronous protocol."""
    ASYNCHRONOUS = "ASYNCHRONOUS"
    """Describes a call of the ExchangeItem using the asynchronous protocol."""
    READ = "READ"
    """Describes access to the ExchangeItem by reading it."""
    ACCEPT = "ACCEPT"
    """Describes access to the ExchangeItem by accepting it."""


class CommunicationItem(
    capellacore.Classifier, datavalue.DataValueContainer, abstract=True
):
    visibility = m.EnumPOD("visibility", capellacore.VisibilityKind)
    state_machines = m.Containment["capellacommon.StateMachine"](
        "ownedStateMachines", (ns.CAPELLACOMMON, "StateMachine")
    )


class Exception(CommunicationItem):
    pass


class Message(CommunicationItem):
    pass


class MessageReference(capellacore.Relationship):
    message = m.Single["Message"](m.Association((NS, "Message"), "message"))


class MessageReferencePkg(capellacore.Structure, abstract=True):
    message_references = m.Containment["MessageReference"](
        "ownedMessageReferences", (NS, "MessageReference")
    )


class Signal(CommunicationItem, behavior.AbstractSignal):
    instances = m.Containment["SignalInstance"](
        "signalInstances", (NS, "SignalInstance")
    )


from . import AbstractInstance


class SignalInstance(AbstractInstance):
    pass


class CommunicationLink(capellacore.CapellaElement):
    kind = m.EnumPOD("kind", CommunicationLinkKind)
    protocol = m.EnumPOD("protocol", CommunicationLinkProtocol)
    exchange_item = m.Association["ExchangeItem"](
        (NS, "ExchangeItem"), "exchangeItem"
    )


class CommunicationLinkExchanger(m.ModelElement, abstract=True):
    links = m.Containment["CommunicationLink"](
        "ownedCommunicationLinks", (NS, "CommunicationLink")
    )


if t.TYPE_CHECKING:
    from . import ExchangeItem  # noqa: F401
from .. import capellacommon  # noqa: F401
