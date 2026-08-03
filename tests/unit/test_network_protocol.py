"""Cryptographic and schema tests for protocol version 3."""

import pytest

from police_thief.services.network_protocol import (
    MessageEnvelope,
    MessageIdempotencyGuard,
    NetworkProtocolError,
    TurnMessage,
    audit_records,
    create_agreement,
    seal_payload,
    validate_handshake_terms,
    verify_agreement,
    verify_peer_identity,
    verify_record,
)


def test_signed_negotiation_round_trip():
    terms = {"board_size": 7, "max_steps": 35}
    message = create_agreement(terms, {"group_name": "Alpha"})
    assert verify_agreement(message, terms) == {"group_name": "Alpha"}


def test_negotiation_rejects_different_terms():
    message = create_agreement({"board_size": 7}, {})
    with pytest.raises(NetworkProtocolError, match="do not match"):
        verify_agreement(message, {"board_size": 8})


def test_turn_contains_commit_but_no_private_truth():
    record = seal_payload({"step": 1, "state": "private", "move": "N", "intent": True})
    turn = TurnMessage(
        step=1,
        sender="thief",
        hint="near the river",
        smell_grid={},
        commit=record["commit"],
        timestamp="2026-07-31T00:00:00Z",
    ).to_dict()
    assert set(turn).isdisjoint({"state", "move", "intent", "nonce"})
    assert verify_record(record)


def test_audit_detects_tampering_and_missing_steps():
    record = seal_payload({"step": 2, "state": {}, "move": "E", "intent": True})
    expected = {2: record["commit"]}
    assert audit_records([record], expected) == (True, [])
    record["payload"]["move"] = "W"
    assert audit_records([record], expected) == (False, [2])
    assert audit_records([], expected) == (False, [2])


def _handshake_terms(**overrides):
    terms = {
        "protocol_name": "police-thief-mcp",
        "protocol_version": "3.0.0",
        "schema_version": "1.00",
        "match_id": "MATCH-1",
        "series_id": "SERIES-1",
        "game_index": 1,
        "counted": False,
        "smoke_test": True,
        "config_sha256": "a" * 64,
        "shared_config_schema_version": "1.00",
        "num_games_declared": 6,
        "previous_counted_games": 0,
        "response_timeout_sec": 30,
        "watchdog_timeout_sec": 60,
        "capabilities": ["commit_reveal_sha256"],
    }
    terms.update(overrides)
    return terms


def test_strict_handshake_terms_require_config_hash_and_game_count():
    validate_handshake_terms(_handshake_terms())
    with pytest.raises(NetworkProtocolError, match="missing mandatory"):
        validate_handshake_terms({"protocol_name": "police-thief-mcp"})
    with pytest.raises(NetworkProtocolError, match="num_games_declared"):
        validate_handshake_terms(_handshake_terms(num_games_declared=0))


def test_peer_identity_rejects_role_conflict_and_missing_commit():
    identity = {
        "group_id": "team-a",
        "group_name": "Team A",
        "role": "police",
        "software_version": "1.00",
        "git_commit_hash": "a" * 40,
        "protocol": {"name": "police-thief-mcp", "version": "3.0.0"},
        "step0_hardware": {"os_name": "Windows"},
    }
    assert verify_peer_identity(identity, "police") == identity
    with pytest.raises(NetworkProtocolError, match="expected opponent role"):
        verify_peer_identity(identity, "thief")
    broken = dict(identity)
    broken["git_commit_hash"] = ""
    with pytest.raises(NetworkProtocolError, match="git commit hash"):
        verify_peer_identity(broken, "police")


def _envelope(**overrides):
    data = {
        "protocol_version": "3.0.0",
        "match_id": "MATCH-1",
        "series_id": "SERIES-1",
        "message_id": "m-1",
        "correlation_id": "turn-1",
        "sender_role": "police",
        "receiver_role": "thief",
        "turn_number": 4,
        "phase": "TURN_COMMIT",
        "message_type": "turn",
        "payload": {"commit": "b" * 64},
        "integrity": {"hash": "c" * 64},
    }
    data.update(overrides)
    return MessageEnvelope.from_dict(data)


def test_message_guard_accepts_once_and_returns_cached_response_on_duplicate():
    guard = MessageIdempotencyGuard(
        match_id="MATCH-1",
        series_id="SERIES-1",
        expected_sender_role="police",
        expected_receiver_role="thief",
        expected_phase="TURN_COMMIT",
        expected_turn_number=4,
    )
    accepted = guard.accept(_envelope(), {"ok": True})
    duplicate = guard.accept(_envelope())
    assert accepted.status == "ACCEPTED"
    assert duplicate.status == "DUPLICATE"
    assert duplicate.cached_response == {"ok": True}


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"match_id": "OTHER"}, "wrong-match"),
        ({"series_id": "OTHER"}, "wrong-series"),
        ({"sender_role": "thief", "receiver_role": "police"}, "wrong-role"),
        ({"receiver_role": "police", "sender_role": "thief"}, "wrong-role"),
        ({"phase": "FINAL_AUDIT"}, "wrong-phase"),
        ({"turn_number": 3}, "stale-turn"),
        ({"turn_number": 5}, "future-turn"),
    ],
)
def test_message_guard_rejects_wrong_identity_order_and_phase(overrides, reason):
    guard = MessageIdempotencyGuard(
        match_id="MATCH-1",
        series_id="SERIES-1",
        expected_sender_role="police",
        expected_receiver_role="thief",
        expected_phase="TURN_COMMIT",
        expected_turn_number=4,
    )
    assert guard.accept(_envelope(**overrides)).reason == reason


def test_audit_rejects_commit_copied_from_another_match():
    record = seal_payload(
        {"step": 2, "match_id": "MATCH-2", "state": {}, "move": "E", "intent": True}
    )
    assert audit_records([record], {2: record["commit"]}, match_id="MATCH-1") == (False, [2])
