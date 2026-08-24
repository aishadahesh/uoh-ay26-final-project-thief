"""Shared builders for the wire-protocol test modules: agreed handshake
terms and a signed message envelope.

Extracted when `test_network_protocol.py` was split by theme."""


from police_thief.services.network_protocol import (
    MessageEnvelope,
)


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
