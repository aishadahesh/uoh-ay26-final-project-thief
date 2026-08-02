# Police-Thief P2P — Distributed Cops-and-Robbers over a Peer-to-Peer Network

Final project for the University of Haifa "Orchestration of AI Agents" course (AY26). Two autonomous agents — a **cop** and a **thief** — play a partial-information pursuit game over a decentralized peer-to-peer network, with no central server, no shared memory between sides, and a cryptographic commit-reveal protocol standing in for a referee.

> **This is the THIEF repo.** Sibling (cop) repo: https://github.com/aishadahesh/uoh-ay26-final-project-cop

> **Status: practical overview**, followed by the required Academic Report (see [Academic Report](#academic-report) below). The mandatory README screenshots are now captured; remaining submission-time actions are listed near the end.

## Role support in this repository

This repository is submitted as the **thief** side only. The sibling repo linked above is the real **cop** submission.

- `uv run python -m police_thief serve` starts the **thief** peer by default (`--role` defaults to `thief`).
- `--role cop` / `--role police` still works only for the PDF's local two-terminal smoke command. It uses built-in loopback defaults, prints a one-line warning every time, and is not backed by a tracked `config/cop/` directory.
- Everywhere else in this codebase that models "cop" (the `AgentRole.COP` enum member and cop-branch logic in shared modules like scoring/board/replay/commit-reveal) is required, not incidental: this thief agent has to validate the cop's moves, verify its commit-reveal proofs, score matches against it, and replay its logs. None of that makes this repo a cop submission — it makes the thief submission correct.

## Academic Report

<a id="academic-report"></a>

### The Dec-POMDP model

The game is modeled as a `Dec-POMDP` `⟨n, S, {Aᵢ}, P, R, {Ωᵢ}, O, γ⟩` with `n = 2` (cop, thief), implemented in `domain/dec_pomdp.py`:

- **`S`** (state space): full board truth — both agents' coordinates plus the barrier layout — is combinatorially large even on a 7×7 grid, which is precisely why brute-force search over `S` is infeasible and heuristic/learned policies are required (`docs/tasks.md` Ch.1).
- **`{Aᵢ}`**: orthogonal movement, barrier placement (cop only), and a natural-language verbal channel (hints/bluffs) — mixing physical and "psychological" action spaces.
- **`P`**: the transition function is not centrally computed by any referee; both peers independently apply the same rules to the same signed `config/game.json`, so they always agree on the result without needing to trust each other (see Commit-Reveal below).
- **`{Ωᵢ}, O`**: neither agent ever observes `S` directly. Each side's *only* signal about the other is a decaying pheromone scent trail (`domain/scent.py`) and the opponent's (possibly deceptive) verbal hint (`domain/hints.py`) — this is the whole reason a `BeliefMap` (`domain/belief.py`) exists: it is a Bayesian-style posterior over the opponent's position, built from the one channel that cannot lie (scent), that the verbal channel (which can lie) is checked against.
- **`γ`** (discount factor): favors patient, multi-turn strategies (e.g. building a barrier cage over several turns) over greedy one-step gains.

The practical upshot for the thief specifically: since the state space forbids exhaustive search, the thief's own belief about *where the cop currently believes it is* — inferred from how the cop's scent-adjacent movement responds over time — is exactly as important as its own position.

### FastMCP / P2P architecture and orchestration dilemmas

Every peer is simultaneously an MCP server (exposing `@mcp.tool` endpoints the opponent calls) and an MCP client (calling the opponent's tools) — `services/mcp_server.py` / `mcp_client.py`. There is no central game server; each side enforces the rules against its own copy of the byte-identical, signed `config/game.json` (Appendix B), and the two independent copies are provably consistent via `config_sha256` rather than via a shared referee.

Building this raised real orchestration tensions, deliberately worked through rather than glossed over:
- **Turn/deadline management**: a hung or slow opponent must not hang this peer forever. `services/deadline_tracker.py` wraps every network await with a hard timeout, and `services/watchdog.py` provides heartbeat monitoring with a controlled shutdown instead of an indefinite wait — see `docs/PRD_reliability_layer.md`.
- **Network-failure handling**: dropped tunnels, a stale opponent process, or a malformed response all have to fail *safely* (technical loss, not a crash) — enforced by `services/state_machine.py` rejecting any illegal state transition outright.
- **Gatekeeper / Orchestrator roles**: `services/orchestrator.py` is the single call-path into the strategy + network + crypto layers per turn (no other module calls the network directly), and `services/gatekeeper.py` is the analogous single choke point for outbound Gmail reporting (token-bucket rate limiting + quota manager + DOS anomaly detector) — see `docs/PRD_gmail_gatekeeper.md`.
- **Public reachability**: FastMCP servers are exposed off `localhost` via an `ngrok`/`Localtonet` tunnel for real cross-machine play (Chapter 2, Stage 5) — a real tunnel session with the sibling cop repo is one of the manual steps still outstanding (see below).

### Commit-Reveal protocol

Every move is committed (`H = SHA256(state ‖ move ‖ intent ‖ nonce)`) before it is revealed, so neither side can retroactively rewrite what it "actually" played — `services/commit_reveal.py`. The nonce is withheld until reveal, both sides run a mutual end-of-match audit over the full log, and a Step-0 hardware/commit-hash fairness declaration (`services/step0.py`) is exchanged before the first move. Full design rationale, worked examples, and the tampering/rejection test matrix are in `docs/PRD_commit_reveal_crypto.md`.

### Thief strategy design

The shipped baseline (`docs/PLAN.md` ADR-010, `docs/PRD_strategy_module.md`) is a **Manhattan-distance heuristic blended with a Bayesian belief map** (`domain/heuristics.py`, `domain/belief.py`, `domain/strategy/manhattan_brain.py`) — chosen over reinforcement learning as the fastest path to a working, testable baseline, with RL treated as an explicitly optional stretch track the rulebook itself does not require (Sec. 6.2.1). The thief's decision loop:

1. Update its own `BeliefMap` from the cop's scent trail (the one channel that cannot lie).
2. Read the cop's verbal hint and run `detect_bluff` against the belief map's own picture — a claimed direction contradicted by the real scent is flagged as a lie.
3. Move away from the belief map's `arg_max` (the cop's most likely position), never toward its own true, hidden position — the LLM (when used for hint phrasing) never decides the move itself; that boundary is enforced structurally in `BrainBase`, not just by convention.

### Learning / empirical evidence

Not applicable in this build: reinforcement learning was evaluated and deliberately **not** chosen as the strategy track (see ADR-010 above and `docs/PRD_strategy_module.md` §1) — the rulebook explicitly treats RL as one optional tool among several, not a requirement (rule 25/T0251). No learning-curve data therefore exists to report. The empirical evidence that *is* available is behavioral: `tests/integration/test_strategy_pipeline.py` proves two real, independent belief-map/heuristic brains reach a capture using only their own local observations, never reading the opponent's true position.

### Screenshots

**Live GUI (belief heatmap + turn banner):**

![Live GUI thief local-truth heatmap](assets/live_gui_thief.png)

**Replay Viewer — `Verified OK`:**

![Replay Viewer verified OK](assets/replay_verified_ok.png)

(The underlying behavior for both is also proven by real widget-state assertions in `tests/unit/test_gui.py` / `tests/unit/test_replay.py`.)

### Sibling repository

Cop submission (the opponent this thief plays against): **https://github.com/aishadahesh/uoh-ay26-final-project-cop**

### Submission tagging

Per rule 41, the final submission commit in both repos must be marked with an annotated, documented Git tag (not created yet — do this only at actual submission time):

```bash
git tag -a v1.0-submission -m "Final submission: Police-Thief P2P, group N"
git push origin v1.0-submission
```

## What's built

The project follows `docs/tasks.md` (the full rulebook extraction) chapter by chapter. All 11 numbered chapters are implemented, tested, and documented:

| Chapter | What it built |
|---|---|
| 1 | Dec-POMDP formal model (`domain/dec_pomdp.py`) |
| 2 | P2P networking over FastMCP — every peer is simultaneously server and client (`services/mcp_server.py`, `mcp_client.py`) |
| 3 | Board physics: movement, barriers, capture, scoring (`domain/board.py`, `capture.py`, `scoring.py`) |
| 4 | Pheromone scent trails — mandatory emission/decay formula (`domain/scent.py`) |
| 5 | Commit-reveal cryptographic protocol (SHA-256) + Step-0 hardware fairness declaration (`services/commit_reveal.py`, `step0.py`) |
| 6 | Strategy module: Bayesian belief map + Manhattan-heuristic brain + natural-language hints/bluff detection (`domain/belief.py`, `strategy/`, `hints.py`) |
| 7 | Live GUI (local-truth-only) + Replay Viewer with cryptographic verification (`domain/live_view_model.py`, `replay.py`, `gui/`) |
| 8 | Reliability layer: legal state machine, Deadline Tracker, Watchdog, Orchestrator (`services/state_machine.py`, `deadline_tracker.py`, `watchdog.py`, `orchestrator.py`) |
| 9 | League scoring, Gatekeeper (rate limiter + quota + anomaly detector), Gmail JSON reporting (`domain/league.py`, `services/gatekeeper.py`, `match_reports.py`, `gmail_report_sender.py`) |
| 10 | Milestone reconciliation against the rulebook's own recommended build order |
| 11 | Full 55-mandatory-rule compliance sweep |

Two things were added after Chapter 11, prompted by direct user requests:
- **A richer GUI** (`gui/board_canvas.py`): agent markers, a visited-cell trail, and a Replay Viewer that now actually renders the board with Play/Pause and jump-to-step — inspired by, but not copied from, the course's reference example repo.
- **Real Gmail OAuth** (`services/gmail_oauth.py`): a working `send`-scope-only OAuth transport, ported from a proven pattern in a separate prior project and plugged directly into the existing reporting pipeline.

Every chapter's design rationale, constraints, and test evidence lives in its own `docs/PRD_<mechanism>.md`. The full chapter-by-chapter build log — what was implemented, what broke and how it was fixed, what was deliberately deferred and why — is in **`ProgressDoc.md`**.

## Quick start

```bash
uv sync                    # install dependencies
uv sync --extra email      # add if you want the real Gmail OAuth transport (optional)
```

**See the belief-map GUI live** (no networking, just the scent/belief mechanics driving a chase):

```bash
uv run python -m police_thief demo --role thief
```

**Run a full local match** (single process, placeholder policies, prints the result):

```bash
uv run python -m police_thief simulate
```

**Play locally with Gemini-powered agents:**

Copy `.env-example` to `.env`, set your Google AI Studio key, and launch the
interactive command center:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.6-flash
```

```bash
uv run python -m police_thief play
```

Gemini selects among the moves already approved by the deterministic rules
engine and its tactical rationale appears in the sidebar. Invalid model output
or an API failure safely falls back to the Manhattan heuristic. Human vs Human
remains fully offline.

### Agent vs Agent on two computers (MCP)

Choose **Agent vs Agent (Two Computers)** from the same `play` launcher. In
this thief repository, the network role is fixed to `thief` in the setup
dialog. The sibling cop repository should run the cop side. Each machine runs
an ngrok or Localtonet HTTP tunnel to the local port shown in its setup screen.

The launcher pre-fills every field from `config/network_match.json`. Edit that
file before launching to set URLs, game ID, both teams and members, four
repository URLs, output directory, and email defaults. The peer role is always
forced to `thief` in this repo. Do not put Gemini keys or Gmail OAuth tokens in
this file; those remain in `.env`, `credentials.json`, and `token.json`.

- Put the **other computer's public URL** in **Opponent public URL**. It must
  include the FastMCP route, for example `https://abc123.ngrok.app/mcp`.
- Put your own tunnel address in **This peer's public tunnel URL** and give it
  to the opponent.
- Use the same game ID, sub-game number, shared `config/game.json`, and shared
  match secret on both computers.
- Enter Team 1 and Team 2 names, both individual member fields for each team,
  plus all four repository URLs;
  they are recorded in the final result schema.

For the lower-level `serve` command, the same opponent address belongs in
`[network].opponent_url` inside the private role file
`config/thief/game.toml`; a submission-facing copy of this thief private config
also exists at `config/game.toml`, matching the rulebook's private-file name.
Never put the opponent URL in the shared `config/game.json`.

Both peers act as MCP server and client simultaneously. Every move is
commit-verified. The final score and log hash are authenticated and compared
on both computers before `mutual_sign_off` becomes `true`. Each peer writes:

```text
declaration_<game_id>.json
config_<game_id>_g<NN>.json
log_<game_id>_g<NN>.json
result_<game_id>.json
```

Enable **Automatically email result JSON** to send the final JSON-only report.
The assignment address `rmisegal+uoh26finalgame@gmail.com` is pre-filled, but
the recipient field can be changed before starting. Install the email extra first, place
Google OAuth `credentials.json` in the project root, and complete browser
consent once; its reusable token is stored as `token.json`. Email is sent only
after both computers agree on the result.

**Run this peer as a real, standalone FastMCP process:**

```bash
uv run python -m police_thief serve                # --role defaults to thief
```

**For local interop/protocol testing only**, you can also run a second process
pretending to be the opponent on the same machine. The first form below is
the exact PDF-compatible "How to Run" form:

```bash
# Terminal 1
uv run python -m police_thief peer --role police    # local opponent peer only

# Terminal 2
uv run python -m police_thief peer --role thief
```

The existing `serve` command remains supported as the same operation:

```bash
uv run python -m police_thief serve --role cop
uv run python -m police_thief serve --role thief
```

`--role police` / `--role cop` prints a one-line stderr notice every time,
since it is never a submission-grade cop peer in this repo — only a local
stand-in for the real cop process, which lives in the sibling repo. This repo
does not track `config/cop/`; the local police smoke process uses built-in
loopback defaults while the thief peer loads `config/thief/game.toml`.

**Replay a saved, cryptographically-sealed match log:**

```bash
uv run python -m police_thief replay --log path/to/log.json
```

## Testing & quality gates

```bash
uv run pytest --cov     # 441 tests, 85%+ coverage required by pyproject.toml
uv run ruff check .     # zero violations required
```

Tests favor real behavior over mocks wherever feasible: real local FastMCP HTTP servers in background threads, real Tkinter widgets, real file round-trips, real `google-api-python-client` objects against hand-built fake services. The one consistent, honest exception is the true external boundary — a real Gmail send, a real OAuth browser consent, a real `ngrok` tunnel — which cannot happen inside an automated session and is documented as a manual step wherever it applies.

## Project layout

```
src/police_thief/
  domain/       # pure game logic: board, scent, belief, replay, league, strategy
  services/     # crypto, networking, reliability layer, Gmail/Gatekeeper
  gui/          # Tkinter Live GUI + Replay Viewer
  shared/       # config loading, constants, versioning
  main.py       # CLI: serve / simulate / demo / replay
config/
  game.json           # shared, signed match config (both sides must load byte-identical)
  game.toml           # submission-facing private config for this thief peer
  thief/               # this repo's real, submitted private config
docs/
  tasks.md            # full rulebook extraction (single source of truth for requirements)
  PRD.md, PLAN.md      # master design documents
  PRD_<mechanism>.md   # one focused design doc per subsystem
  TODO.md              # ~900 granular tasks, honestly checked off chapter by chapter
tests/
  unit/, integration/
ProgressDoc.md    # the chapter-by-chapter development log
```

## What's genuinely still outstanding

Tracked in detail in `docs/TODO.md` and `ProgressDoc.md`'s Chapter 11 entry — the short version:

- The mandatory screenshots in the [Academic Report](#academic-report) section above have been captured and inserted.
- A real Google Cloud OAuth consent flow (the code is ready; someone needs to create the project and run it once).
- A real `ngrok`/tunnel session for cross-machine play against the sibling cop repo.
- Actual league matches against other teams' agents, plus final human confirmation
  that the GitHub URLs, group name, and 8-character group ID in
  `config/game.toml`, `config/thief/game.toml`, and `config/network_match.json`
  are the exact values the team wants to submit.
- The annotated `v1.0-submission` Git tag (command above) — created only at actual submission time, in both repos.
- One open rulebook-interpretation question found during the Chapter 11 sanity sweep (rule 47 — see `docs/TODO.md`).
