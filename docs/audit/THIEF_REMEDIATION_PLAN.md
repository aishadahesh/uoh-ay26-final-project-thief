# Thief Remediation Plan

Audit date: 2026-08-03  
Audited commit: `bb217d10f1211050c2cafe7b06863a73146906d1`

## P0

No P0 finding was confirmed locally. No tracked or history-secret exposure was found, and the replay/commit primitives reject tampering. This does not make the repo safe to submit because P1/P2 blockers remain.

## P1 - Mandatory Functionality / Rule Compliance

| ID | Requirement reference | Affected files | Proposed change | Test required | Dependencies | Difficulty | Regression risk |
|---|---|---|---|---|---|---|---|
| P1-001 | F-022, E-012, E-031 | `config/game.json`, `src/police_thief/shared/game_config.py`, tests, README/docs | Align `num_games` with Appendix F's fixed value of 6, not Appendix B's example value of 1. | Config loader test; network settings test; docs consistency check. | None. | Low-Medium | Medium: existing tests/docs currently assume 1. |
| P1-002 | E-003 | `src/police_thief/services/orchestrator.py`, `network_match.py`, `main.py` | Define one authoritative runtime orchestrator path, or make `NetworkMatchRunner` explicitly use the state machine/orchestrator responsibilities. | Integration test proving full match path goes through state transitions. | None. | Medium | Medium. |
| P1-003 | E-007, F-033 | `network_match.py`, `watchdog.py`, report/log manager | Add watchdog heartbeat and controlled failure/report behavior to the real network match loop. | Opponent hang/disconnect tests; restart/timeout tests. | None. | Medium | Medium. |
| P1-004 | E-011, E-023 | `network_match.py`, `network_protocol.py`, Step-0/report files | Exchange and compare full `config_sha256` before match start; reject mismatches before any turn. | Mismatched-config integration test. | Sibling repo must use same protocol. | Medium | High interop risk. |
| P1-005 | E-015, E-016, E-046 | `network_match.py`, `network_protocol.py`, `domain/replay.py`, tests | Implement network barrier placement, sealed barrier payloads, validation, and replay display/audit. | Legal barrier, illegal barrier, barrier-on-thief capture, false barrier audit tests. | None. | Medium-High | High: affects turn semantics. |
| P1-006 | E-021, E-022 | `network_match.py`, `network_protocol.py`, replay/audit tests | Validate capture claims by reconstructing opponent legal position from revealed payloads and board rules, not only by comparing claim coordinate to thief position. | False capture, stale capture, impossible move then capture, copied-commit tests. | None. | High | High. |
| P1-007 | E-010, E-035, E-036 | configs, README, possibly `NetworkSetupDialog` | Run and document a real cross-machine/tunnel match against the sibling cop repo; save logs/results. | Manual plus automated replay of generated log. | ngrok/Localtonet, sibling repo, two processes/machines. | Medium | Low code risk, high environment risk. |
| P1-008 | E-032, E-051 | `config/*.toml`, `network_reporting.py`, Gmail setup docs | Complete real OAuth setup and verify authorized draft/send mode without leaking credentials. | Manual OAuth; mocked send remains in CI; dry-run/send result artifact. | Google Cloud/Gmail account. | Medium | Security-sensitive. |

## P2 - Mandatory Submission / Documentation / Test Issues

| ID | Requirement reference | Affected files | Proposed change | Test required | Dependencies | Difficulty | Regression risk |
|---|---|---|---|---|---|---|---|
| P2-001 | E-041 | Git metadata | Create annotated `v1.0-submission` tag only at final submission time. | `git show v1.0-submission`. | User approval. | Low | Low. |
| P2-002 | Q-005 | 42 Python files | Run `uv run ruff format .` after remediation approval. | `uv run ruff format --check .`; full pytest. | None. | Low | Low-Medium due broad formatting churn. |
| P2-003 | E-049 | README, result JSON artifacts, sibling cop repo | Verify sibling repo exists, is accessible to grader, and links back to this thief repo. | Remote link check if network available. | GitHub/network. | Low | Low. |
| P2-004 | E-037, E-038, E-052 | league/reporting modules | Track opponent identity, prior counted games, warmups, and counted-game declarations. | Unit tests for duplicate opponent/game count and false declaration. | League policy input. | Medium | Medium. |
| P2-005 | E-054, F-025 | `gemini_agent.py`, `network_match.py`, result reports | Capture real LLM input/output token usage and write it into `TokenUsage`. | Gemini fake-response test including token metadata; result JSON assertion. | Provider response metadata. | Medium | Low-Medium. |
| P2-006 | Audit adversarial suite | tests/integration and tests/unit | Add missing adversarial tests: duplicate turn, stale turn, copied commit from another game, missing reveal, corrupted network log, opponent timeout/disconnect, service restart. | New tests must fail before fix and pass after. | None. | Medium-High | Medium. |

## P3 - Quality Improvements

| ID | Requirement reference | Affected files | Proposed change | Test required | Dependencies | Difficulty | Regression risk |
|---|---|---|---|---|---|---|---|
| P3-001 | Q-003 | `network_match.py`, `play_app.py`, `network_setup.py`, `main.py`, other long files | Done 2026-08-24 for every file except `network_match.py` (documented exception, TODO T0899): split by responsibility into facade/mixin modules, suites unchanged (627/2 thief). | Full test suite; CLI and GUI smoke tests; byte-diff of moved method bodies for the strategy planner. | None. | Medium | Done except the one exception. |
| P3-002 | Q-009 | `pyproject.toml`, typed boundaries | Add intentional mypy configuration or fix the 18 reported errors/stub gaps. | `uv run mypy src\police_thief`. | Stubs/config decisions. | Medium | Low. |
| P3-003 | Q-010 | `pyproject.toml`, docs | Add dependency vulnerability scanning command if permitted. | `uv run <audit tool>` in test-results doc. | Network/advisory database access. | Low | Low. |
| P3-004 | Coverage gaps | `network_match_app.py`, `network_reporting.py`, `gmail_oauth.py`, `mcp_client.py` | Increase coverage above a less fragile buffer, targeting >90% for network/report paths. | `uv run pytest --cov`. | None. | Medium | Low-Medium. |
| P3-005 | Security hardening | `step0.py`, subprocess call sites | Make `get_git_commit_hash` safe-directory robust or documented for sandboxed environments. | Unit test with explicit `safe.directory` or mocked subprocess. | Git config policy. | Low | Low. |

