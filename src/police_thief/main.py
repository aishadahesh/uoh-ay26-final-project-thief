"""CLI entry point: `uv run python -m police_thief <command> ...`.

This repository is the **thief-side submission repo** (sibling `cop` repo:
see README.md). Public `serve`/`peer` mode accepts only `--role thief`.
Police sub-games run from the sibling Cop repository as an independent
process with independent configuration and process memory.

Commands:
  peer [--role thief]      Coordinate the complete six-game series with
                           fresh fixed-role Thief and Cop child processes.
  serve [--role thief]
                           Start this peer's FastMCP server (Chapter 2).
                           Defaults to --role thief. Police is deliberately
                           rejected by this submission repository.
  simulate                 Run a single-process local match with placeholder
                           policies and print the result (Chapter 3).
  replay --log PATH        Launch the Replay Viewer against a saved match
                           log (Chapter 7) -- runs standalone, independent
                           of any live match code (docs/tasks.md T0437).
  demo [--role thief|police]
                           Open a standalone local-truth Live GUI window for
                           one side's view. Defaults to thief in this thief
                           submission repo. Single-process, no networking or
                           crypto layer -- just a quick way to see the Live
                           GUI in action.
  play                     Open the interactive, mode-selectable play window:
                           choose Agent vs Agent, Human (either side) vs
                           Agent, or Human vs Human, then play with a move
                           pad / board clicks / barrier placement. A
                           deliberate addition beyond the rulebook's own
                           scope -- see domain/interactive_match.py.

`serve` is the concrete realization of Chapter 2's "Total Separation of
Working Environments" rule: one shared codebase (docs/PLAN.md ADR-011), but
each invocation is its own OS process reading only its own role's config,
sharing no memory with the other role's process. `simulate` has no
networking or role concept at all -- it exercises board/movement/barrier/
capture/scoring end-to-end against the single shared config/game.json.
"""

from __future__ import annotations

import argparse
import sys
import threading
import tkinter as tk
from dataclasses import replace
from pathlib import Path
from tkinter import messagebox

from police_thief.domain.belief import BeliefMap
from police_thief.domain.board import Board, BoardConfig, Position
from police_thief.domain.heuristics import greedy_manhattan_move
from police_thief.domain.live_view_model import TurnState, build_live_view_model
from police_thief.domain.replay import ReplaySession, load_log
from police_thief.domain.scent import ScentConfig, ScentField
from police_thief.domain.simulation import run_local_match
from police_thief.gui.live_gui import LiveGUI
from police_thief.gui.network_setup import load_network_defaults, validate_mcp_url
from police_thief.gui.replay_gui import ReplayGUI
from police_thief.services.doctor import render_text, run_doctor, save_json_report
from police_thief.services.mcp_server import PeerInboxes, build_peer_server, run_peer_server
from police_thief.services.network_match import NetworkMatchRunner, NetworkMatchSettings
from police_thief.services.series_coordinator import mark_subgame_finished, run_series
from police_thief.shared.config import load_network_config
from police_thief.shared.constants import AgentRole
from police_thief.shared.game_config import load_match_parameters

DEFAULT_CONFIG_ROOT = Path(__file__).resolve().parents[2] / "config"
DEFAULT_GAME_CONFIG = DEFAULT_CONFIG_ROOT / "game.json"
ROLE_ALIASES = {
    AgentRole.COP.value: AgentRole.COP,
    "police": AgentRole.COP,
    AgentRole.THIEF.value: AgentRole.THIEF,
}


def _coerce_role(value: str) -> AgentRole:
    return ROLE_ALIASES[value]


