# Strategy Log Analysis and Anti-Loop Upgrade

## Evidence from the supplied games

| Log | Role | Moves | Unique cells | Reversals | ABAB loops |
|---|---:|---:|---:|---:|---:|
| `log_G001_g01.json` | Police | 16 | 14 | 3 | 2 |
| `log_G001_g01.json` | Thief | 17 | 7 | 9 | 7 |
| `log_G001_g02.json` | Police | 34 | 7 | 26 | 24 |
| `log_G001_g02.json` | Thief | 35 | 7 | 19 | 12 |

Game 2's police repeatedly switches between `(0,5)` and `(0,6)`, while
the thief switches between `(6,5)` and `(6,6)` or stays. The original one-step
Manhattan policy had no path cost, continuation value, or movement memory;
Gemini also lacked enough board/history context to recognize the oscillation.

## Upgrade

`TacticalPlanner` scores every board-validated move using barrier-aware BFS path
distance, five weighted belief candidates, two-ply continuation value, mobility,
dead-end risk, revisits, repeated actions, reversals, STAY, and loop penalties.
Police values sustained pursuit; thief values capture margin, future escape
distance, open space, and multiple exits. ABAB positions/actions, repeated cells,
and consecutive STAY are detected. If alternatives exist, moves that continue a
loop are removed from Gemini's allowed set, and the best remaining score becomes
the objective-aligned fallback.

The belief update now predicts one legal hidden-opponent move before applying
new scent evidence, preventing historical scent from freezing a stale peak.
Gemini receives blocked cells, belief candidates, legal destinations and scores,
recent history, loop warnings, and a strict JSON contract. Invalid output gets
one corrective prompt and is validated again against live board state.

## Legality

`ProgressDoc.md`, `docs/tasks.md`, and `ref/police_thief_p2p.pdf` were reviewed.
The opponent's true position is never supplied to the live policy. It receives
only its own position and scent-derived belief. Movement remains one orthogonal
cell or STAY and must pass `Board.legal_moves` plus `Board.apply_move`; no
diagonal, blocked, off-board, or invented action can execute. The cop-role
barrier policy uses legal current/adjacent cells and spends only on a real
chokepoint.

## Controlled replay

Using the recorded `(0,0)` police and `(3,3)` thief starts on the same open 7x7
board, with policies updated only from scent-derived beliefs, the improved run
produced zero reversals and zero ABAB loops for both roles. Police used 10 moves
across 11 unique cells, thief used 11 moves across 8 unique cells, and capture
occurred at `(5,5)`. True coordinates were used only by the offline observer to
check capture, never as policy input.
