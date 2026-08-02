# PDF Compliance Checklist

This checklist tracks the repository against `police_thief_p2p.pdf` and
`software_submission_guidelines-V3.pdf`. It separates code-level compliance
from final submission actions that require real accounts, real opponents, or
the course submission system.

## Code-Level Checks

- [x] Exact PDF run commands are supported:
  - `uv run python -m police_thief peer --role police`
  - `uv run python -m police_thief peer --role thief`
  - `uv run python -m police_thief replay --log logs/police_match.json`
- [x] Existing internal commands remain supported:
  - `uv run python -m police_thief serve --role cop`
  - `uv run python -m police_thief serve --role thief`
  - `uv run python -m police_thief replay --log-file path/to/log.json`
- [x] This repository defaults to the thief role.
- [x] `police` / `cop` mode is marked and warned as local opponent testing only.
- [x] Two separate runtime config directories exist for local process isolation:
  `config/cop/` and `config/thief/`.
- [x] A submission-facing private TOML exists at `config/game.toml`.
- [x] `config/game.toml` mirrors `config/thief/game.toml` for the thief peer.
- [x] The shared signed game constitution exists at `config/game.json`.
- [x] Team identity code is 8 characters and has no spaces:
  `group_id = "ay26-uoh"`.
- [x] Required repo cross-links are present in config defaults.
- [x] Secrets are ignored: `.env`, `credentials.json`, `token.json`, keys, and
  local tool metadata.
- [x] Board mechanics enforce orthogonal movement only and reject illegal moves.
- [x] Thief out-of-bounds movement is treated as capture at the match layer.
- [x] Scoring table matches the required capture/survival/tie/technical-loss
  values.
- [x] Pheromone scent constants are fixed and validated.
- [x] Commit-reveal SHA-256 primitives and replay verification are implemented
  and tested.
- [x] FastMCP peer server/client plumbing is implemented and tested.
- [x] Reliability components exist: state machine, deadline tracker, watchdog,
  orchestrator.
- [x] Gmail reporting support uses JSON attachments and send-only OAuth scope.
- [x] Required project structure exists: `README.md`, `docs/PRD.md`,
  `docs/PLAN.md`, `docs/TODO.md`, per-mechanism PRDs, `pyproject.toml`,
  `uv.lock`, `.env-example`, and `.gitignore`.
- [x] Quality gates pass locally:
  - `uv run ruff check .`
  - `uv run pytest --cov`

## Manual Final-Submission Checks

- [x] Capture and insert the mandatory Live GUI screenshot.
- [x] Capture and insert the mandatory Replay Viewer `Verified OK` screenshot.
- [ ] Confirm the final real GitHub URLs in both cop and thief repositories.
- [ ] Confirm the sibling cop README links back to this thief repository.
- [ ] Run a real tunnel session with ngrok or Localtonet.
- [ ] Run at least the required real opponent matches against distinct teams.
- [ ] Complete Google Cloud OAuth setup and generate local `credentials.json`
  and `token.json` without committing them.
- [ ] Send real end-of-match JSON reports to
  `rmisegal+uoh26finalgame@gmail.com`.
- [ ] Create and push the final annotated `v1.0-submission` tag in both repos.
- [ ] Fill the official Word/PDF submission template without moving fields.
- [ ] Submit the required individual file for each team member through the
  official course submission system.
