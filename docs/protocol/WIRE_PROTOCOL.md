# Wire Protocol

Protocol name: `police-thief-mcp`

Protocol version: `3.0.0`

Canonical JSON hash procedure: JSON is serialized with sorted keys, UTF-8, and compact separators before SHA-256 hashing. The shared config fingerprint is SHA-256 over canonical `config/game.json`.

## Prematch Handshake

Each peer sends:

```json
{
  "terms": {
    "protocol_name": "police-thief-mcp",
    "protocol_version": "3.0.0",
    "schema_version": "1.00",
    "match_id": "MATCH-FAKE-001",
    "series_id": "SERIES-FAKE-001",
    "game_index": 1,
    "counted": false,
    "smoke_test": true,
    "config_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "shared_config_schema_version": "1.00",
    "num_games_declared": 6,
    "previous_counted_games": 0,
    "response_timeout_sec": 30,
    "watchdog_timeout_sec": 60,
    "capabilities": ["commit_reveal_sha256", "canonical_json", "non_counted_smoke"]
  },
  "nonce": "fake-nonce",
  "signature": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "identity": {
    "group_id": "fake-team",
    "group_name": "Fake Team",
    "role": "thief",
    "software_version": "1.00",
    "git_commit_hash": "cccccccccccccccccccccccccccccccccccccccc",
    "protocol": {"name": "police-thief-mcp", "version": "3.0.0"},
    "step0_hardware": {"os_name": "Windows", "cpu_count": 8, "ram_gb": 16, "gpu_present": false, "llm_model": "template"}
  }
}
```

Reject on config hash mismatch, schema/protocol mismatch, equal roles, match or series mismatch, counted/smoke mismatch, missing mandatory fields, or invalid capabilities.

## Turn Message

Outgoing turn messages use canonical fields: `protocol_version`, `match_id`, `series_id`, `message_id`, `correlation_id`, `sender`, `receiver`, `step`, `phase`, `message_type`, `commit`, `hint`, `smell_grid`, optional `barrier_placed`, optional `capture_claim`, optional `claim_response`, and optional `win_claim`.

Legacy parsers may accept older turn messages that omit match metadata, but outgoing messages must include it.

Protocol errors are reported structurally in tests through `NetworkProtocolError` and idempotency decisions: `wrong-match`, `wrong-series`, `wrong-role`, `wrong-receiver`, `wrong-phase`, `stale-turn`, `future-turn`, and `duplicate message_id`.

