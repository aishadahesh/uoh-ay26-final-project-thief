"""The wire vocabulary: protocol name and version, role and phase names,
control kinds, and the mandatory handshake/identity field sets."""

from __future__ import annotations

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
