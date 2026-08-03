# Thief Requirements Traceability Matrix

Audit date: 2026-08-03  
Audited commit: `bb217d10f1211050c2cafe7b06863a73146906d1`

Status counts in this matrix: PASS 69, PARTIAL 16, FAIL 7, NOT TESTED 4, NOT APPLICABLE 2.

Severity scale: P0 = cheating/invalid result/secret exposure; P1 = mandatory functionality incorrect or missing; P2 = mandatory documentation/testing/submission issue; P3 = quality recommendation.

## Appendix F Mandatory Parameters

Appendix F of `police_thief_p2p.pdf` is treated as the highest authority for numeric values. Appendix B examples are treated as examples when they conflict with Appendix F.

| ID | Source | Requirement summary | Level | Applicability | Implementation / test evidence | Verification | Status | Severity | Remediation |
|---|---|---|---|---|---|---|---|---|---|
| F-001 | Primary PDF App. F table 13 p.152 | Board grid side is at least 7x7. | MUST | Thief validates shared board. | `config/game.json`; `BoardConfig`; `test_load_match_parameters_reads_the_real_shipped_config` | Config smoke printed `7`. | PASS | - | None. |
| F-002 | App. F table 13 p.152 | Number of agents is fixed at 2. | MUST | Shared model. | `config/game.json` has `num_agents: 2`; Dec-POMDP tests. | Static inspection. | PASS | - | None. |
| F-003 | App. F table 13 p.152 | Origin corner is top-left unless mutually agreed. | MUST | Coordinate convention. | `config/game.json`; `BoardConfig.axis_origin_corner`. | Static inspection. | PASS | - | None. |
| F-004 | App. F table 13 p.152 | Axis start index is 0 unless mutually agreed. | MUST | Coordinate convention. | `config/game.json`; `BoardConfig.axis_start_index`. | Static inspection. | PASS | - | None. |
| F-005 | App. F table 13 p.152 | Thief starts at `(3,3)`. | MUST | Thief-side initial state. | `config/game.json`; `MatchParameters.thief_start`. | Config smoke printed `Position(row=3, col=3)`. | PASS | - | None. |
| F-006 | App. F table 13 p.152 | Police starts at `(0,0)`. | MUST | Opponent initial state validation. | `config/game.json`; `MatchParameters.cop_start`. | Config smoke printed `Position(row=0, col=0)`. | PASS | - | None. |
| F-007 | App. F table 14 p.152 | Map area is negotiated; default/example may be blank or New York. | MUST | Hint context only. | `WorldConfig.map_area`; `config/game.json`. | Static inspection. | PASS | - | None. |
| F-008 | App. F table 14 p.152 | Hints are capped at 15 words. | MUST | Thief hints. | `WorldConfig.hint_max_words`; `TemplateHintProvider`; `test_template_provider_respects_a_config_supplied_word_limit`. | Tests passed. | PASS | - | None. |
| F-009 | App. F table 15 p.153 | Move set is N/S/E/W/STAY; no diagonals. | MUST | Thief movement. | `Move` enum; `Board.apply_move`; board tests. | Tests passed. | PASS | - | None. |
| F-010 | App. F table 15 p.153 | Max barrier budget is at least 14. | MUST | Thief validates police barriers. | `MIN_MAX_BARRIERS`; `Board.place_barrier`; `test_load_match_parameters_rejects_max_barriers_below_floor`. | Tests passed. | PASS | - | None. |
| F-011 | App. F table 15 p.153 | Max moves is at least 35. | MUST | Match termination. | `config/game.json`; simulation uses `params.max_moves`. | Simulation ended at 35 turns. | PASS | - | None. |
| F-012 | App. F table 15 p.153 | Survival threshold is at least 35. | MUST | Thief survival condition. | `config/game.json`; simulation tests. | Tests passed. | PASS | - | None. |
| F-013 | App. F table 16 p.153 | Scent center intensity is fixed at 0.9. | MUST | Scent/replay/belief. | `ScentConfig`; `_validate_fixed_scent_config`; `test_default_config_matches_mandatory_parameters_table`. | Config smoke printed `0.9`. | PASS | - | None. |
| F-014 | App. F table 16 p.153 | Scent decay is fixed at 0.10. | MUST | Scent/replay/belief. | `ScentConfig`; `ScentField.decay`; scent tests. | Config smoke printed `0.1`. | PASS | - | None. |
| F-015 | App. F table 16 p.153 | Scent field size is fixed at 5x5. | MUST | Scent/replay/belief. | `ScentConfig`; `_validate_fixed_scent_config`. | Config smoke printed `5`. | PASS | - | None. |
| F-016 | App. F table 17 p.154 | Capture gives cop 20. | MUST | Scoring. | `config/game.json`; `ScoringTable`; scoring tests. | Tests passed. | PASS | - | None. |
| F-017 | App. F table 17 p.154 | Capture gives thief 5. | MUST | Scoring. | `config/game.json`; `ScoringTable`; scoring tests. | Tests passed. | PASS | - | None. |
| F-018 | App. F table 17 p.154 | Survival gives cop 5. | MUST | Scoring. | `config/game.json`; simulation output. | Simulation printed `cop_score=5`. | PASS | - | None. |
| F-019 | App. F table 17 p.154 | Survival gives thief 10. | MUST | Scoring. | `config/game.json`; simulation output. | Simulation printed `thief_score=10`. | PASS | - | None. |
| F-020 | App. F table 17 p.154 | Tie score is 2 each. | MUST | Scoring. | `config/game.json`; `score_for`. | Static/tests. | PASS | - | None. |
| F-021 | App. F table 17 p.154 | Technical loss score is 0. | MUST | Scoring. | `config/game.json`; `score_for`. | Tests passed. | PASS | - | None. |
| F-022 | App. F table 18 p.154 | Number of games in a series is fixed at 6. | MUST | League config. | Local `config/game.json` has `num_games: 1`; code enforces `FIXED_NUM_GAMES = 1`. | PDF comparison. | FAIL | P1 | Change shared config and loader constant to Appendix F value, then update tests/docs. |
| F-023 | App. F table 18 p.154 | Diversity reward is fixed at 10. | MUST | League scoring. | `config/game.json`; `NetworkLeagueConfig`. | Static inspection. | PASS | - | None. |
| F-024 | App. F table 18 p.154 | Minimum games to pass is 2. | MUST | League readiness. | `config/game.json`; `NetworkLeagueConfig`. | Static inspection. | PASS | - | None. |
| F-025 | App. F table 18 p.154 | Token budget per series is about 200000. | MUST | LLM/reporting. | `config/game.json`; `TokenUsage` in result reports. | Static inspection. | PARTIAL | P2 | Actual Gemini usage is not accumulated into `TokenUsage()` in `NetworkMatchRunner._write_result`. |
| F-026 | App. F table 18 p.154 | Maximum games per team is fixed at 10. | MUST | League readiness. | `config/game.json`; loader validation. | Static inspection. | PASS | - | None. |
| F-027 | App. F table 19 p.155 | Requests per minute floor is 30. | MUST | Gatekeeper. | `config/game.json`; `MIN_REQUESTS_PER_MINUTE`. | Static/tests. | PASS | - | None. |
| F-028 | App. F table 19 p.155 | Concurrent requests floor is 2. | MUST | Gatekeeper. | `config/game.json`; `MIN_CONCURRENT_REQUESTS`. | Static/tests. | PASS | - | None. |
| F-029 | App. F table 19 p.155 | Retry backoff floor is 5 seconds. | MUST | Gatekeeper/network. | `config/game.json`; `MIN_RETRY_BACKOFF_SEC`. | Static/tests. | PASS | - | None. |
| F-030 | App. F table 19 p.155 | Max retries floor is 3. | MUST | Gatekeeper/network. | `config/game.json`; `MIN_MAX_RETRIES`. | Static/tests. | PASS | - | None. |
| F-031 | App. F table 19 p.155 | Queue depth floor is 100. | MUST | Gatekeeper. | `config/game.json`; `MIN_QUEUE_DEPTH`. | Static/tests. | PASS | - | None. |
| F-032 | App. F table 19 p.155 | Response timeout is 30 seconds unless negotiated upward. | MUST | Network. | `config/game.json`; `NetworkMatchRunner` uses `params.network_league.response_timeout_sec`. | Static inspection. | PASS | - | None. |
| F-033 | App. F table 19 p.155 | Watchdog timeout is 60 seconds. | MUST | Reliability. | `config/game.json`; `Watchdog` tests. | Tests passed. | PARTIAL | P1 | `NetworkMatchRunner` does not instantiate/use `Watchdog`; only `Orchestrator` path does. |

