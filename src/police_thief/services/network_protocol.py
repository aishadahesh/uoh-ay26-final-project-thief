"""Versioned wire contract for reference-compatible peer matches."""

from __future__ import annotations

from police_thief.services.protocol_audit import (
    AuditPayload,
    AuditVerification,
    audit_records,
    verify_audit_records,
)
from police_thief.services.protocol_constants import (
    ALLOWED_WIN_CLAIMS,
    CONTROL_KINDS,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    REQUIRED_HANDSHAKE_TERMS,
    REQUIRED_IDENTITY_FIELDS,
    WIRE_PHASES,
    WIRE_ROLES,
    NetworkProtocolError,
)
from police_thief.services.protocol_crypto import (
    create_agreement,
    now_iso,
    seal_payload,
    verify_agreement,
    verify_record,
)
from police_thief.services.protocol_messages import (
    MessageEnvelope,
    MessageIdempotencyGuard,
    ProtocolDecision,
)
from police_thief.services.protocol_turns import (
    ControlMessage,
    TurnMessage,
    validate_claim_response,
)

__all__ = [
    "ALLOWED_WIN_CLAIMS",
    "AuditPayload",
    "AuditVerification",
    "CONTROL_KINDS",
    "ControlMessage",
    "MessageEnvelope",
    "MessageIdempotencyGuard",
    "NetworkProtocolError",
    "PROTOCOL_NAME",
    "PROTOCOL_VERSION",
    "ProtocolDecision",
    "REQUIRED_HANDSHAKE_TERMS",
    "REQUIRED_IDENTITY_FIELDS",
    "TurnMessage",
    "WIRE_PHASES",
    "WIRE_ROLES",
    "audit_records",
    "create_agreement",
    "now_iso",
    "seal_payload",
    "validate_claim_response",
    "validate_handshake_terms",
    "verify_agreement",
    "verify_audit_records",
    "verify_peer_identity",
    "verify_record",
]








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
