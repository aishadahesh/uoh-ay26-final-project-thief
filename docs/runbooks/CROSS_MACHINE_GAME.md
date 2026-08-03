# Cross-Machine Game Runbook

Prerequisites on both machines:

- Python 3.11+ available.
- `uv` installed.
- both repositories checked out separately.
- identical `config/game.json` on both sides.
- private TOML configured under the local role directory.

Install:

```powershell
uv sync
```

Check local thief readiness:

```powershell
uv run python -m police_thief doctor --role thief --offline --json-output tmp\doctor-thief.json
```

Non-counted thief smoke peer:

```powershell
uv run python -m police_thief peer --role thief --smoke-test --non-counted
```

Tunnel setup is manual. Use placeholders only in docs:

- thief public MCP URL: `https://THIEF-TUNNEL.example/mcp`
- police public MCP URL: `https://POLICE-TUNNEL.example/mcp`

Values required from police machine:

- public MCP URL ending in `/mcp`;
- police role declaration `police`;
- police group ID and team name;
- police repository URL;
- police shared config SHA-256;
- police protocol version;
- counted/non-counted declaration;
- previous counted games against this thief team.

Proceed to an official counted game only after a non-counted smoke match completes, both result claims match, both logs replay as verified, and both peers agree on barrier/capture behavior.