## Appendix E Mandatory Rules

| ID | Source | Requirement summary | Level | Applicability | Implementation / test evidence | Verification | Status | Severity | Remediation |
|---|---|---|---|---|---|---|---|---|---|
| E-001 | Primary PDF App. E p.143 | Police and thief run as separate processes. | MUST | Thief process. | CLI `serve`/`peer`; server smoke test. | Server started on port 8802. | PASS | - | None. |
| E-002 | App. E p.143 | No shared memory or mutable state between peers. | MUST | P2P isolation. | Separate OS process model; no sibling police import found. | Static inspection. | PASS | - | None. |
| E-003 | App. E p.143 | Orchestrator is the single entry point to subsystems. | MUST | Thief runtime. | `Orchestrator.run_turn`; `NetworkMatchRunner.run`. | Static inspection. | PARTIAL | P1 | There are two independent orchestration paths; unify or document primary runtime path. |
| E-004 | App. E p.143 | Game states are managed by a state machine. | MUST | Protocol. | `MatchStateMachine`; state-machine tests. | Tests passed. | PASS | - | None. |
| E-005 | App. E p.143 | Illegal transitions are rejected. | MUST | Protocol. | `IllegalStateTransitionError`; tests. | Tests passed. | PASS | - | None. |
| E-006 | App. E p.143 | Deadline tracking prevents indefinite waits. | MUST | Network. | `DeadlineTracker`; `McpPeerTransport` timeouts. | Tests passed. | PASS | - | None. |
| E-007 | App. E p.143 | Watchdog monitors process/crash paths. | MUST | Reliability. | `Watchdog` exists; `Orchestrator` uses it. | Tests passed. | PARTIAL | P1 | Main network match loop lacks watchdog integration and crash-recovery persistence. |
| E-008 | App. E p.143 | Live GUI displays only local truth. | MUST | Thief GUI. | `LiveViewModel` has no opponent-position field; tests. | Tests passed. | PASS | - | None. |
| E-009 | App. E p.143 | Live GUI must not show full objective board state. | MUST | Thief GUI. | GUI tests verify belief-only render path. | Tests passed. | PASS | - | None. |
| E-010 | App. E p.144 | Public tunnel exposes each local FastMCP peer. | MUST | League play. | Docs mention ngrok/Localtonet. | No tunnel run. | NOT TESTED | P1 | Run real tunnel and cross-machine smoke test. |
| E-011 | App. E p.144 | Shared config is byte-identical on both sides. | MUST | P2P agreement. | `config_fingerprint`; `create_agreement` terms. | Sibling repo not verified. | PARTIAL | P1 | Exchange/compare full `config_sha256` before match start and verify sibling repo. |
| E-012 | App. E p.144 | Mandatory parameter floors/fixed values are not lowered. | MUST | Shared config. | Most values pass; `num_games` lowered to 1. | Appendix F comparison. | FAIL | P1 | Fix `num_games` per Appendix F. |
| E-013 | App. E p.144 | Movement is orthogonal only. | MUST | Game logic. | `Move` enum and `_DELTA`. | Tests passed. | PASS | - | None. |
| E-014 | App. E p.144 | Diagonal moves are forbidden. | MUST | Game logic. | No diagonal enum; tests. | Tests passed. | PASS | - | None. |
| E-015 | App. E p.144 | Barrier placement is openly declared. | MUST | Thief validation of cop. | `TurnMessage.barrier_placed` exists; runner does not process it. | Static inspection. | PARTIAL | P1 | Implement and test barrier placement on network turns. |
| E-016 | App. E p.144 | Barrier locations must not be falsified. | MUST | Thief audit. | Commit/audit primitives can detect payload tamper. | No live barrier audit. | PARTIAL | P1 | Include barrier declarations in sealed payload validation and replay. |
| E-017 | App. E p.145 | SHA-256 commit-reveal is used. | MUST | Protocol/crypto. | `commit_reveal.py`; `seal_payload`; tests. | Tests passed. | PASS | - | None. |
| E-018 | App. E p.145 | Nonce remains secret until reveal/audit. | MUST | Crypto. | `TurnMessage` carries commit only; audit records reveal nonce at end. | `test_turn_contains_commit_but_no_private_truth`. | PASS | - | None. |
| E-019 | App. E p.145 | Audit-stage hash mismatch fails match. | MUST | Integrity. | `audit_records`, `ReplaySession`. | Tamper tests pass. | PASS | - | None. |
| E-020 | App. E p.145 | Replay/audit app exists and verifies logs. | MUST | Replay. | `ReplaySession`, `ReplayGUI`; sample replay smoke. | `verified True steps 7`. | PASS | - | None. |
| E-021 | App. E p.145 | Capture is declared truthfully. | MUST | Thief/capture. | Thief checks claim coordinate against own position. | Static/tests. | PARTIAL | P1 | Verify cop position and capture legality from revealed payload, not just claim coordinate. |
| E-022 | App. E p.145 | False capture declarations are forbidden. | MUST | Thief audit. | Same as E-021. | Not proven against adversarial cop. | PARTIAL | P1 | Add adversarial network tests for false capture. |
| E-023 | App. E p.145 | Scent model is cryptographically locked before game start. | MUST | Shared config. | `config_fingerprint` includes config; Step-0 declaration contains fingerprint. | Config fingerprint smoke. | PARTIAL | P1 | Make pre-match network handshake compare full fingerprint and reject mismatch. |
| E-024 | App. E p.145 | Hardware declaration occurs before game start. | MUST | Step 0. | `Step0Declaration`; `_write_pregame_files`. | Tests passed. | PASS | - | None. |
| E-025 | App. E p.146 | LLM should not decide exact movement; movement remains bounded program logic. | SHOULD | Strategy. | `BrainBase`, `GeminiAgentAdvisor` validates legal moves/fallback. | Tests passed. | PASS | - | None. |
| E-026 | App. E p.146 | Free-text communication uses natural language. | MUST | Hints. | `TemplateHintProvider`; hint parser. | Tests passed. | PASS | - | None. |
| E-027 | App. E p.146 | Do not use direct numeric-coordinate hints/protocol for the verbal game. | MUST | Hints. | Hints use directions, not coordinate pairs. | Tests passed. | PASS | - | None. |
| E-028 | App. E p.146 | Token-bucket rate limiting protects Gmail reports. | MUST | Reporting. | `TokenBucket`, `Gatekeeper`, sender tests. | Tests passed. | PASS | - | None. |
| E-029 | App. E p.146 | DOS/anomaly detector protects reporting resource. | MUST | Reporting. | `AnomalyDetector`, `Gatekeeper`. | Tests passed. | PASS | - | None. |
| E-030 | App. E p.146 | Gmail uses send-only OAuth scope. | MUST | Reporting. | `SCOPES = ["https://www.googleapis.com/auth/gmail.send"]`; tests. | Tests passed. | PASS | - | None. |
| E-031 | App. E p.147 | Minimum league game count is satisfied. | MUST | Submission/league. | No real league results; config `num_games` is wrong. | Static + no artifacts. | FAIL | P1 | Run required real games and fix Appendix F series count. |
| E-032 | App. E p.147 | End-of-match results are reported through Gmail. | MUST | Reporting. | Code exists; `email_mode` default is dry_run; no real send. | Not sent. | PARTIAL | P1 | Complete OAuth and send/draft verification without exposing secrets. |
| E-033 | App. E p.147 | Match report is structured JSON. | MUST | Reporting. | `match_reports.py`; tests. | Tests passed. | PASS | - | None. |
| E-034 | App. E p.147 | Final report is not free text only. | MUST | Reporting. | `send_match_report` enforces JSON attachment/content. | Tests passed. | PASS | - | None. |
| E-035 | App. E p.147 | Both teams agree on outcome and each sends separate report. | MUST | P2P/reporting. | `peer_audit.result_claim` check; `results_agree`. | Local integration only. | PARTIAL | P1 | Run against sibling/opponent repo and verify both emitted reports. |
| E-036 | App. E p.147 | Mutual log audit occurs at match end. | MUST | Integrity. | `exchange_audit`; `audit_records`; integration test. | Local test passed. | PASS | - | None. |
| E-037 | App. E p.147 | Number of played games is declared at match start. | MUST | League. | Step0/report structures exist. | No live league validation. | PARTIAL | P2 | Add explicit declared prior-game count and verification. |
| E-038 | App. E p.148 | Game-count declarations are not false. | MUST | League. | No real game count exchange. | Not testable locally. | NOT TESTED | P2 | Verify during real league run. |
| E-039 | App. E p.148 | No secrets or credentials are pushed. | MUST | Security. | Git history filename scan found no secret additions; tracked file list excludes `.env`. | Scan passed. | PASS | - | Continue final pre-tag scan. |
| E-040 | App. E p.148 | Secret files are in `.gitignore`. | MUST | Security. | `.gitignore` contains `.env`, `credentials.json`, `token.json`, `*.pem`, `*.key`. | Static inspection. | PASS | - | None. |
| E-041 | App. E p.148 | Submission version has documented annotated Git tag. | MUST | Submission. | `git tag -n` produced no output. | Git check. | FAIL | P2 | Create annotated tag only at final submission. |
| E-042 | App. E p.148 | README is an academic report. | MUST | Submission docs. | README includes Dec-POMDP, FastMCP, strategy, screenshots, sibling link, commands. | Static inspection. | PASS | - | None. |
| E-043 | App. E p.148 | Official Word/PDF submission template remains unchanged. | MUST | Outside repo artifact. | No official form in repo. | Not repo-local. | NOT APPLICABLE | - | Handle outside Git repo. |
| E-044 | App. E p.148 | Each student submits the assignment separately. | MUST | Outside repo process. | Not represented in repo. | Not repo-local. | NOT APPLICABLE | - | Handle in course submission system. |
| E-045 | App. E p.148 | Team id is exactly 8 characters without spaces. | MUST | Config/reporting. | `group_id = "uoh-ay26"` is 8 chars, no spaces. | Static inspection. | PASS | - | None. |
| E-046 | App. F additions p.149 | Barrier placed on thief cell counts as capture. | MUST | Thief validation. | `InteractiveMatch.place_barrier`; capture tests. | Tests passed. | PASS | - | None for local; add network barrier test under E-015. |
| E-047 | App. F additions p.149 | Thief trapped with no legal move counts as captured. | MUST | Game logic. | `is_boxed_in`; simulation/interactive tests. | Tests passed. | PASS | - | None. |
| E-048 | App. F additions p.149 | Every terminal scenario uses the scoring table. | MUST | Scoring. | `score_for`; simulation output; scoring tests. | Tests passed. | PASS | - | None. |
| E-049 | App. F additions p.149 | Two GitHub repos cross-link and results include all four repo links. | MUST | Submission/reporting. | README sibling link; `RepoCrossLinks`; remote not verified. | Static only. | PARTIAL | P2 | Verify sibling repo README and generated result JSON with real links. |
| E-050 | App. F additions p.149 | Repo contains README, config, PRD, PLAN, TODO. | MUST | Submission. | Files present in tracked list. | Static inspection. | PASS | - | None. |
| E-051 | App. F additions p.149 | Automatic reports are sent to lecturer address. | MUST | Reporting. | Config recipient is `rmisegal+uoh26finalgame@gmail.com`; default dry_run. | No real send. | PARTIAL | P1 | Complete OAuth and authorized dry-run/send verification. |
| E-052 | App. F additions p.149 | Only one counted game per opponent; warmups do not count. | MUST | League. | No real league artifacts. | Not tested. | NOT TESTED | P2 | Track opponent IDs and counted-game status. |
| E-053 | App. F additions p.150 | Step-0 declaration records commit hash. | MUST | Step 0. | `get_git_commit_hash`; `Step0Declaration.git_commit_hash`. | Tests passed. | PASS | - | None. |
| E-054 | App. F additions p.150 | Final JSON reports total tokens used. | MUST | Reporting/LLM. | `MatchResult.total_tokens_used`; `NetworkMatchRunner` passes `TokenUsage()` with zeros. | Static inspection. | PARTIAL | P2 | Wire real Gemini token accounting into `TokenUsage`. |
| E-055 | App. F additions p.150 | Self-score only software quality, not match outcome. | MUST | Academic grading. | No in-code self-grading tied to game result found. | Static inspection. | PASS | - | None. |

