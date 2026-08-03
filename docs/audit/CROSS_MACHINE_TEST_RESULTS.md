# Cross-Machine Test Results

## Baseline Before Fixes

| Command | Exit | Important output | Interpretation |
|---|---:|---|---|
| `uv sync` | 1 then 0 | uv cache denied in sandbox; rerun succeeded | environment first failure, dependencies valid |
| package import | 0 | `1.00` | ok |
| CLI help | 0 | no `doctor` command | baseline gap |
| local simulation | 0 | `survival`, 35 turns | ok |
| full pytest | 0 | `453 passed, 1 skipped` | ok |
| coverage | 0 | `85.22%` | above gate |
| Ruff lint | 0 | all checks passed | ok |
| Ruff format check | 1 | 42 files would reformat | failed |
| mypy | 1 | 18 errors | failed |
| replay via current API | 0 | verified 7 steps | ok |
| config load/fingerprint | 0 | `num_games=1`, SHA generated | mismatch with Appendix F |
| bounded server startup | 124 | blocking process timed out | server command blocks; no persistent process left |

## Focused Post-Fix Checks

| Command | Exit | Important output | Interpretation |
|---|---:|---|---|
| `uv run pytest tests\unit\test_network_protocol.py tests\unit\test_network_state_machine.py tests\unit\test_doctor.py tests\unit\test_network_match_terms.py tests\unit\test_game_config.py tests\unit\test_board.py tests\integration\test_network_match.py` | 0 | `81 passed` | focused fixes pass |
| `uv run python -m police_thief doctor --role thief --offline --json-output tmp\doctor-baseline.json` | 0 | all local checks PASS except submission tag MANUAL CHECK | local smoke readiness command works |

## Final Gates

| Command | Exit | Important output | Interpretation |
|---|---:|---|---|
| `uv run ruff format .` | 0 | `48 files reformatted, 63 files left unchanged` | formatting applied |
| `uv run ruff format --check .` | 0 | `111 files already formatted` | format gate passes |
| `uv run ruff check .` | 0 | `All checks passed!` | lint gate passes |
| `uv run pytest` | 0 | `481 passed, 1 skipped` | full suite passes |
| `uv run pytest --cov` | 0 | `85.92%` | coverage above 85% |
| `uv run mypy src\police_thief` | 1 | `18 errors in 11 files` | same count as baseline; no new mypy debt observed in new modules |
| `uv run python -m police_thief simulate` | 0 | `outcome=survival ... turns_played=35` | simulation still passes |
| `uv run python -m police_thief doctor --role thief --offline --json-output tmp\doctor-final.json` | 0 | local checks PASS; submission tag MANUAL CHECK | doctor readiness command passes offline |

## Local Two-Process Result

No real two-OS-process smoke game was run in this pass. Existing in-memory two-peer integration passed, but it is not equivalent to the requested local two-process evidence.