def _add_peer_command(subparsers: argparse._SubParsersAction, name: str, help_text: str) -> None:
    command = subparsers.add_parser(name, help=help_text)
    command.add_argument(
        "--role",
        default=AgentRole.THIEF.value,
        choices=[AgentRole.THIEF.value],
        help="Only 'thief' is supported; run the sibling Cop repository for Police games.",
    )
    command.add_argument("--config-root", type=Path, default=DEFAULT_CONFIG_ROOT)
    command.add_argument(
        "--smoke-test",
        action="store_true",
        help="Label this peer as a deterministic NON-COUNTED cross-machine smoke peer.",
    )
    command.add_argument(
        "--non-counted",
        action="store_true",
        help="Require non-counted mode for smoke testing; official shared num_games is unchanged.",
    )
    command.add_argument("--single-subgame", action="store_true", help=argparse.SUPPRESS)
    command.add_argument("--sub-game-number", type=int, help=argparse.SUPPRESS)
    command.add_argument("--output-directory", type=Path, help=argparse.SUPPRESS)
    command.add_argument("--series-state", type=Path, help=argparse.SUPPRESS)
    command.add_argument("--finalize-series", action="store_true", help=argparse.SUPPRESS)
    command.add_argument(
        "--series-first-role", choices=["police", "thief"], default="thief",
        help=argparse.SUPPRESS,
    )
    command.add_argument(
        "--sibling-repo", type=Path,
        default=DEFAULT_CONFIG_ROOT.parent.parent / "uoh-ay26-final-project-cop",
        help="Path to this team's independent Cop repository.",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the `serve`/`simulate`/`replay` subcommands and their options."""
    parser = argparse.ArgumentParser(prog="police_thief")
    subparsers = parser.add_subparsers(dest="command", required=True)

    _add_peer_command(subparsers, "serve", "Start this peer's FastMCP server")
    _add_peer_command(subparsers, "peer", "PDF-compatible alias for serve")

    simulate = subparsers.add_parser("simulate", help="Run a local placeholder-policy match")
    simulate.add_argument("--game-config", type=Path, default=DEFAULT_GAME_CONFIG)

    replay = subparsers.add_parser("replay", help="Launch the Replay Viewer on a saved match log")
    replay.add_argument("--log-file", "--log", dest="log_file", required=True, type=Path)

    demo = subparsers.add_parser("demo", help="Open a standalone Live GUI demo (no networking)")
    demo.add_argument(
        "--role",
        default=AgentRole.THIEF.value,
        choices=sorted(ROLE_ALIASES),
        help="Local-truth view to render. Defaults to thief in this thief submission repo.",
    )
    demo.add_argument("--turns", type=int, default=25)
    demo.add_argument("--delay-ms", type=int, default=500)

    subparsers.add_parser("play", help="Open the interactive, mode-selectable play window")

    doctor = subparsers.add_parser(
        "doctor", help="Run non-destructive cross-machine readiness checks"
    )
    doctor.add_argument("--role", default=AgentRole.THIEF.value, choices=sorted(ROLE_ALIASES))
    doctor.add_argument("--config-root", type=Path, default=DEFAULT_CONFIG_ROOT)
    doctor.add_argument("--game-config", type=Path, default=DEFAULT_GAME_CONFIG)
    doctor.add_argument("--offline", action="store_true")
    doctor.add_argument("--check-opponent", action="store_true")
    doctor.add_argument("--json-output", type=Path)

    return parser.parse_args(argv)


def _serve(args: argparse.Namespace) -> None:
    role = _coerce_role(args.role)
    if args.smoke_test and not args.non_counted:
        raise SystemExit(
            "--smoke-test requires --non-counted so it cannot be mistaken for a league result"
        )
    if role is not AgentRole.THIEF:
        raise SystemExit(
            "This submission repository can only run the Thief peer; use the "
            "independent Cop repository for Police games."
        )
    project_root = args.config_root.parent
    defaults = load_network_defaults(args.config_root / "network_match.json", project_root)
    if not args.single_subgame:
        first_role = (
            AgentRole.COP if args.series_first_role == "police" else AgentRole.THIEF
        )
        run_series(
            current_role=AgentRole.THIEF,
            first_role=first_role,
            current_repo=project_root,
            sibling_repo=args.sibling_repo,
            config_root=args.config_root,
            output_dir=Path(defaults["output"]),
            game_id=defaults["game"],
            first_sub_game=int(defaults["subgame"]),
        )
        return
    if args.smoke_test:
        print(
            "NON-COUNTED TEST: deterministic peer server only; do not submit this as a counted result.",
            file=sys.stderr,
        )
    network = load_network_config(role, args.config_root)
    validate_mcp_url(network.opponent_url)
    required = (
        "public",
        "game",
        "secret",
        "team1_name",
        "team1_member1",
        "team1_member2",
        "team2_name",
        "team2_member1",
        "team2_member2",
        "own_cop",
        "own_thief",
        "opponent_cop",
        "opponent_thief",
    )
    missing = [key for key in required if not str(defaults.get(key, "")).strip()]
    if missing:
        raise SystemExit(
            "Cannot start the network agent: incomplete network_match.json fields: "
            + ", ".join(missing)
        )

    from dotenv import load_dotenv

    load_dotenv(project_root / ".env")
    gemini_advisor = None
    settings = NetworkMatchSettings(
        role=role,
        local_port=network.my_port,
        opponent_url=network.opponent_url,
        public_url=defaults["public"],
        game_id=defaults["game"],
        game_uid=defaults["game_uid"],
        sub_game_number=args.sub_game_number or int(defaults["subgame"]),
        shared_config=args.config_root / "game.json",
        output_dir=args.output_directory or Path(defaults["output"]),
        team_name=defaults["team1_name"],
        members=(defaults["team1_member1"], defaults["team1_member2"]),
        opponent_team_name=defaults["team2_name"],
        opponent_members=(defaults["team2_member1"], defaults["team2_member2"]),
        own_cop_repo=defaults["own_cop"],
        own_thief_repo=defaults["own_thief"],
        opponent_cop_repo=defaults["opponent_cop"],
        opponent_thief_repo=defaults["opponent_thief"],
        shared_key=defaults["secret"].encode(),
        email_mode="real" if defaults["email"] else "dry_run",
        email_recipient=defaults["email_recipient"],
        credentials_path=project_root / "credentials.json",
        token_path=project_root / "token.json",
        llm_model="deterministic-smoke" if args.smoke_test else "deterministic-brain",
    )
    inboxes = PeerInboxes()
    mcp = build_peer_server(role.value, inboxes)
    threading.Thread(
        target=run_peer_server,
        args=(mcp, "0.0.0.0", network.my_port),
        daemon=True,
        name="mcp-peer-server",
    ).start()
    print(f"MCP server listening on 0.0.0.0:{network.my_port}/mcp")
    # Keep the submitted Cop and Thief as independent live processes.  This
    # Thief entry point runs exactly one configured sub-game and never changes
    # its role in-process; the sibling Cop repository owns police-role games.
    child_settings = replace(settings, email_mode="series_deferred")
    result_path = NetworkMatchRunner(
        child_settings,
        inboxes,
        gemini_advisor=gemini_advisor,
    ).run(threading.Event(), emit=print)
    if args.series_state is not None:
        mark_subgame_finished(
            args.series_state, settings.game_id, settings.sub_game_number,
        )
    print(f"Thief sub-game complete -- result saved to {result_path}")
    if args.finalize_series:
        if args.series_state is None:
            raise RuntimeError("--finalize-series requires --series-state")
        from police_thief.services.network_match import finalize_completed_series

        first_role = (
            AgentRole.COP if args.series_first_role == "police" else AgentRole.THIEF
        )
        final_path = finalize_completed_series(
            settings, inboxes, args.series_state, first_role, emit=print,
        )
        print(f"Final series result saved to {final_path}")


def _doctor(args: argparse.Namespace) -> None:
    role = _coerce_role(args.role)
    repo_root = DEFAULT_CONFIG_ROOT.parent
    report = run_doctor(
        role=role,
        config_root=args.config_root,
        game_config=args.game_config,
        repo_root=repo_root,
        offline=args.offline,
        check_opponent=args.check_opponent,
    )
    if args.json_output:
        save_json_report(report, args.json_output)
    print(render_text(report))
    raise SystemExit(report.exit_code)


def _simulate(args: argparse.Namespace) -> None:
    params = load_match_parameters(args.game_config)
    result = run_local_match(params)
    print(
        f"outcome={result.outcome.value} cop_score={result.cop_score} "
        f"thief_score={result.thief_score} turns_played={result.turns_played}"
    )


def _replay(args: argparse.Namespace) -> None:
    session = ReplaySession(load_log(args.log_file))
    root = tk.Tk()
    root.title(f"Replay Viewer - {args.log_file.name}")
    ReplayGUI(root, session)
    root.mainloop()


def _demo(args: argparse.Namespace) -> None:
    """A standalone Live GUI demo: one selected side's local-truth view.

    Not a real match -- no networking, no commit-reveal, no strategy module
    (Chapter 6's ManhattanHeuristicBrain isn't even used here). This is just
    the Chapter 4 scent field + Chapter 6 belief map + Chapter 3 greedy
    Manhattan search, wired to the real Chapter 7 LiveGUI for screenshot and
    smoke-test use.
    """
    view_role = _coerce_role(args.role)
    board = Board(BoardConfig(grid_size=7, max_barriers=14))
    cop_pos = Position(0, 0)
    thief_pos = Position(3, 4)  # off-center: avoids the thief camping in a
    # corner for several turns maximizing distance from the cop, which would
    # otherwise build up one dominant scent blob and make the belief's guess
    # look artificially "stuck" instead of visibly tracking the chase
    scent = {
        AgentRole.COP: ScentField(grid_size=board.config.grid_size, config=ScentConfig()),
        AgentRole.THIEF: ScentField(grid_size=board.config.grid_size, config=ScentConfig()),
    }
    belief = {AgentRole.COP: BeliefMap(board), AgentRole.THIEF: BeliefMap(board)}
    visited: set[Position] = {thief_pos if view_role is AgentRole.THIEF else cop_pos}

    root = tk.Tk()
    root.title(f"Live GUI Demo - {view_role.value.title()}'s View")
    gui = LiveGUI(root, grid_size=board.config.grid_size)

    def step(turn: int) -> None:
        nonlocal cop_pos, thief_pos
        if turn >= args.turns or cop_pos == thief_pos:
            return
        thief_guess = belief[AgentRole.THIEF].arg_max()
        thief_pos = board.apply_move(
            thief_pos, greedy_manhattan_move(board, thief_pos, thief_guess, chase=False)
        )
        scent[AgentRole.THIEF].decay()
        scent[AgentRole.THIEF].emit(thief_pos)
        belief[AgentRole.COP].update_from_scent(scent[AgentRole.THIEF])

        cop_guess = belief[AgentRole.COP].arg_max()
        cop_pos = board.apply_move(
            cop_pos, greedy_manhattan_move(board, cop_pos, cop_guess, chase=True)
        )
        scent[AgentRole.COP].decay()
        scent[AgentRole.COP].emit(cop_pos)
        belief[AgentRole.THIEF].update_from_scent(scent[AgentRole.COP])

        own_pos = thief_pos if view_role is AgentRole.THIEF else cop_pos
        visited.add(own_pos)

        turn_state = TurnState.YOUR_TURN if turn % 2 == 0 else TurnState.LOCKED
        view_model = build_live_view_model(
            own_pos,
            belief[view_role],
            board,
            turn_state,
            role_label=view_role.value[:1].upper(),
            visited=frozenset(visited),
        )
        gui.render(view_model)
        root.after(args.delay_ms, step, turn + 1)

    step(0)
    root.mainloop()


def _play(args: argparse.Namespace) -> None:
    """The interactive, mode-selectable play window (see main.py's own
    module docstring and domain/interactive_match.py for scope/rationale).

    `args` is unused today (no CLI flags yet) but kept for a consistent
    handler signature alongside `_serve`/`_simulate`/`_replay`/`_demo`.
    """
    from dotenv import load_dotenv

    from police_thief.domain.interactive_match import (
        InteractiveMatch,
        PlayerType,
        controller_for,
    )
    from police_thief.gui.mode_select import ModeSelectDialog
    from police_thief.gui.network_match_app import NetworkMatchApp
    from police_thief.gui.network_setup import NetworkSetupDialog
    from police_thief.gui.play_app import PlayApp
    from police_thief.services.gemini_agent import GeminiAgentAdvisor, GeminiConfigurationError

    root = tk.Tk()
    root.withdraw()
    load_dotenv()
    current_app: PlayApp | NetworkMatchApp | None = None

    def select_and_start() -> bool:
        nonlocal current_app
        mode = ModeSelectDialog(root).show()
        if mode is None:
            return False

        if mode.value == "network_agent_vs_agent":
            try:
                gemini_advisor = GeminiAgentAdvisor()
            except GeminiConfigurationError as exc:
                root.deiconify()
                messagebox.showerror(
                    "Gemini API key required",
                    f"{exc}\n\nCopy .env-example to .env and set GEMINI_API_KEY, then launch again.",
                    parent=root,
                )
                return False
            settings = NetworkSetupDialog(root, DEFAULT_CONFIG_ROOT.parent).show()
            if settings is None:
                return False
            if current_app is not None:
                current_app.close()
            root.deiconify()
            current_app = NetworkMatchApp(
                root,
                settings,
                gemini_advisor,
                on_new_game=select_and_start,
            )
            current_app.start()
            return True

        has_agent = any(controller_for(mode, role) is PlayerType.AGENT for role in AgentRole)
        gemini_advisor = None
        if has_agent:
            try:
                gemini_advisor = GeminiAgentAdvisor()
            except GeminiConfigurationError as exc:
                root.deiconify()
                messagebox.showerror(
                    "Gemini API key required",
                    f"{exc}\n\nCopy .env-example to .env and set GEMINI_API_KEY, then launch again.",
                    parent=root,
                )
                return False

        if current_app is not None:
            current_app.close()
        board = Board(BoardConfig(grid_size=7, max_barriers=14))
        match = InteractiveMatch(board, Position(0, 0), Position(3, 3), mode, max_moves=35)
        root.deiconify()
        root.title("Police-Thief - Interactive Play")
        current_app = PlayApp(
            root, match, gemini_advisor=gemini_advisor, on_new_game=select_and_start
        )
        current_app.start()
        return True

    if not select_and_start():
        root.destroy()
        return
    root.mainloop()


def main(argv: list[str] | None = None) -> None:
    """Dispatch to `serve`, `simulate`, `replay`, `demo`, or `play` based on the parsed subcommand."""
    args = parse_args(argv)
    if args.command in {"serve", "peer"}:
        _serve(args)
    elif args.command == "simulate":
        _simulate(args)
    elif args.command == "replay":
        _replay(args)
    elif args.command == "demo":
        _demo(args)
    elif args.command == "play":
        _play(args)
    elif args.command == "doctor":
        _doctor(args)


if __name__ == "__main__":
    main()
