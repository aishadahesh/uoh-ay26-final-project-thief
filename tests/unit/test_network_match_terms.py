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


def test_official_terms_match_the_reference_wire_contract_exactly():
    settings = _settings(series_id="SERIES-A", game_index=2, counted=True, smoke_test=False)
    runner = NetworkMatchRunner(settings, PeerInboxes())
    params = load_match_parameters(settings.shared_config)
    terms = runner._terms(params)

    assert terms == {
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
        "num_games": params.network_league.num_games,
    }


def test_local_smoke_metadata_does_not_change_signed_public_terms():
    settings = _settings(counted=True, smoke_test=True)
    runner = NetworkMatchRunner(settings, PeerInboxes())
    params = load_match_parameters(settings.shared_config)
    terms = runner._terms(params)

    assert "counted" not in terms
    assert "smoke_test" not in terms
    assert "series_id" not in terms
    assert "game_index" not in terms
    assert terms["num_games"] == params.network_league.num_games
