"""Step-0 attestation and the mutual log audit: what counts as tampering and
what is merely unverified.

Split by theme out of the original `test_network_protocol.py`."""

import pytest

from police_thief.services.network_protocol import (
    AuditPayload,
    NetworkProtocolError,
    audit_records,
    seal_payload,
    verify_audit_records,
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


def test_audit_payload_still_rejects_unagreed_unknown_fields() -> None:
    with pytest.raises(NetworkProtocolError, match="malformed audit payload"):
        AuditPayload.from_dict({
            "sender": "thief", "records": [], "result_claim": "survival",
            "future_unagreed_field": True,
        })


def test_audit_detects_tampering_and_missing_steps():
    record = seal_payload({"step": 2, "state": {}, "move": "E", "intent": True})
    expected = {2: record["commit"]}
    assert audit_records([record], expected) == (True, [])
    record["payload"]["move"] = "W"
    assert audit_records([record], expected) == (False, [2])
    assert audit_records([], expected) == (False, [2])


def test_audit_rejects_commit_copied_from_another_match():
    record = seal_payload(
        {"step": 2, "match_id": "MATCH-2", "state": {}, "move": "E", "intent": True}
    )
    assert audit_records([record], {2: record["commit"]}, match_id="MATCH-1") == (False, [2])


def test_audit_accepts_peer_specific_move_schema_but_rejects_tampering() -> None:
    peer_record = seal_payload({
        "step": 1, "role": "thief", "state": {}, "move": "MOVE:S", "intent": True,
    })
    assert audit_records([peer_record], {1: peer_record["commit"]}) == (True, [])

    peer_record["payload"]["move"] = "MOVE:N"
    assert audit_records([peer_record], {1: peer_record["commit"]}) == (False, [1])
