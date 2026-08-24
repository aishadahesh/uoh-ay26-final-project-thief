"""Pre-game negotiation: signed agreement round-trips, term equality, and
peer identity checks.

Split by theme out of the original `test_network_protocol.py`."""

import pytest

from police_thief.services.network_protocol import (
    NetworkProtocolError,
    create_agreement,
    validate_handshake_terms,
    verify_agreement,
    verify_peer_identity,
)
from tests.unit.protocol_helpers import (
    _handshake_terms,
)


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
