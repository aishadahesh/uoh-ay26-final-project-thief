"""This repository is thief-only: it must refuse in-process role alternation
and refuse to run a live police runner.

Split out of the original `test_network_match.py`."""

from pathlib import Path
from threading import Event

import pytest

from police_thief.services.mcp_server import PeerInboxes
from police_thief.services.network_match import (
    NetworkMatchRunner,
    NetworkMatchSeriesRunner,
    NetworkMatchSettings,
    role_for_subgame,
)
from police_thief.shared.constants import AgentRole


def test_legacy_series_runner_rejects_in_process_role_alternation(tmp_path):
    settings = NetworkMatchSettings(
        role=AgentRole.THIEF,
        local_port=8802,
        opponent_url="https://cop.example/mcp",
        public_url="https://thief.example/mcp",
        game_id="NETWORK-TEST",
        sub_game_number=2,
        shared_config=Path(__file__).parents[2] / "config" / "game.json",
        output_dir=tmp_path,
        team_name="alpha",
        members=("Ada", "Grace"),
        opponent_team_name="beta",
        opponent_members=("Linus", "Margaret"),
        own_cop_repo="https://github.com/example/a-cop",
        own_thief_repo="https://github.com/example/a-thief",
        opponent_cop_repo="https://github.com/example/b-cop",
        opponent_thief_repo="https://github.com/example/b-thief",
        shared_key=b"integration-secret",
    )
    with pytest.raises(RuntimeError, match="in-process role alternation is disabled"):
        NetworkMatchSeriesRunner(settings, PeerInboxes()).run(Event())


def test_thief_repository_role_never_changes_between_subgames():
    assert [role_for_subgame(AgentRole.THIEF, index) for index in range(6)] == [
        AgentRole.THIEF
    ] * 6


def test_thief_repository_rejects_live_police_runner(tmp_path):
    settings = NetworkMatchSettings(
        role=AgentRole.COP,
        local_port=8802,
        opponent_url="https://peer.example/mcp",
        public_url="https://thief.example/mcp",
        game_id="NETWORK-TEST",
        sub_game_number=1,
        shared_config=Path(__file__).parents[2] / "config" / "game.json",
        output_dir=tmp_path,
    )
    with pytest.raises(RuntimeError, match="cannot run a live Police role"):
        NetworkMatchRunner(settings, PeerInboxes(), transport=object()).run(Event())
