"""Turn and control messages: what may cross the wire, idempotency of
duplicate deliveries, and claim-response ordering.

Split by theme out of the original `test_network_protocol.py`."""

import pytest

from police_thief.services.network_protocol import (
    MessageIdempotencyGuard,
    NetworkProtocolError,
    TurnMessage,
    seal_payload,
    validate_claim_response,
    verify_record,
)
from tests.unit.protocol_helpers import (
    _envelope,
)


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


def test_claim_response_must_reference_the_last_public_claim() -> None:
    response = {"claim": [5, 6], "caught": True}
    validate_claim_response(response, [[5, 5], [5, 6]])

    with pytest.raises(NetworkProtocolError, match="expected one of"):
        validate_claim_response(response, [[5, 5]])


def test_turn_rejects_unknown_win_claim_type() -> None:
    record = seal_payload({"step": 1, "move": "N"})
    message = TurnMessage(
        step=1, sender="thief", hint="", smell_grid=[[0.0]],
        commit=record["commit"], timestamp="now", win_claim={"type": "invented"},
    )
    with pytest.raises(NetworkProtocolError, match="win_claim.type"):
        TurnMessage.from_dict(message.to_dict())
