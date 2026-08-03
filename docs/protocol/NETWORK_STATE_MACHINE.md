# Network State Machine

Authoritative runtime model: `police_thief.services.network_state_machine.NetworkRuntimeStateMachine`.

| Current state | Event | Guard | Action | Next state | Failure behavior |
|---|---|---|---|---|---|
| INITIALIZING | START | process created | initialize local runtime | WAITING_FOR_OPPONENT | illegal event raises `NetworkStateError` |
| WAITING_FOR_OPPONENT | OPPONENT_CONNECTED | transport available | begin negotiation | NEGOTIATING_CONFIG | timeout/disconnect -> TECHNICAL_LOSS |
| NEGOTIATING_CONFIG | TERMS_VERIFIED | signed terms match | accept config and role identity | EXCHANGING_STEP0 | stale/future/malformed -> PROTOCOL_FAILURE |
| EXCHANGING_STEP0 | STEP0_EXCHANGED | declarations present | persist pregame artifacts | READY | malformed -> PROTOCOL_FAILURE |
| READY | LOCAL_TURN | turn is local | start strategy deadline | COMPUTING_MOVE | illegal duplicate transition rejected |
| COMPUTING_MOVE | MOVE_COMPUTED | legal move selected | seal payload | COMMITTING | local exception -> TECHNICAL_LOSS |
| COMMITTING | COMMIT_SENT | SHA-256 commitment emitted | wait for turn exchange | EXCHANGING_TURN_DATA | retry stays bounded |
| READY | REMOTE_TURN | turn belongs to opponent | wait for remote commitment | WAITING_FOR_REMOTE_COMMIT | timeout/disconnect -> TECHNICAL_LOSS |
| WAITING_FOR_REMOTE_COMMIT | COMMIT_RECEIVED | match/series/role/turn valid | record commitment | EXCHANGING_TURN_DATA | stale/future/wrong role -> PROTOCOL_FAILURE |
| EXCHANGING_TURN_DATA | TURN_DATA_EXCHANGED | reveal data available | verify payload | VERIFYING_TURN | malformed -> PROTOCOL_FAILURE |
| VERIFYING_TURN | TURN_VERIFIED | commitment and rules valid | mark turn ready to apply | APPLYING_TURN | tamper -> PROTOCOL_FAILURE |
| APPLYING_TURN | TURN_APPLIED | turn not previously applied | mutate local board state once | READY | duplicate application rejected |
| READY | MATCH_FINISHED | terminal gameplay condition | begin mutual audit | FINAL_AUDIT | mismatch -> PROTOCOL_FAILURE |
| FINAL_AUDIT | AUDIT_VERIFIED | both logs verify | write report | REPORTING | failed audit -> PROTOCOL_FAILURE |
| REPORTING | REPORT_WRITTEN | JSON persisted | stop runtime | COMPLETED | reporting failure is structured separately from gameplay |

Terminal states `COMPLETED`, `TECHNICAL_LOSS`, and `PROTOCOL_FAILURE` cannot transition.

