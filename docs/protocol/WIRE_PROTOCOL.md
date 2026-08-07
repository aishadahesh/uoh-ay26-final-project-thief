# Wire Protocol

Protocol name: `police-thief-mcp`

Protocol version: `3.0.0`

Each peer exposes exactly four FastMCP tools:

- `negotiate(message)`
- `receive_turn(message)`
- `submit_audit(payload)`
- `receive_control(message)`

## Prematch negotiation

`negotiate` receives `{terms, nonce, signature, identity}`. The signature is
SHA-256 over canonical JSON terms plus the nonce. The runtime terms object is
kept character-for-character compatible with the lecturer reference:

```json
{
  "board_size": 7,
  "smell_grid_size": 5,
  "decay_per_step": 0.1,
  "emit_intensity": 0.9,
  "min_center_intensity": 0.5,
  "max_steps": 35,
  "barriers_max": 14,
  "setting": "New York",
  "hint_max_words": 15,
  "axis_origin_corner": "top-left",
  "axis_start_index": 0,
  "thief_start": [3, 3],
  "cop_start": [0, 0],
  "num_games": 6
}
```

Do not add local fields such as `series_id`, `counted`, `config_sha256`, or
`capabilities` to the signed terms: equality is exact, so extensions make a
reference-compatible opponent reject negotiation. Team identity and repository
links belong in `identity`, not in public game terms.

## Turn message

`receive_turn` gets the exact public shape below. Optional fields are present
with `null` when unused:

```json
{
  "step": 1,
  "sender": "thief",
  "hint": "bounded public hint",
  "smell_grid": {},
  "commit": "64-character SHA-256 digest",
  "timestamp": "2026-08-03T12:00:00+00:00",
  "barrier_placed": null,
  "capture_claim": null,
  "claim_response": null,
  "win_claim": null
}
```

Moves and private state stay sealed until audit. Cop barrier coordinates are
public immediately. Step numbers are local to each peer and run from 1 through
`max_steps`.

## Audit and control

`submit_audit` receives `{sender, records, result_claim}`. Records include one
sealed Step-0 hardware/model declaration and every local turn nonce reveal.
Both peers independently verify the commitments and outcome before setting
`mutual_sign_off` to true.

`receive_control` carries `enable`, `status`, `restart`, or `quit`. A six-game
series renegotiates and resets state before every sub-game while keeping one
long-lived MCP server per computer.
