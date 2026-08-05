# Police–Thief P2P · Thief Agent

> An evasive autonomous agent that survives through uncertainty-aware movement, future-mobility analysis, validated Gemini decisions, and cryptographically auditable peer-to-peer play.

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/badge/package_manager-uv-DE5FE9)](https://docs.astral.sh/uv/)
[![FastMCP](https://img.shields.io/badge/network-FastMCP-2F80ED)](https://gofastmcp.com/)
[![Ruff](https://img.shields.io/badge/style-Ruff-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)

This is the **thief-side repository** for the University of Haifa **Orchestration of AI Agents** final project (AY26). Its companion is the [cop repository](https://github.com/aishadahesh/uoh-ay26-final-project-cop).

The thief does not share memory with the cop, does not read the cop’s coordinates, and does not trust a central referee. It maintains its own board, belief map, private nonces, network state, audit evidence, and final report. The two peers agree only through signed configuration and a validated wire protocol.

## Why this project is interesting

Survival is not simply “move away.” The thief must answer harder questions:

- Which legal action increases distance without entering a dead end?
- Is an edge cell safer now but strategically worse next turn?
- Can a Gemini response be useful without letting an LLM violate board rules?
- How can two opponents prove a match result without revealing hidden actions early?
- How should a completed result survive network, OAuth, or reporting failures?

This repository combines evasive planning, constrained model output, decentralized orchestration, cryptographic commitments, and evidence-first reporting.

## Contents

- [System at a glance](#system-at-a-glance)
- [Thief intelligence](#thief-intelligence)
- [Validated Gemini decision pipeline](#validated-gemini-decision-pipeline)
- [Trust and protocol design](#trust-and-protocol-design)
- [Installation](#installation)
- [Run modes](#run-modes)
- [Two-computer match guide](#two-computer-match-guide)
- [Configuration](#configuration)
- [Results and automatic email](#results-and-automatic-email)
- [Testing and quality](#testing-and-quality)
- [Project map](#project-map)
- [Troubleshooting](#troubleshooting)
- [Academic design notes](#academic-design-notes)

## System at a glance

```text
┌──────────────────────── THIEF PROCESS ──────────────────────┐
│ local board + cop belief + escape policy + private nonce    │
│                                                             │
│ observe scent → estimate threat → enumerate legal actions   │
│                                    ↓                        │
│                         score distance + future exits        │
│                                    ↓                        │
│                 Gemini choose → validate → repair/retry      │
│                                    ↓                        │
│                 final live validation → sealed turn         │
└─────────────────────────── FastMCP P2P ─────────────────────┘
              ↓ final mutual audit and sign-off
       result JSON → optional Gmail gatekeeper → recipient
```

The code is separated by responsibility:

| Layer | Responsibility |
|---|---|
| `domain/` | Board physics, scent, belief, escape scoring, capture, replay |
| `services/` | Gemini boundary, MCP protocol, commit–reveal, reporting |
| `gui/` | Play modes, network setup, live board, replay viewer |
| `shared/` | Configuration loading, constants, validation, versioning |

## Thief intelligence

### 1. Partial-observation threat model

The thief never receives the cop’s actual cell. `BeliefMap` maintains probability across open board cells and updates from scent evidence. The most likely cell, `arg_max()`, becomes the current threat estimate.

This distinction matters: the policy reacts to evidence, not hidden global truth.

### 2. Legal actions first

Every turn begins with `Board.legal_moves(current_position)`. That method delegates to the same movement engine used during execution, so prompt construction and actual board physics share one source of truth.

Legal actions can include north, south, east, west, and stay. Off-board directions and cells occupied by barriers are omitted.

### 3. Escape score: distance plus future mobility

The original baseline maximized only Manhattan distance from the believed cop. That is safe locally but can create edge oscillations or move into a cell with too few future exits.

The improved thief evaluates every legal candidate with a lexicographic safety score:

```text
(distance from believed cop, number of future exits, moved instead of stayed)
```

This preserves distance as the primary objective while using future mobility to break ties. The policy therefore prefers:

- greater separation from the threat estimate;
- open cells with multiple escape routes;
- movement over unnecessary waiting;
- recovery routes when barriers restrict the board;
- avoiding corners and dead ends when an equally distant alternative exists.

### 4. Different game states

The same scoring logic adapts naturally:

| Situation | Preferred behavior |
|---|---|
| Cop belief is nearby | Maximize immediate separation |
| Two moves are equally distant | Choose the cell with more future exits |
| A barrier blocks the expected route | Re-enumerate legal actions from the updated board |
| The thief reaches an edge | Avoid corner commitment when a mobile alternative exists |
| Only `STAY` remains | Remain legal and allow boxed-in resolution to proceed |
| Gemini is unavailable | Use the validated deterministic escape choice |

## Validated Gemini decision pipeline

Gemini is the primary tactical selector in agent-driven network play, but it operates inside a strict action boundary.

### Prompt contract

Gemini receives:

- the thief role and turn horizon;
- the thief’s own position;
- the believed cop position, explicitly labeled as an estimate;
- every allowed action and its exact destination cell;
- per-action safety information `(distance, exits, moved)`;
- explicit restrictions against omitted directions, diagonals, coordinates, and barrier actions;
- a strict JSON response schema.

Expected response:

```json
{"action":"EAST","reason":"Keeps distance while preserving three exits."}
```

### Parsing and validation

The parser supports strict JSON and remains backward-compatible with the earlier `MOVE|reason` format. Exact names, move codes, and unambiguous aliases such as `RIGHT → EAST` are normalized—but only if the resulting move exists in the current legal set.

Validation happens twice:

1. **Response validation:** reject missing, malformed, invented, or unavailable actions.
2. **Live-state validation:** immediately before execution, compare the selected move with a fresh `board.legal_moves()` result.

No Gemini-generated action can bypass `Board.apply_move`.

### Repair before fallback

An invalid response no longer activates fallback immediately. The advisor sends one corrective prompt containing:

- the rejection reason;
- a clipped form of the previous response;
- the current exact allowed actions;
- an instruction to copy one legal action name and return JSON only.

Fallback is used only when correction fails or the provider is genuinely unavailable.

### Decision logging

Network output now explains:

- which action Gemini selected;
- whether it passed validation;
- how many attempts were needed;
- why a response was rejected;
- why fallback was activated;
- which fallback move was selected.

This turns “Gemini returned an invalid move” into actionable evidence.

Configure the advisor in `.env`:

```env
GEMINI_API_KEY=your_google_ai_studio_key
GEMINI_MODEL=gemini-3.1-flash-lite
GEMINI_TIMEOUT_SECONDS=8
GEMINI_ENABLE_MODEL_FALLBACKS=false
```

Human-vs-human mode remains fully offline.

## Trust and protocol design

### Independent peers

The thief and cop each run a FastMCP server and client. Neither side controls the other’s process. Match progression uses four protocol operations:

1. `negotiate` — bind peer identity to signed game terms;
2. `receive_turn` — exchange sealed movement and public declarations;
3. `submit_audit` — reveal records and verify commitments;
4. `receive_control` — coordinate readiness and lifecycle state.

### Commit–reveal

Every private turn is committed before final reveal:

```text
commit = SHA256(state || move || intent || nonce)
```

The nonce prevents the opponent from guessing the sealed content and prevents the sender from changing its story later. During final audit, both peers recompute all commitments and reject mismatches.

### Public barriers, private movement

The cop’s barrier placement changes shared board geometry and is declared immediately. The thief applies it locally through the board engine before its next decision. Movement details remain sealed until audit.

### Mutual result agreement

A result is not trusted merely because one peer writes it. The audit must validate records, outcome claims must agree, and both peers independently derive scores and log hashes.

## Installation

Requirements:

- Python 3.11 or newer;
- [`uv`](https://docs.astral.sh/uv/);
- Tk support for graphical modes;
- a Gemini API key for agent modes;
- Gmail OAuth files only for automatic reporting.

```bash
git clone https://github.com/aishadahesh/uoh-ay26-final-project-thief.git
cd uoh-ay26-final-project-thief
uv sync
```

Install Gmail support when automatic email is needed:

```bash
uv sync --extra email
```

Create local environment settings:

```powershell
Copy-Item .env-example .env
```

Never commit `.env`, `credentials.json`, or `token.json`.

## Run modes

### Interactive command center

```bash
uv run python -m police_thief play
```

Choose human-vs-human, human-vs-agent, local agent-vs-agent, or a real two-computer MCP match.

### Standalone thief visualization

```bash
uv run python -m police_thief demo --role thief
```

Displays the local-truth board and evolving belief mechanics without networking.

### Local simulation

```bash
uv run python -m police_thief simulate
```

Exercises movement, scent, beliefs, capture, and scoring in one process.

### Readiness doctor

```bash
uv run python -m police_thief doctor --role thief --offline
```

For network-aware checks:

```bash
uv run python -m police_thief doctor --role thief --check-opponent
```

A machine-readable report can be saved with `--json-output path/to/report.json`.

### Real peer

```bash
uv run python -m police_thief peer --role thief
```

Starts this repository in its natural role for the first sub-game, negotiates the match, drives the Gemini/validation pipeline, performs final audit, and saves results.

### Non-counted smoke peer

```bash
uv run python -m police_thief peer --role thief --smoke-test --non-counted
```

The explicit `--non-counted` requirement prevents deterministic connectivity checks from being mistaken for league evidence.

### Replay an audited log

```bash
uv run python -m police_thief replay --log results/network/log_G001_g01.json
```

The viewer recalculates commitments and flags modified evidence.

## Two-computer match guide

### Prepare both computers

1. Run `uv sync` in each repository.
2. Configure `.env` with Gemini credentials.
3. Confirm both sides have byte-identical `config/game.json` files.
4. Fill team identities, repositories, shared secret, game ID, output, and email defaults in `config/network_match.json`.
5. Set the opponent URL in `config/thief/game.toml`.
6. Start the project's **Cloudflare Tunnel (cloudflared)** for the local thief MCP port.

### Cloudflare Tunnel

This project uses **Cloudflare Tunnel (`cloudflared`)** to expose the local FastMCP server securely over HTTPS without opening an inbound router port. Start the thief application first, then open another terminal and publish port `8802`:

```bash
cloudflared tunnel --url http://localhost:8802
```

For a quick tunnel, `cloudflared` prints a temporary `https://<random>.trycloudflare.com` address. The MCP endpoint shared with the cop must append `/mcp`:

```text
https://<random>.trycloudflare.com/mcp
```

Put that full address in the cop peer's **Opponent public URL**. Put the cop's corresponding Cloudflare URL in this thief repository's opponent configuration. Keep the `cloudflared` process running throughout the match; restarting a quick tunnel generates a new URL that must be updated on the other peer.

A named Cloudflare Tunnel and custom hostname may also be used when a stable URL is required. In either mode, Cloudflare handles the public HTTPS connection while FastMCP continues listening locally on `localhost:8802`.

### Launch

```bash
# Thief computer
uv run python -m police_thief peer --role thief

# Cop computer
uv run python -m police_thief peer --role police
```

Each side may start first and wait at negotiation.

### Shared versus private values

The following must agree:

- shared configuration fingerprint;
- game/series identity;
- scoring and maximum turns;
- shared match secret;
- team and repository declarations.

These remain private:

- Gemini keys;
- OAuth credentials and tokens;
- private nonces;
- local process state.

## Configuration

| File | Visibility | Purpose |
|---|---|---|
| `config/game.json` | Shared | Board, scent, scoring, league, timing, protocol rules |
| `config/thief/game.toml` | Private | Thief port, opponent URL, timeouts, role strategy |
| `config/network_match.json` | Local launcher defaults | Match identity, teams, repositories, output, email switch |
| `config/game.toml` | Submission-facing private config | Required role-specific submission settings |
| `.env` | Secret/local | Gemini and other provider settings |
| `credentials.json` | Secret/local | Google OAuth client configuration |
| `token.json` | Secret/local | Reusable Gmail authorization token |

The tracked network defaults currently control whether automatic email begins enabled. The GUI can override that choice for the current launch.

## Results and automatic email

A verified match or series produces artifacts such as:

```text
results/network/
├── declaration_G001.json
├── config_G001_g01.json
├── log_G001_g01.json
├── result_G001_g01.json
└── result_G001.json
```

The result is constructed from audited records, scores, identities, repository links, and the replay-log hash.

To enable automatic Gmail reporting:

1. Run `uv sync --extra email`.
2. Place `credentials.json` in the project root.
3. Complete OAuth browser consent once to create `token.json`.
4. Enable `email.automatic` in `config/network_match.json` or check the option in the network setup GUI.
5. Verify the recipient before starting.

Email is sent only after mutual match completion. The sender uses the minimal `gmail.send` scope and passes through quota, rate-limit, anomaly, and retry controls. The final JSON is attached directly.

## Testing and quality

```bash
uv run pytest --cov
uv run ruff check .
uv run ruff format --check .
```

Focused strategy coverage includes:

- legal-action enumeration;
- threat-distance improvement;
- equal-distance mobility tie-breaking;
- malformed and unavailable Gemini actions;
- corrective regeneration before fallback;
- alias and JSON parsing;
- validation of the fallback itself;
- real two-peer integration and audit behavior.

Coverage is enforced at **85% minimum** in `pyproject.toml`.

GUI tests require a working Tcl/Tk installation. External Gmail sends and public tunnel sessions remain manual integration boundaries.

## Project map

```text
src/police_thief/
├── domain/
│   ├── board.py              # legal movement and barrier state
│   ├── belief.py             # believed cop distribution
│   ├── scent.py              # evidence emission and decay
│   ├── heuristics.py         # distance and mobility escape scores
│   ├── capture.py            # capture and boxed-in rules
│   └── strategy/             # role-aware deterministic policy
├── services/
│   ├── gemini_agent.py       # prompt, parsing, repair, strict validation
│   ├── network_match.py      # live decision and audit orchestration
│   ├── network_protocol.py   # signed wire schema
│   ├── commit_reveal.py      # turn sealing and verification
│   ├── mcp_server.py         # inbound FastMCP tools
│   ├── mcp_client.py         # opponent calls
│   └── network_reporting.py  # audited Gmail delivery
├── gui/                      # mode selection, board, network setup, replay
├── shared/                   # validated configuration
└── main.py                   # CLI entry point
```

Detailed design decisions live in `docs/PRD_*.md`; the chronological engineering record is `ProgressDoc.md`.

## Troubleshooting

### Gemini repeatedly returns invalid actions

Read the new rejection logs. They show the raw action category, allowed actions, correction count, and fallback choice. Confirm the running code includes the strict JSON prompt and that both peers use the expected board state.

### Gemini is unavailable

Check `GEMINI_API_KEY`, model name, timeout, and network access. The deterministic strategy remains safe and legal when the provider fails.

### Opponent is unreachable

Verify `cloudflared`, local port `8802`, the public HTTPS URL, and the required `/mcp` suffix. Remember that a quick-tunnel URL changes after restart. Use `doctor --check-opponent` before a counted match.

### Negotiation fails

Compare `config/game.json` byte-for-byte and verify the secret, team names, game ID, repository URLs, and opponent identity expectations.

### Tkinter cannot find `init.tcl`

Install or repair a Python distribution containing Tcl/Tk. CLI simulations and non-GUI tests remain available.

### Gmail is not sent

First check whether automatic email was enabled. Then verify the email extra, OAuth files, recipient, token validity, and emitted reporting logs.

### Result JSON exists after a reporting failure

That is expected: gameplay evidence is created before email delivery. Preserve the result and diagnose the reporting boundary separately.

## Academic design notes

The game is represented as a decentralized partially observable Markov decision process:

```text
⟨agents, states, actions, transition, rewards, observations, observation model, γ⟩
```

The true state includes both positions and barrier layout, yet neither peer observes the full state. Scent provides truthful but decaying evidence; verbal hints may be deceptive; belief maps summarize uncertainty; signed shared configuration keeps physics consistent across machines.

The selected policy is deliberately interpretable. Distance explains immediate safety, mobility explains route quality, and every model-assisted choice is logged and validated. This provides stronger auditability than an opaque end-to-end policy while still allowing Gemini to contribute contextual tactical reasoning.

## Team and companion repository

Built by **Aisha Abu Dahesh** and **Yousef Asadi** for the University of Haifa Orchestration of AI Agents course.

Companion cop implementation: [uoh-ay26-final-project-cop](https://github.com/aishadahesh/uoh-ay26-final-project-cop).
