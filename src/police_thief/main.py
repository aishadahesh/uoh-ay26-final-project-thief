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
import tkinter as tk

from police_thief.cli.args import (
    DEFAULT_CONFIG_ROOT,
    _coerce_role,
    parse_args,
)
from police_thief.cli.demo import _demo
from police_thief.cli.play import _play
from police_thief.cli.serve import _serve
from police_thief.domain.replay import ReplaySession, load_log
from police_thief.domain.simulation import run_local_match
from police_thief.gui.replay_gui import ReplayGUI
from police_thief.services.doctor import render_text, run_doctor, save_json_report
from police_thief.shared.game_config import load_match_parameters

__all__ = ["main", "parse_args"]



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
