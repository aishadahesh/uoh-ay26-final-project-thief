# Cross-Machine Readiness Checklist

| Item | Status | Evidence |
|---|---|---|
| dependencies install | PASS | `uv sync` succeeded after uv cache access |
| package imports | PASS | package version `1.00` |
| CLI works | PASS | help and `doctor` run |
| local simulation | PASS | survival, 35 turns |
| full test suite | PASS | final `481 passed, 1 skipped` |
| coverage above 85% | PASS | final 85.92% |
| Ruff lint | PASS | baseline passed |
| Ruff format | PASS | final format check passed |
| mypy | FAIL | 18 baseline errors |
| mandatory `num_games` | PASS | fixed to 6 |
| config fingerprint | PASS | doctor prints SHA-256 |
| strict handshake | PASS | runner terms and tests include config/match/series/counting metadata |
| role conflict rejection | PASS | protocol tests |
| stale/future/duplicate handling | PASS | message guard tests |
| barriers over network | FAIL | only duplicate barrier and payload field fixed |
| capture reconstruction | FAIL | not fully implemented |
| watchdog in live runtime | FAIL | state machine exists; heartbeat not fully wired |
| non-counted smoke mode | PASS | CLI requires `--non-counted` |
| doctor command | PASS | offline JSON output succeeds |
| Gmail dry-run | PASS | doctor validates dry-run mode |
| Gmail OAuth/send | MANUAL TEST REQUIRED | intentionally not performed |
| real police peer compatibility | POLICE-SIDE CHANGE REQUIRED | see compatibility doc |
| local two-process OS smoke | MANUAL TEST REQUIRED | not run with two OS processes in this pass |
| cross-machine smoke | MANUAL TEST REQUIRED | requires separate police machine/repo/tunnel |
| official counted game | MANUAL TEST REQUIRED | requires real two-machine evidence |

## Readiness Declarations

- READY FOR LOCAL TWO-PROCESS TEST: NO
- READY FOR CROSS-MACHINE SMOKE TEST: NO
- READY FOR OFFICIAL COUNTED GAME: NO
