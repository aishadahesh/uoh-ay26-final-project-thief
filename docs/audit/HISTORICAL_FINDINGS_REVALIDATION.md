# Historical Findings Revalidation

Old audit files were untracked historical artifacts from commit `bb217d10f1211050c2cafe7b06863a73146906d1`. Current baseline was `62fe9fa3cf9b6a29a3a2cad523ef4faff91b8e44`.

| Old finding ID | Old severity | Old description | Old affected files | Current status | Current evidence | Still requires action | Updated severity | Updated remediation |
|---|---|---|---|---|---|---|---|---|
| P1-001 | P1 | Appendix F `num_games` fixed 6 but repo enforced 1 | `config/game.json`, `game_config.py`, tests | STILL PRESENT at baseline; fixed in this pass | baseline config loaded `num_games=1`; PDF Appendix F says 6 | No after fix | P1 | Config and loader now enforce 6; tests updated |
| P1-002 | P1 | two runtime paths | `orchestrator.py`, `network_match.py`, `state_machine.py` | PARTIALLY FIXED | live runner still exists, but explicit network state machine added and wired | Yes | P1 | Make all GUI/live paths use the new state history and remove ambiguity later |
| P1-003 | P1 | watchdog missing from real loop | `network_match.py`, `watchdog.py` | STILL PRESENT | deadlines declared, but watchdog heartbeat not fully integrated into runner | Yes | P1 | Add live watchdog heartbeat and structured technical loss |
| P1-004 | P1 | full config SHA-256 not exchanged | `network_match.py`, `network_protocol.py` | CHANGED | handshake terms now include `config_sha256` and schema | No for local runner | P1 | Verify sibling police peer implements same terms |
| P1-005 | P1 | network barrier support incomplete | board/protocol/runtime/replay | PARTIALLY FIXED | duplicate barrier rejected; payload carries barrier field; full network barrier replay remains incomplete | Yes | P1 | Complete barrier semantics in commit/reveal/replay |
| P1-006 | P1 | capture claims not reconstructable | `network_match.py`, `capture.py` | STILL PRESENT | live thief still cannot reconstruct police position until audit reveal | Yes | P1 | Share reveal data through one rule engine before accepting capture |
| P1-007 | P1 | no real cross-machine/tunnel match | operations | REQUIRES REVALIDATION | no two-machine evidence was produced | Yes | P1 | Run manual non-counted smoke against real police repo |
| P1-008 | P1 | Gmail OAuth/send not verified | Gmail services/runbook | PARTIALLY FIXED | doctor checks dry-run mode; runbook added; no OAuth/send performed by design | Yes | P1 | Manual OAuth/draft/send validation only when authorized |
| P2-001 | P2 | final tag absent | Git | NO LONGER APPLICABLE | current request forbids tag | No for smoke prep | P2 | Do not tag until official submission |
| P2-002 | P2 | Ruff format fails | repo-wide | STILL PRESENT at baseline | 42 files would reformat | Yes | P2 | Run `ruff format .` and verify |
| P2-003 | P2 | sibling repo reciprocal link unverified | README/config | REQUIRES REVALIDATION | police repo not modified or inspected in this pass | Yes | P2 | Verify manually with police repo authorization |
| P2-004 | P2 | league game-count tracking missing | `league.py`, reports, protocol | PARTIALLY FIXED | handshake serializes counted/smoke/game index/previous counted games | Yes | P2 | Persist complete league record across real opponents |
| P2-005 | P2 | token accounting written as zero | `step0.py`, `match_reports.py`, `network_match.py` | CHANGED | result now includes `token_usage_available` flag | Yes | P2 | Wire Gemini provider metadata when real LLM is used |
| P2-006 | P2 | missing adversarial tests | tests | PARTIALLY FIXED | protocol/state/doctor/config/barrier tests added | Yes | P2 | Add full barrier/capture/watchdog two-process tests |
| P3-001 | P3 | oversized files | GUI/runtime modules | STILL PRESENT | no file split done | Yes | P3 | Refactor only after behavior stabilizes |
| P3-002 | P3 | mypy errors | 11 files | STILL PRESENT | baseline mypy had 18 errors | Yes | P3 | Fix remaining typing errors without global ignores |
| P3-003 | P3 | dependency scan absent | operations | REQUIRES REVALIDATION | no networked dependency scan performed | Yes | P3 | Run authorized audit tool if needed |
| P3-004 | P3 | coverage gaps | GUI/network/reporting | CHANGED | new tests added; final coverage pending | Maybe | P3 | Keep coverage above 85% |
| P3-005 | P3 | git safe-directory warnings | environment | STILL PRESENT | Git warns about global ignore permission | Yes | P3 | User environment permission issue, not repo code |

