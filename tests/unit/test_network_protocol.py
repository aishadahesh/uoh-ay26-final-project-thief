"""Cryptographic and schema tests for protocol version 3."""

import pytest

from police_thief.services.network_protocol import (
    AuditPayload,
    MessageEnvelope,
    MessageIdempotencyGuard,
    NetworkProtocolError,
    TurnMessage,
    audit_records,
    create_agreement,
    seal_payload,
    validate_claim_response,
    validate_handshake_terms,
    verify_agreement,
    verify_audit_records,
    verify_peer_identity,
    verify_record,
)


def test_structurally_invalid_step0_is_unverified_but_not_tampering() -> None:
    verdict = verify_audit_records(
        [{"payload": {"hardware": "declared"}, "nonce": "n", "commit": "c"}],
        {},
        require_step0=True,
    )
    assert verdict.verified is False
    assert verdict.failed_steps == (-1, 0)
    assert verdict.cryptographic_failure is False


def test_changed_live_commit_is_cryptographic_failure() -> None:
    record = seal_payload({"step": 1, "role": "police", "move": "E"})
    verdict = verify_audit_records([record], {1: "0" * 64})
    assert verdict.verified is False
    assert verdict.failed_steps == (1,)
    assert verdict.cryptographic_failure is True


def test_audit_accepts_sealed_capture_answer_auxiliary_records() -> None:
    turn = seal_payload({"step": 1, "role": "thief", "move": "E"})
    answer = seal_payload({
        "kind": "capture_answer",
        "role": "thief",
        "at_step": 1,
        "claim_cell": [1, 0],
        "answer": False,
    })

    verdict = verify_audit_records([turn, answer], {1: turn["commit"]})

    assert verdict.verified is True
    assert verdict.failed_steps == ()


def test_audit_accepts_capture_answer_auxiliary_records_with_step_alias() -> None:
    turn = seal_payload({"kind": "step", "step": 1, "role": "thief", "move": "E"})
    answer = seal_payload({
        "kind": "capture_answer",
        "role": "thief",
        "step": 1,
        "at_step": 1,
        "claim_cell": [1, 0],
        "answer": False,
    })

    verdict = verify_audit_records([turn, answer], {1: turn["commit"]})

    assert verdict.verified is True
    assert verdict.failed_steps == ()


def test_audit_accepts_sealed_survival_claim_auxiliary_record() -> None:
    turn = seal_payload({"kind": "step", "step": 35, "role": "thief", "move": "N"})
    claim = seal_payload({
        "kind": "survival_claim",
        "role": "thief",
        "step": 35,
        "steps": 35,
    })

    verdict = verify_audit_records([turn, claim], {35: turn["commit"]})

    assert verdict.verified is True
    assert verdict.failed_steps == ()


def test_audit_rejects_tampered_capture_answer_auxiliary_record() -> None:
    answer = seal_payload({
        "kind": "capture_answer",
        "role": "thief",
        "at_step": 1,
        "claim_cell": [1, 0],
        "answer": False,
    })
    answer["payload"]["answer"] = True

    verdict = verify_audit_records([answer], {})

    assert verdict.verified is False
    assert verdict.cryptographic_failure is True


def test_audit_payload_omits_unset_consensus_sha() -> None:
    payload = AuditPayload("thief", [], "survival").to_dict()
    assert "consensus_sha" not in payload


def test_audit_payload_accepts_valid_consensus_sha() -> None:
    digest = "a" * 64
    payload = AuditPayload("thief", [], "series_consensus", consensus_sha=digest)
    assert AuditPayload.from_dict(payload.to_dict()).consensus_sha == digest


@pytest.mark.parametrize("digest", ["A" * 64, "a" * 63, "g" * 64, 123])
def test_audit_payload_rejects_invalid_consensus_sha(digest) -> None:
    with pytest.raises(NetworkProtocolError, match="consensus_sha"):
        AuditPayload.from_dict({
            "sender": "thief", "records": [],
            "result_claim": "series_consensus", "consensus_sha": digest,
        })


def test_audit_payload_ignores_peer_metadata_fields() -> None:
    payload = AuditPayload.from_dict({
        "sender": "thief", "records": [], "result_claim": "survival",
        "sub_game": 1, "future_unagreed_field": True,
    })
    assert payload.sender == "thief"
    assert payload.records == []
    assert payload.result_claim == "survival"


def test_signed_negotiation_round_trip():
    terms = {"board_size": 7, "max_steps": 35}
    message = create_agreement(terms, {"group_name": "Alpha"})
    assert verify_agreement(message, terms) == {"group_name": "Alpha"}


def test_signed_negotiation_carries_public_conformance_manifest():
    terms = {"board_size": 7}
    manifest = {"game_config_sha256": "a" * 64}
    message = create_agreement(terms, {"group_name": "Alpha"}, manifest)
    assert message["conformance"] == manifest
    assert verify_agreement(message, terms) == {"group_name": "Alpha"}


def test_negotiation_rejects_non_object_terms():
    message = {"terms": [], "nonce": "x", "signature": "y", "identity": {}}
    with pytest.raises(NetworkProtocolError, match="terms must be an object"):
        verify_agreement(message, {})


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


def test_claim_response_must_reference_the_last_public_claim() -> None:
    response = {"claim": [5, 6], "caught": True}
    validate_claim_response(response, [[5, 5], [5, 6]])

    with pytest.raises(NetworkProtocolError, match="expected one of"):
        validate_claim_response(response, [[5, 5]])


def test_audit_accepts_peer_specific_move_schema_but_rejects_tampering() -> None:
    peer_record = seal_payload({
        "step": 1, "role": "thief", "state": {}, "move": "MOVE:S", "intent": True,
    })
    assert audit_records([peer_record], {1: peer_record["commit"]}) == (True, [])

    peer_record["payload"]["move"] = "MOVE:N"
    assert audit_records([peer_record], {1: peer_record["commit"]}) == (False, [1])


def test_turn_rejects_unknown_win_claim_type() -> None:
    record = seal_payload({"step": 1, "move": "N"})
    message = TurnMessage(
        step=1, sender="thief", hint="", smell_grid=[[0.0]],
        commit=record["commit"], timestamp="now", win_claim={"type": "invented"},
    )
    with pytest.raises(NetworkProtocolError, match="win_claim.type"):
        TurnMessage.from_dict(message.to_dict())
