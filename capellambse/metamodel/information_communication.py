# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import typing as t

from capellambse import modelv2 as m

from . import behavior, capellacore, information
from . import information_datavalue as dv
from . import modellingcore, modeltypes
from . import namespaces as ns

if t.TYPE_CHECKING:
    from . import capellacommon

NS = ns.INFORMATION_COMMUNICATION


class CommunicationItem(capellacore.Classifier, dv.DataValueContainer):
    visibility = m.EnumPOD("visibility", modeltypes.VisibilityKind)
    state_machines = m.Containment["capellacommon.StateMachine"](
        "ownedStateMachines", (ns.CAPELLACOMMON, "StateMachine")
    )


class Exception(CommunicationItem):
    pass


class Message(CommunicationItem):
    pass


class MessageReference(capellacore.Relationship):
    message = m.Single(
        m.Association["Message"]("message", (NS, "Message")), enforce="min"
    )


class MessageReferencePkg(capellacore.Structure):
    message_references = m.Containment["MessageReference"](
        "ownedMessageReferences", (NS, "MessageReference")
    )


class Signal(CommunicationItem, behavior.AbstractSignal):
    instances = m.Containment["SignalInstance"](
        "signalInstances", (NS, "SignalInstance")
    )


class SignalInstance(information.AbstractInstance):
    pass


class CommunicationLink(capellacore.CapellaElement):
    kind = m.EnumPOD("kind", modeltypes.CommunicationLinkKind)
    protocol = m.EnumPOD("protocol", modeltypes.CommunicationLinkProtocol)
    exchange_item = m.Association["information.ExchangeItem"](
        "exchangeItem", (ns.INFORMATION, "ExchangeItem")
    )


class CommunicationLinkExchanger(modellingcore.ModelElement, abstract=True):
    communication_links = m.Containment["CommunicationLink"](
        "ownedCommunicationLinks", (NS, "CommunicationLink")
    )

    @property
    def produce(self) -> m.ElementList[CommunicationLink]:
        return self.communication_links.by_kind("PRODUCE", single=False)

    @property
    def consume(self) -> m.ElementList[CommunicationLink]:
        return self.communication_links.by_kind("CONSUME", single=False)

    @property
    def send(self) -> m.ElementList[CommunicationLink]:
        return self.communication_links.by_kind("SEND", single=False)

    @property
    def receive(self) -> m.ElementList[CommunicationLink]:
        return self.communication_links.by_kind("RECEIVE", single=False)

    @property
    def call(self) -> m.ElementList[CommunicationLink]:
        return self.communication_links.by_kind("CALL", single=False)

    @property
    def execute(self) -> m.ElementList[CommunicationLink]:
        return self.communication_links.by_kind("EXECUTE", single=False)

    @property
    def write(self) -> m.ElementList[CommunicationLink]:
        return self.communication_links.by_kind("WRITE", single=False)

    @property
    def access(self) -> m.ElementList[CommunicationLink]:
        return self.communication_links.by_kind("ACCESS", single=False)

    @property
    def acquire(self) -> m.ElementList[CommunicationLink]:
        return self.communication_links.by_kind("ACQUIRE", single=False)

    @property
    def transmit(self) -> m.ElementList[CommunicationLink]:
        return self.communication_links.by_kind("TRANSMIT", single=False)
