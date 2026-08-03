# Cross-Machine Fix Report

- Starting commit: `62fe9fa3cf9b6a29a3a2cad523ef4faff91b8e44`
- Old audit commit differed: yes, old audit referenced `bb217d10f1211050c2cafe7b06863a73146906d1`
- Git operations performed: no commit, no push, no tag

## Files Changed

- `.gitignore`
- `config/game.json`
- `src/police_thief/domain/board.py`
- `src/police_thief/main.py`
- `src/police_thief/services/doctor.py`
- `src/police_thief/services/match_reports.py`
- `src/police_thief/services/network_match.py`
- `src/police_thief/services/network_protocol.py`
- `src/police_thief/services/network_state_machine.py`
- `src/police_thief/services/step0.py`
- focused unit/integration tests
- protocol docs, runbooks, and audit reports

## Requirements Fixed or Improved

- Appendix F fixed `num_games` now enforced as 6.
- Non-counted smoke metadata is separate from official shared series count.
- Prematch handshake includes protocol/schema/match/series/counting/config hash/capability fields.
- Peer identity validation rejects equal or wrong roles and missing commit metadata.
- Turn messages include match/series/message/correlation/phase metadata.
- Audit verification can reject commits copied from another match.
- Duplicate barrier placement is rejected.
- Result reports explicitly mark whether token usage is measured.
- `doctor` command performs local, secret-free readiness checks.

## Unresolved Risks

- Real two-machine police compatibility is not proven.
- Watchdog heartbeat is not fully integrated into every live network wait.
- Capture verification is still not fully reconstructed from revealed police moves.
- Barrier replay/network semantics are still partial beyond duplicate-target validation.
- Gmail OAuth/draft/send were intentionally not performed.
- Existing mypy errors remain outside the focused changes.

## Commands Run After Fixes

- `uv run ruff format .` -> pass
- `uv run ruff format --check .` -> pass
- `uv run ruff check .` -> pass
- `uv run pytest` -> `481 passed, 1 skipped`
- `uv run pytest --cov` -> `85.92%`
- `uv run mypy src\police_thief` -> fail, 18 errors
- `uv run python -m police_thief simulate` -> pass
- `uv run python -m police_thief doctor --role thief --offline --json-output tmp\doctor-final.json` -> pass

## Police-Side Changes Required

- Implement the same handshake fields and canonical config SHA-256 comparison.
- Emit/accept the turn metadata fields documented in `docs/protocol/WIRE_PROTOCOL.md`.
- Agree on non-counted smoke mode before local cross-machine testing.
- Preserve the same barrier and capture payload names.
