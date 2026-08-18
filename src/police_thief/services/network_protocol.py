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
ALLOWED_WIN_CLAIMS = frozenset({"boxed_in", "survival"})
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


def _is_coordinate(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(item, int) and not isinstance(item, bool) for item in value)
    )


def validate_claim_response(
    response: dict | None, expected_claims: list[list[int]] | None = None,
) -> None:
    """Validate structure and, when known, bind a response to our last claim."""
    if response is None:
        return
    if not isinstance(response, dict) or not isinstance(response.get("caught"), bool):
        raise NetworkProtocolError("claim_response must contain a boolean caught value")
    claim = response.get("claim")
    if not _is_coordinate(claim):
        raise NetworkProtocolError("claim_response.claim must be a two-integer coordinate")
    if expected_claims is not None and claim not in expected_claims:
        raise NetworkProtocolError(
            f"claim_response references {claim!r}, expected one of {expected_claims!r}"
        )


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


def create_agreement(
    terms: dict, identity: dict, conformance: dict | None = None,
) -> dict:
    nonce = secrets.token_hex(16)
    agreement = {
        "terms": terms,
        "nonce": nonce,
        "signature": _digest(terms, nonce),
        "identity": identity,
    }
    if conformance is not None:
        agreement["conformance"] = conformance
    return agreement


def verify_agreement(message: dict, expected_terms: dict) -> dict:
    try:
        terms = message["terms"]
        nonce = str(message["nonce"])
        signature = str(message["signature"])
        identity = dict(message.get("identity", {}))
    except (KeyError, TypeError, ValueError) as exc:
        raise NetworkProtocolError(f"malformed negotiation message: {exc}") from exc
    if not isinstance(terms, dict):
        raise NetworkProtocolError(
            f"malformed negotiation message: terms must be an object, got {type(terms).__name__}"
        )
    if terms != expected_terms:
        differing = sorted(
            key
            for key in set(terms) | set(expected_terms)
            if terms.get(key) != expected_terms.get(key)
        )
        details = ", ".join(
            f"{key}: local={expected_terms.get(key)!r}, opponent={terms.get(key)!r}"
            for key in differing
        )
        raise NetworkProtocolError(f"opponent game terms do not match: {details}")
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
        # Lecturer reference v3 accepts this exact public turn shape. Keep
        # local reliability metadata out of the cross-team wire contract.
        return {
            "step": self.step,
            "sender": self.sender,
            "hint": self.hint,
            "smell_grid": self.smell_grid,
            "commit": self.commit,
            "timestamp": self.timestamp,
            "barrier_placed": self.barrier_placed,
            "capture_claim": self.capture_claim,
            "claim_response": self.claim_response,
            "win_claim": self.win_claim,
        }

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
        for field, value in (
            ("barrier_placed", message.barrier_placed),
            ("capture_claim", message.capture_claim),
        ):
            if value is not None and not _is_coordinate(value):
                raise NetworkProtocolError(f"{field} must be a two-integer coordinate")
        validate_claim_response(message.claim_response)
        if (
            message.win_claim is not None
            and (
                not isinstance(message.win_claim, dict)
                or message.win_claim.get("type") not in ALLOWED_WIN_CLAIMS
            )
        ):
            raise NetworkProtocolError(
                "win_claim.type must be either 'boxed_in' or 'survival'"
            )
        return message


@dataclass(frozen=True)
class AuditPayload:
    sender: str
    records: list[dict]
    result_claim: str
    token_usage: dict | None = None
    consensus_sha: str | None = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        if self.consensus_sha is None:
            payload.pop("consensus_sha")
        return payload

    @classmethod
    def from_dict(cls, data: dict) -> AuditPayload:
        allowed = set(cls.__dataclass_fields__)
        try:
            payload = cls(**{key: value for key, value in data.items() if key in allowed})
        except (TypeError, ValueError) as exc:
            raise NetworkProtocolError(f"malformed audit payload: {exc}") from exc
        if payload.sender not in WIRE_ROLES.values() or not isinstance(payload.records, list):
            raise NetworkProtocolError("invalid audit sender or records")
        if payload.consensus_sha is not None and (
            not isinstance(payload.consensus_sha, str)
            or len(payload.consensus_sha) != 64
            or any(char not in "0123456789abcdef" for char in payload.consensus_sha)
        ):
            raise NetworkProtocolError("consensus_sha must be 64 lowercase hexadecimal characters")
        return payload


@dataclass(frozen=True)
class AuditVerification:
    """Detailed audit verdict separating malformed evidence from forgery."""

    verified: bool
    failed_steps: tuple[int, ...]
    cryptographic_failure: bool
    errors: tuple[str, ...]

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
    require_step0: bool = False,
) -> tuple[bool, list[int]]:
    verdict = verify_audit_records(
        records, expected_commits, match_id=match_id, require_step0=require_step0,
    )
    return verdict.verified, list(verdict.failed_steps)


def verify_audit_records(
    records: list[dict],
    expected_commits: dict[int, str],
    *,
    match_id: str | None = None,
    require_step0: bool = False,
) -> AuditVerification:
    """Return an evidence-rich audit verdict for outcome adjudication."""
    failed: list[int] = []
    errors: list[str] = []
    cryptographic_failure = False
    seen: set[int] = set()
    saw_step0 = False
    for index, record in enumerate(records):
        try:
            step = int(record["payload"]["step"])
            commit = str(record["commit"])
        except (KeyError, TypeError, ValueError):
            failed.append(-1)
            errors.append(
                f"records[{index}] must contain payload.step and top-level commit"
            )
            continue
        if step == 0:
            duplicate_step0 = saw_step0
            correct_type = record["payload"].get("type") == "system_spec"
            valid_commit = verify_record(record)
            valid_step0 = not duplicate_step0 and correct_type and valid_commit
            saw_step0 = True
            if not valid_step0:
                failed.append(0)
                if duplicate_step0:
                    errors.append("duplicate Step-0 system_spec record")
                if not correct_type:
                    errors.append("Step 0 must have payload.type='system_spec'")
                if not valid_commit:
                    cryptographic_failure = True
                    errors.append("Step-0 nonce/commit verification failed")
            continue
        if step in seen:
            failed.append(step)
            errors.append(f"duplicate revealed step {step}")
            continue
        seen.add(step)
        record_match_id = record.get("payload", {}).get("match_id")
        expected = expected_commits.get(step)
        if expected is None:
            failed.append(step)
            errors.append(f"unexpected revealed step {step} had no live commitment")
            continue
        if expected != commit:
            failed.append(step)
            cryptographic_failure = True
            errors.append(f"step {step} does not match its live commitment")
            continue
        if not verify_record(record):
            failed.append(step)
            cryptographic_failure = True
            errors.append(f"step {step} nonce/commit verification failed")
            continue
        if match_id is not None and record_match_id != match_id:
            failed.append(step)
            errors.append(f"step {step} belongs to a different match")
    missing = sorted(set(expected_commits) - seen)
    if missing:
        failed.extend(missing)
        cryptographic_failure = True
        errors.extend(f"missing reveal for committed step {step}" for step in missing)
    if require_step0 and not saw_step0:
        failed.append(0)
        errors.append("required Step-0 system_spec record is missing")
    return AuditVerification(
        verified=not failed,
        failed_steps=tuple(failed),
        cryptographic_failure=cryptographic_failure,
        errors=tuple(errors),
    )
