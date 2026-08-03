# Police Peer Compatibility

This thief repository expects the police peer to expose the same FastMCP logical endpoints used by `PeerInboxes` and `McpPeerTransport`:

| Endpoint | Request model | Response model |
|---|---|---|
| agreement exchange | signed handshake object | signed handshake object |
| turn send/receive | `TurnMessage` JSON | `TurnMessage` JSON |
| audit exchange | `AuditPayload` JSON | `AuditPayload` JSON |
| control | `ControlMessage` JSON | acknowledgement or queued control state |

Required role rules:

- thief wire role is `thief`;
- police wire role is `police`;
- equal roles are rejected before turn 1;
- `match_id`, `series_id`, `counted`, `smoke_test`, config SHA-256, and schema version must match exactly.

Timeout behavior:

- `response_timeout_sec` comes from shared JSON;
- `watchdog_timeout_sec` is declared during handshake;
- retry must not apply a move twice;
- stale or future turns must be rejected.

Example public URL format: `https://example-tunnel.invalid/mcp`.

Use fake values only in documentation. Real tunnel URLs, tokens, OAuth files, and `.env` values must never be committed or printed.

