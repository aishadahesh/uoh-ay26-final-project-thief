# Cross-Machine Implementation Plan

| Priority | Requirement reference | Current evidence | Affected files | Proposed change | Protocol impact | Compatibility impact | Tests | Rollback | Completion criteria | Risk |
|---|---|---|---|---|---|---|---|---|---|---|
| P1 | Appendix F Table 18 page 154; Appendix E rules 31, 37 | `num_games=1` loaded | config, loader, tests | enforce fixed 6; separate smoke/counting metadata | handshake declares official 6 separately from smoke | police peer must use 6 | config and terms tests | revert config/constant/tests | lowered value rejected | medium |
| P1 | Appendix E config identity | runner compared limited terms | protocol, runner | include config SHA, schema, match/series IDs | strict pre-match rejection | police peer must mirror fields | protocol + integration tests | disable strict identity helper | mismatch fails before turn 1 | medium |
| P1 | Appendix E distributed runtime | implicit loop | runner, new state machine | add explicit transition model and state history | network events become structural | no wire break | state-machine tests | remove runner hooks | illegal/duplicate transitions rejected | medium |
| P1 | Appendix E barrier/capture audit | partial live verification | board/protocol/runtime | reject duplicate barriers; add barrier payload field | barrier field canonicalized | police peer should emit same field | board/protocol tests | remove duplicate check only if incompatible | duplicate barrier rejected | low |
| P2 | Appendix E/Gmail rules | no readiness CLI | main, doctor | add non-destructive doctor | no wire change | none | CLI tests | remove subcommand | doctor exits 0 when local smoke prerequisites pass | low |
| P2 | Appendix E token reporting | zero without availability | step0/reports | add availability flag | result schema adds field | police parser should tolerate field | report tests | omit new field if parser rejects | zero is labeled unavailable | low |
| P2 | Operational smoke mode | no explicit non-counted peer flag | main, runbooks | add `--smoke-test --non-counted` | future handshakes declare non-counted | police peer must agree | CLI parse tests | remove flags | smoke cannot start without non-counted | low |

Deferred items requiring real police peer or manual operations: full barrier/capture reconstruction over a real network, watchdog heartbeat in the live runner, Gmail OAuth/draft/send, tunnel setup, and official counted-game evidence.

