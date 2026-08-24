"""Argument parsing and role coercion for the CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from police_thief.shared.constants import AgentRole

DEFAULT_CONFIG_ROOT = Path(__file__).resolve().parents[3] / "config"
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
