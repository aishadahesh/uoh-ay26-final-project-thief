# Gmail Reporting Setup

Modes:

- `dry_run`: build JSON/MIME preview only; no Gmail contact.
- `draft`: create a Gmail draft after explicit OAuth setup.
- `send`: send the final report after explicit authorization.

Required local secret files:

- `credentials.json`
- `token.json`

Both files must remain ignored by Git. The required OAuth scope is send-only Gmail scope as configured by the Gmail reporting implementation.

Dry-run readiness:

```powershell
uv run python -m police_thief doctor --role thief --offline
```

Do not run OAuth or real send from automation. Complete Google Cloud consent, OAuth client setup, and local token generation manually before switching from `dry_run`.

