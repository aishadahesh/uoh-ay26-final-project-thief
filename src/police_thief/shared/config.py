"""Per-peer configuration loading.

Chapter 2's environment-separation rule requires this peer to load its own
private local config, never a config shared in memory with the opponent. This
thief submission repository tracks only the thief private TOML files. The
PDF-compatible local `peer --role police` smoke command uses built-in loopback
defaults instead of a tracked `config/cop/` directory.
"""

from __future__ import annotations

import importlib
import tomllib
from dataclasses import dataclass
from pathlib import Path

from police_thief.domain.strategy.brain_base import BrainBase
from police_thief.domain.strategy.manhattan_brain import ManhattanHeuristicBrain
from police_thief.shared.constants import AgentRole


class ConfigError(ValueError):
    """Raised when a per-peer config file is missing or malformed."""


@dataclass(frozen=True)
class NetworkConfig:
    """The `[network]` section of a peer's private TOML config."""

    my_port: int
    opponent_url: str
    turn_timeout_seconds: float


LOCAL_POLICE_FALLBACK = NetworkConfig(
    my_port=8801,
    opponent_url="http://127.0.0.1:8802/mcp",
    turn_timeout_seconds=180.0,
)


def config_dir_for(role: AgentRole, config_root: Path) -> Path:
    """Return the conventional private config directory for `role`."""
    return config_root / role.value


def load_network_config(role: AgentRole, config_root: Path) -> NetworkConfig:
    """Load the peer's private network config.

    The thief role reads `config/thief/game.toml`. The local police role is
    retained only for the PDF two-terminal smoke command and falls back to
    loopback defaults when no `config/cop/` directory is tracked.
    """
    path = config_dir_for(role, config_root) / "game.toml"
    if not path.is_file():
        if role is AgentRole.COP and _is_thief_submission_config(config_root):
            return LOCAL_POLICE_FALLBACK
        raise ConfigError(f"missing per-peer config file: {path}")
    with path.open("rb") as f:
        data = tomllib.load(f)
    try:
        network = data["network"]
        return NetworkConfig(
            my_port=int(network["my_port"]),
            opponent_url=str(network["opponent_url"]),
            turn_timeout_seconds=float(network.get("turn_timeout_seconds", 30.0)),
        )
    except KeyError as exc:
        raise ConfigError(f"malformed config at {path}: missing key {exc}") from exc


def _is_thief_submission_config(config_root: Path) -> bool:
    return (config_root / "game.toml").is_file() and (
        config_root / AgentRole.THIEF.value / "game.toml"
    ).is_file()


def _load_toml(role: AgentRole, config_root: Path) -> dict:
    path = config_dir_for(role, config_root) / "game.toml"
    if not path.is_file():
        raise ConfigError(f"missing per-peer config file: {path}")
    with path.open("rb") as f:
        return tomllib.load(f)


def load_strategy_class(role: AgentRole, config_root: Path) -> type[BrainBase]:
    """Load role's own `[strategy]` `{role}_class` key.

    For role=THIEF, this reads `thief_class = "my_team.strategy:MyBrain"`
    from `config/thief/game.toml`. It falls back to the built-in
    ManhattanHeuristicBrain if the key is absent or commented out.
    """
    data = _load_toml(role, config_root)
    dotted_path = data.get("strategy", {}).get(f"{role.value}_class")
    if dotted_path is None:
        return ManhattanHeuristicBrain
    module_name, _, class_name = dotted_path.rpartition(":")
    if not module_name or not class_name:
        raise ConfigError(f"strategy class must be 'module:Class', got {dotted_path!r}")
    module = importlib.import_module(module_name)
    brain_class = getattr(module, class_name)
    if not (isinstance(brain_class, type) and issubclass(brain_class, BrainBase)):
        raise ConfigError(f"{dotted_path!r} is not a BrainBase subclass")
    return brain_class
