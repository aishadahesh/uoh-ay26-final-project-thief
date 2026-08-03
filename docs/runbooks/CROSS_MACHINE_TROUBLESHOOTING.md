# Cross-Machine Troubleshooting

Connection refused: verify local server is running and firewall allows the configured port.

Firewall block: allow inbound traffic only for the intended peer port.

Incorrect `/mcp` path: ensure `opponent_url` ends with `/mcp`.

HTTP/HTTPS mismatch: tunnel URLs are usually HTTPS; loopback tests may be HTTP.

Expired tunnel: restart the tunnel manually and update private TOML.

Wrong port: compare `my_port`, server output, and tunnel target.

Config hash mismatch: compare doctor output fingerprints before playing.

Protocol-version mismatch: both peers must support `police-thief-mcp` version `3.0.0`.

Role conflict: one side must be `police`, the other `thief`.

Match-ID mismatch: restart with matching `match_id` and `series_id`.

Stale turn, duplicate message, or future turn: inspect `message_id`, `turn_number`, `phase`, and retry logs.

Invalid commitment or reveal: replay the log and compare SHA-256 commitments.

Barrier disagreement: verify barrier target, budget, bounds, duplicate target, and turn timing.

Capture disagreement: reconstruct previous police position, police move, barriers, thief position, and capture rule.

Timeout or watchdog failure: compare configured response/watchdog deadlines and local clock behavior.

Replay failure: do not submit; preserve logs and compare first tampered step.

Gmail dry-run failure: keep gameplay result unchanged, fix report generation, and do not send real mail until dry-run succeeds.

