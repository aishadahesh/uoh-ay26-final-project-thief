"""Versioned wire contract for reference-compatible peer matches."""

from __future__ import annotations

import hashlib
import json
import secrets
from collections import OrderedDict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

PROTOCOL_NAME = "police-thief-mcp"
PROTOCOL_VERSION = "3.0.0"
WIRE_ROLES = {"cop": "police", "thief": "thief"}
CONTROL_KINDS = frozenset({"enable", "status", "restart", "quit"})
WIRE_PHASES = frozenset(
    {
        "NEGOTIATING_CONFIG",
        "EXCHANGING_STEP0",
        "TURN_COMMIT",
        "TURN_REVEAL",
        "FINAL_AUDIT",
        "REPORTING",
        "CONTROL",
    }
)
REQUIRED_HANDSHAKE_TERMS = frozenset(
    {
        "protocol_name",
        "protocol_version",
        "schema_version",
        "match_id",
        "series_id",
        "game_index",
        "counted",
        "smoke_test",
        "config_sha256",
        "shared_config_schema_version",
        "num_games_declared",
        "previous_counted_games",
        "response_timeout_sec",
        "watchdog_timeout_sec",
        "capabilities",
    }
)
REQUIRED_IDENTITY_FIELDS = frozenset(
    {
        "group_id",
        "group_name",
        "role",
        "software_version",
        "git_commit_hash",
        "protocol",
        "step0_hardware",
    }
)


class NetworkProtocolError(ValueError):
    """Raised when a peer message is malformed, incompatible, or tampered."""


def _canonical(data: Any) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _digest(payload: dict, nonce: str) -> str:
    return hashlib.sha256(f"{_canonical(payload)}|{nonce}".encode()).hexdigest()


def seal_payload(payload: dict) -> dict:
    nonce = secrets.token_hex(32)
    return {"payload": payload, "nonce": nonce, "commit": _digest(payload, nonce)}


def verify_record(record: dict) -> bool:
    try:
        return secrets.compare_digest(
            str(record["commit"]),
            _digest(record["payload"], str(record["nonce"])),
        )
    except (KeyError, TypeError):
        return False


def create_agreement(terms: dict, identity: dict) -> dict:
    nonce = secrets.token_hex(16)
    return {
        "terms": terms,
        "nonce": nonce,
        "signature": _digest(terms, nonce),
        "identity": identity,
    }


def verify_agreement(message: dict, expected_terms: dict) -> dict:
    try:
        terms = message["terms"]
        nonce = str(message["nonce"])
        signature = str(message["signature"])
        identity = dict(message.get("identity", {}))
    except (KeyError, TypeError, ValueError) as exc:
        raise NetworkProtocolError(f"malformed negotiation message: {exc}") from exc
    if terms != expected_terms:
        raise NetworkProtocolError("opponent game terms do not match local signed terms")
    if not secrets.compare_digest(signature, _digest(terms, nonce)):
        raise NetworkProtocolError("opponent negotiation signature is invalid")
    return identity


def validate_handshake_terms(terms: dict) -> None:
    missing = sorted(REQUIRED_HANDSHAKE_TERMS - set(terms))
    if missing:
        raise NetworkProtocolError(f"handshake terms missing mandatory fields: {missing}")
    if terms["protocol_name"] != PROTOCOL_NAME:
        raise NetworkProtocolError("unsupported protocol name")
    if terms["protocol_version"] != PROTOCOL_VERSION:
        raise NetworkProtocolError("unsupported protocol version")
    if not isinstance(terms["capabilities"], list) or not terms["capabilities"]:
        raise NetworkProtocolError("handshake capabilities must be a non-empty list")
    if len(str(terms["config_sha256"])) != 64:
        raise NetworkProtocolError("config_sha256 must be a SHA-256 hex digest")
    if int(terms["game_index"]) < 1:
        raise NetworkProtocolError("game_index must be positive")
    if int(terms["num_games_declared"]) < int(terms["game_index"]):
        raise NetworkProtocolError("num_games_declared cannot be below game_index")


