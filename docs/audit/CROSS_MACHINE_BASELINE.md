# Cross-Machine Baseline

Baseline captured before production edits on 2026-08-03.

## Repository State

- Branch: `main`
- Starting HEAD: `62fe9fa3cf9b6a29a3a2cad523ef4faff91b8e44`
- Recent commits: `62fe9fa Remove PDF compliance checklist`, `bb217d1 Make network setup thief-only`, `61f7fbc Prepare thief repository for submission`
- Worktree at start: no tracked modifications; `docs/audit/` untracked
- `git ls-files docs/audit`: empty, so historical audit files were untracked local evidence
- Historical audit commit: `bb217d10f1211050c2cafe7b06863a73146906d1`; current HEAD differs
- Environment: Python `3.13.3`, uv `0.11.23`

## Baseline Commands

| Command | Exit | Important output | Interpretation |
|---|---:|---|---|
| `uv sync` | 1 then 0 | sandbox cache access denied, rerun succeeded | environment-related first failure |
| `uv run python -c "import police_thief; print(police_thief.__version__)"` | 0 | `1.00` | package import works |
| `uv run python -m police_thief --help` | 0 | commands: `serve`, `peer`, `simulate`, `replay`, `demo`, `play` | no `doctor` at baseline |
| `uv run python -m police_thief simulate` | 0 | `outcome=survival ... turns_played=35` | local simulation works |
| `uv run pytest` | 0 | `453 passed, 1 skipped` | baseline test suite passes |
| `uv run pytest --cov` | 0 | `85.22%` | coverage barely above 85% gate |
| `uv run ruff check .` | 0 | all checks passed | lint passed |
| `uv run ruff format --check .` | 1 | 42 files would reformat | formatting failed |
| `uv run mypy src\police_thief` | 1 | 18 errors | typing failed |
| replay one-liner using old `verify_replay` name | 1 | import error | historical command stale |
| replay via `ReplaySession(load_log(...))` | 0 | verified 7 steps | replay API works |
| config load via `load_match_parameters` | 0 | `num_games=1` | Appendix F mismatch present |
| config fingerprint via `config_fingerprint` | 0 | `cba6a49e...` | fingerprint primitive works |
| bounded `serve --role thief` | 124 | process timed out | blocking server path exists; no startup banner |

## Existing Entry Points

- CLI: `serve`, `peer`, `simulate`, `replay`, `demo`, `play`
- Live network runtime: `NetworkMatchRunner`
- MCP server: `build_peer_server` / `run_peer_server`
- Historical state-machine path: `services/state_machine.py` and `services/orchestrator.py`

## PDF Evidence

- Primary PDF Appendix F, extracted page 138 / document page 154, Table 18: fixed game-series count is 6.
- Primary PDF Appendix B example shows `num_games: 1`; Appendix F controls numeric mandatory values.
- Appendix E pages 142-150 require process separation, config identity, mutual audit, Gmail reporting, game-count declarations, no secrets, and commit hash/token reporting.
- Secondary software guidelines require structured `src/`, `tests/`, documentation, lint/test gates, and coverage reporting.

