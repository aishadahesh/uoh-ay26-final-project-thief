"""The `serve` subcommand: run this repo as a live MCP peer."""

from __future__ import annotations

import argparse
import sys
import threading
from dataclasses import replace
from pathlib import Path

from police_thief.cli.args import (
    _coerce_role,
)
from police_thief.services.mcp_server import PeerInboxes, build_peer_server, run_peer_server
from police_thief.services.network_match import NetworkMatchRunner, NetworkMatchSettings
from police_thief.services.network_match_config import load_network_defaults, validate_mcp_url
from police_thief.services.series_coordinator import mark_subgame_finished, run_series
from police_thief.shared.config import load_network_config
from police_thief.shared.constants import AgentRole


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

    from police_thief.services.gemini_agent import GeminiAgentAdvisor, GeminiConfigurationError

    load_dotenv(project_root / ".env")
    gemini_advisor = None
    if not args.smoke_test:
        try:
            gemini_advisor = GeminiAgentAdvisor()
        except GeminiConfigurationError as exc:
            raise SystemExit(f"Cannot start the network agent: {exc}") from exc
    settings = NetworkMatchSettings(
        role=role,
        local_port=network.my_port,
        opponent_url=network.opponent_url,
        public_url=defaults["public"],
        game_id=defaults["game"],
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
        llm_model=gemini_advisor.model if gemini_advisor else "deterministic-smoke",
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
