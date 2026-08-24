"""Signed message envelopes and the idempotency guard that makes a repeated
delivery safe."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, dataclass

from police_thief.services.protocol_constants import (
    PROTOCOL_VERSION,
    WIRE_PHASES,
    WIRE_ROLES,
    NetworkProtocolError,
)


@dataclass(frozen=True)
class MessageEnvelope:
    protocol_version: str
    match_id: str
    series_id: str
    message_id: str
    correlation_id: str
    sender_role: str
    receiver_role: str
    turn_number: int
    phase: str
    message_type: str
    payload: dict
    integrity: dict

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> MessageEnvelope:
        try:
            envelope = cls(**data)
        except (TypeError, ValueError) as exc:
            raise NetworkProtocolError(f"malformed message envelope: {exc}") from exc
        envelope.validate()
        return envelope

    def validate(self) -> None:
        if self.protocol_version != PROTOCOL_VERSION:
            raise NetworkProtocolError("wrong protocol_version")
        if not self.match_id or not self.series_id:
            raise NetworkProtocolError("match_id and series_id are mandatory")
        if not self.message_id:
            raise NetworkProtocolError("message_id is mandatory")
        if (
            self.sender_role not in WIRE_ROLES.values()
            or self.receiver_role not in WIRE_ROLES.values()
        ):
            raise NetworkProtocolError("sender_role or receiver_role is invalid")
        if self.sender_role == self.receiver_role:
            raise NetworkProtocolError("sender_role and receiver_role must differ")
        if self.turn_number < 0:
            raise NetworkProtocolError("turn_number cannot be negative")
        if self.phase not in WIRE_PHASES:
            raise NetworkProtocolError("wrong phase")
        if not self.message_type:
            raise NetworkProtocolError("message_type is mandatory")


@dataclass(frozen=True)
class ProtocolDecision:
    status: str
    reason: str = ""
    cached_response: dict | None = None

    @property
    def accepted(self) -> bool:
        return self.status in {"ACCEPTED", "DUPLICATE"}


class MessageIdempotencyGuard:
    """Bounded per-match message guard for ordering and duplicate safety."""

    def __init__(
        self,
        *,
        match_id: str,
        series_id: str,
        expected_sender_role: str,
        expected_receiver_role: str,
        expected_phase: str,
        expected_turn_number: int,
        max_entries: int = 128,
    ) -> None:
        self.match_id = match_id
        self.series_id = series_id
        self.expected_sender_role = expected_sender_role
        self.expected_receiver_role = expected_receiver_role
        self.expected_phase = expected_phase
        self.expected_turn_number = expected_turn_number
        self.max_entries = max_entries
        self._responses: OrderedDict[str, dict] = OrderedDict()

    def accept(self, envelope: MessageEnvelope, response: dict | None = None) -> ProtocolDecision:
        envelope.validate()
        if envelope.message_id in self._responses:
            cached = self._responses[envelope.message_id]
            self._responses.move_to_end(envelope.message_id)
            return ProtocolDecision("DUPLICATE", "duplicate message_id", cached)
        if envelope.match_id != self.match_id:
            return ProtocolDecision("REJECTED", "wrong-match")
        if envelope.series_id != self.series_id:
            return ProtocolDecision("REJECTED", "wrong-series")
        if envelope.sender_role != self.expected_sender_role:
            return ProtocolDecision("REJECTED", "wrong-role")
        if envelope.receiver_role != self.expected_receiver_role:
            return ProtocolDecision("REJECTED", "wrong-receiver")
        if envelope.phase != self.expected_phase:
            return ProtocolDecision("REJECTED", "wrong-phase")
        if envelope.turn_number < self.expected_turn_number:
            return ProtocolDecision("REJECTED", "stale-turn")
        if envelope.turn_number > self.expected_turn_number:
            return ProtocolDecision("REJECTED", "future-turn")

        cached = response or {"status": "accepted", "message_id": envelope.message_id}
        self._responses[envelope.message_id] = cached
        while len(self._responses) > self.max_entries:
            self._responses.popitem(last=False)
        return ProtocolDecision("ACCEPTED", cached_response=cached)