def verify_peer_identity(identity: dict, expected_peer_role: str) -> dict:
    missing = sorted(REQUIRED_IDENTITY_FIELDS - set(identity))
    if missing:
        raise NetworkProtocolError(f"peer identity missing mandatory fields: {missing}")
    role = str(identity["role"])
    if role not in WIRE_ROLES.values():
        raise NetworkProtocolError("peer identity role is not a wire role")
    if role != expected_peer_role:
        raise NetworkProtocolError("peer identity role does not match the expected opponent role")
    protocol = identity.get("protocol")
    if not isinstance(protocol, dict) or protocol.get("version") != PROTOCOL_VERSION:
        raise NetworkProtocolError("peer identity protocol version is unsupported")
    if len(str(identity["git_commit_hash"])) < 7:
        raise NetworkProtocolError("peer identity git commit hash is missing")
    return identity


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


@dataclass(frozen=True)
class TurnMessage:
    step: int
    sender: str
    hint: str
    smell_grid: dict
    commit: str
    timestamp: str
    barrier_placed: list[int] | None = None
    capture_claim: list[int] | None = None
    claim_response: dict | None = None
    win_claim: dict | None = None
    protocol_version: str = PROTOCOL_VERSION
    match_id: str = ""
    series_id: str = ""
    message_id: str = ""
    correlation_id: str = ""
    receiver: str = ""
    phase: str = "TURN_COMMIT"
    message_type: str = "turn"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> TurnMessage:
        try:
            message = cls(**data)
        except (TypeError, ValueError) as exc:
            raise NetworkProtocolError(f"malformed turn message: {exc}") from exc
        if message.sender not in WIRE_ROLES.values() or message.step < 1:
            raise NetworkProtocolError("invalid turn sender or step")
        if message.protocol_version != PROTOCOL_VERSION:
            raise NetworkProtocolError("wrong protocol_version")
        if message.phase != "TURN_COMMIT":
            raise NetworkProtocolError("wrong phase")
        if len(message.commit) != 64:
            raise NetworkProtocolError("turn commitment must be a SHA-256 digest")
        return message


@dataclass(frozen=True)
class AuditPayload:
    sender: str
    records: list[dict]
    result_claim: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> AuditPayload:
        try:
            payload = cls(**data)
        except (TypeError, ValueError) as exc:
            raise NetworkProtocolError(f"malformed audit payload: {exc}") from exc
        if payload.sender not in WIRE_ROLES.values() or not isinstance(payload.records, list):
            raise NetworkProtocolError("invalid audit sender or records")
        return payload


@dataclass(frozen=True)
class ControlMessage:
    kind: str
    sender: str
    sub_game_number: int = 1
    status: str = ""
    step_budget: float = 0.0
    payload: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ControlMessage:
        allowed = set(cls.__dataclass_fields__)
        try:
            message = cls(**{key: value for key, value in data.items() if key in allowed})
        except (TypeError, ValueError) as exc:
            raise NetworkProtocolError(f"malformed control message: {exc}") from exc
        if message.kind not in CONTROL_KINDS or message.sender not in WIRE_ROLES.values():
            raise NetworkProtocolError("invalid control kind or sender")
        return message


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def audit_records(
    records: list[dict],
    expected_commits: dict[int, str],
    *,
    match_id: str | None = None,
) -> tuple[bool, list[int]]:
    failed: list[int] = []
    seen: set[int] = set()
    for record in records:
        try:
            step = int(record["payload"]["step"])
            commit = str(record["commit"])
        except (KeyError, TypeError, ValueError):
            failed.append(-1)
            continue
        seen.add(step)
        record_match_id = record.get("payload", {}).get("match_id")
        if (
            expected_commits.get(step) != commit
            or not verify_record(record)
            or (match_id is not None and record_match_id != match_id)
        ):
            failed.append(step)
    failed.extend(sorted(set(expected_commits) - seen))
    return not failed, failed