## Secondary Software-Quality Requirements

| ID | Source | Requirement summary | Level | Applicability | Evidence | Verification | Status | Severity | Remediation |
|---|---|---|---|---|---|---|---|---|---|
| Q-001 | Secondary PDF sec. 2 p.7 | README exists and includes install/usage/config/screenshots/credits. | SHOULD | Repo docs. | README present and extensive. | Static inspection. | PASS | - | None. |
| Q-002 | Secondary PDF sec. 2 p.7 | `docs/PRD.md`, `docs/PLAN.md`, `docs/TODO.md`, per-mechanism PRDs exist. | SHOULD | Repo docs. | Files present. | Static inspection. | PASS | - | None. |
| Q-003 | Secondary PDF sec. 3 p.10 | Python files should generally be <=150 code lines. | SHOULD | Code quality. | 12 files exceed 150; largest `network_match.py` has 305. | Line-count scan. | FAIL | P3 | Split large modules after mandatory gaps are fixed. |
| Q-004 | Secondary PDF sec. 7 p.17 | `ruff check` must pass with zero violations. | SHOULD | Quality gate. | `uv run ruff check .` | Exit 0. | PASS | - | None. |
| Q-005 | Secondary PDF quality gate | Formatting check should pass. | SHOULD | Quality gate. | `uv run ruff format --check .` | Exit 1; 42 files would reformat. | FAIL | P2 | Run formatter after audit approval. |
| Q-006 | Secondary PDF sec. 6 p.15 | Test coverage target is at least 85%. | SHOULD | Quality gate. | `uv run pytest --cov` | 85.22%. | PASS | - | Keep above threshold when fixing. |
| Q-007 | Secondary PDF sec. 8 p.19 | Use uv and committed `uv.lock`. | SHOULD | Packaging. | `pyproject.toml`, `uv.lock`; `uv sync` passed with cache access. | Command passed. | PASS | - | None. |
| Q-008 | Secondary PDF sec. 7 p.18 | No secrets in source; `.env-example` exists. | SHOULD | Security. | `.env-example`, `.gitignore`, history scan. | Scan passed; local ignored `.env` exists. | PASS | - | Do final ignored-file review before submission. |
| Q-009 | Audit request | Type checking, if available/configured. | SHOULD | Quality gate. | `uv run mypy src\police_thief` | Exit 1, 18 errors. | FAIL | P3 | Configure mypy or fix/ignore typed boundaries intentionally. |
| Q-010 | Audit request | Dependency vulnerability scan where tooling is available. | SHOULD | Security. | No vulnerability tool configured in repo. | Not run. | NOT TESTED | P3 | Add `pip-audit`/`uv audit` equivalent if approved. |

