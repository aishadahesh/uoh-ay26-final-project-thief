"""Unit tests for per-peer config loading (Chapter 2 environment separation)."""

import tomllib
from pathlib import Path

import pytest

from police_thief.shared.config import (
    LOCAL_POLICE_FALLBACK,
    ConfigError,
    config_dir_for,
    load_network_config,
)
from police_thief.shared.constants import AgentRole

VALID_TOML = """
version = "1.00"

[game]
group_name = "test-group"

[network]
my_port = 8801
opponent_url = "http://127.0.0.1:8802/mcp"
turn_timeout_seconds = 45
"""


def _write_config(tmp_path, role: AgentRole, content: str):
    role_dir = tmp_path / role.value
    role_dir.mkdir(parents=True, exist_ok=True)
    (role_dir / "game.toml").write_text(content, encoding="utf-8")


def test_config_dir_for_matches_role_value(tmp_path):
    assert config_dir_for(AgentRole.COP, tmp_path) == tmp_path / "cop"
    assert config_dir_for(AgentRole.THIEF, tmp_path) == tmp_path / "thief"


def test_load_network_config_reads_valid_toml(tmp_path):
    _write_config(tmp_path, AgentRole.COP, VALID_TOML)
    network = load_network_config(AgentRole.COP, tmp_path)
    assert network.my_port == 8801
    assert network.opponent_url == "http://127.0.0.1:8802/mcp"
    assert network.turn_timeout_seconds == 45


def test_load_network_config_applies_default_timeout_when_absent(tmp_path):
    content = """
[network]
my_port = 8801
opponent_url = "http://127.0.0.1:8802/mcp"
"""
    _write_config(tmp_path, AgentRole.COP, content)
    network = load_network_config(AgentRole.COP, tmp_path)
    assert network.turn_timeout_seconds == 30.0


def test_load_network_config_raises_on_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="missing per-peer config file"):
        load_network_config(AgentRole.COP, tmp_path)


def test_local_police_fallback_works_without_tracked_cop_config(tmp_path):
    (tmp_path / "game.toml").write_text("", encoding="utf-8")
    thief_dir = tmp_path / "thief"
    thief_dir.mkdir()
    (thief_dir / "game.toml").write_text("", encoding="utf-8")

    assert load_network_config(AgentRole.COP, tmp_path) == LOCAL_POLICE_FALLBACK


def test_load_network_config_raises_on_missing_required_key(tmp_path):
    content = """
[network]
my_port = 8801
"""
    _write_config(tmp_path, AgentRole.COP, content)
    with pytest.raises(ConfigError, match="malformed config"):
        load_network_config(AgentRole.COP, tmp_path)


def test_load_network_config_never_reads_the_other_roles_directory(tmp_path):
    """Only the cop directory exists; loading the thief role must not find it."""
    _write_config(tmp_path, AgentRole.COP, VALID_TOML)
    with pytest.raises(ConfigError):
        load_network_config(AgentRole.THIEF, tmp_path)


def test_submission_game_toml_mirrors_thief_private_config():
    """The rulebook names config/game.toml; runtime keeps config/thief/game.toml."""
    root = Path(__file__).resolve().parents[2]
    submission = tomllib.loads((root / "config" / "game.toml").read_text(encoding="utf-8"))
    thief = tomllib.loads((root / "config" / "thief" / "game.toml").read_text(encoding="utf-8"))

    assert submission["game"] == thief["game"]
    assert submission["network"] == thief["network"]
    assert submission["trash_talk"] == thief["trash_talk"]
    assert submission["llm"] == thief["llm"]
    assert submission["email"] == thief["email"]
    assert len(submission["game"]["group_id"]) == 8
    assert " " not in submission["game"]["group_id"]


def test_submission_repo_does_not_track_a_cop_private_config_directory():
    root = Path(__file__).resolve().parents[2]

    assert not (root / "config" / "cop").exists()
