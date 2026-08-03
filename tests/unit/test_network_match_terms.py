"""Network match metadata serialization tests."""

from pathlib import Path

from police_thief.services.mcp_server import PeerInboxes
from police_thief.services.network_match import NetworkMatchRunner, NetworkMatchSettings
from police_thief.shared.constants import AgentRole
from police_thief.shared.game_config import load_match_parameters


def _settings(**overrides):
    project_root = Path(__file__).parents[2]
    defaults = {
        "role": AgentRole.THIEF,
        "local_port": 8802,
        "opponent_url": "http://127.0.0.1:8801/mcp",
        "public_url": "https://thief.example/mcp",
        "game_id": "MATCH-TERMS",
        "sub_game_number": 1,
        "shared_config": project_root / "config" / "game.json",
        "output_dir": project_root / "tmp" / "test-network-terms",
    }
    defaults.update(overrides)
    return NetworkMatchSettings(**defaults)


def test_official_terms_serialize_counted_series_without_smoke_flag():
    settings = _settings(series_id="SERIES-A", game_index=2, counted=True, smoke_test=False)
    runner = NetworkMatchRunner(settings, PeerInboxes())
    params = load_match_parameters(settings.shared_config)
    terms = runner._terms(params)

    assert terms["series_id"] == "SERIES-A"
    assert terms["game_index"] == 2
    assert terms["counted"] is True
    assert terms["smoke_test"] is False
    assert terms["num_games_declared"] == 6


def test_smoke_terms_are_non_counted_without_changing_shared_num_games():
    settings = _settings(counted=True, smoke_test=True)
    runner = NetworkMatchRunner(settings, PeerInboxes())
    params = load_match_parameters(settings.shared_config)
    terms = runner._terms(params)

    assert terms["counted"] is False
    assert terms["smoke_test"] is True
    assert terms["num_games_declared"] == 6
    assert params.network_league.num_games == 6