## P2P Isolation Verdict

PARTIAL. The thief can run as its own FastMCP process and does not import the sibling police repository. However, the repository still contains a local `--role cop/police` fallback for smoke testing, and the live cross-machine tunnel/opponent run was not executed. The network match loop also has protocol-specific gaps around barriers, capture-claim validation, config fingerprint exchange, watchdog integration, and real reporting.

## State Transition Table

| Current state | Event | Guard | Action | Next state | Failure behavior |
|---|---|---|---|---|---|
| `WAITING_FOR_OPPONENT` | Own turn starts | Match not terminal | Ask strategy to compute move | `COMPUTING_MOVE` | Illegal transition raises |
| `COMPUTING_MOVE` | Move selected | Strategy returns `Move` | Commit selected move | `COMMITTING` | Deadline/client/verification failure goes to `TECHNICAL_LOSS` in `Orchestrator` |
| `COMMITTING` | Commitment sent | Opponent call succeeds | Await reveal/audit phase | `AWAITING_REVEAL` | Network error -> `TECHNICAL_LOSS` |
| `AWAITING_REVEAL` | Reveal phase entered | No explicit opponent reveal in `Orchestrator` path | Self-verify local commitment | `VERIFYING` | Self-verification failure -> `TECHNICAL_LOSS` |
| `VERIFYING` | Verification OK | Commitment recomputes | Log entry | `WAITING_FOR_OPPONENT` | Failure -> `TECHNICAL_LOSS` |
| `TECHNICAL_LOSS` | Any event | Terminal | None | Terminal | No transitions allowed |

`NetworkMatchRunner` uses a different implicit loop: negotiate terms, alternate turn messages by step parity, reject wrong step/sender, exchange final audit records, then write reports. It is not modeled through `MatchStateMachine`.
