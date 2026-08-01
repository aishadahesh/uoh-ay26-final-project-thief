"""Per-peer configuration loading.

Chapter 2's mandatory environment-separation rule (docs/tasks.md Sec. 3,
"Total Separation of Working Environments") requires each role to load its
own config directory (config/cop/ vs config/thief/) — never a config
shared in memory with the other role. This module loads the [network]
section (Chapter 2) and the [strategy] section (Chapter 6, Sec. 6.1.2);
the fuller shared, signed config/game.json format (App. B) is a separate
module (shared/game_config.py).
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
    """The [network] section of a role's private config/<role>/game.toml."""

    my_port: int
    opponent_url: str
    turn_timeout_seconds: float


def config_dir_for(role: AgentRole, config_root: Path) -> Path:
    """Return this role's own config directory (config/cop/ or config/thief/).

    In this thief-submission repository, `config/cop/` is a local-only
    opponent-peer directory used for interop testing -- it is not a
    submission-grade cop config. See config/cop/game.toml's header comment.
    """
    return config_root / role.value


def load_network_config(role: AgentRole, config_root: Path) -> NetworkConfig:
    """Load role's private config/<role>/game.toml [network] section.

    Never reads the other role's directory — the caller passes only its own
    `role`, and this function only ever looks inside that one directory.
    """
    path = config_dir_for(role, config_root) / "game.toml"
    if not path.is_file():
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


def _load_toml(role: AgentRole, config_root: Path) -> dict:
    path = config_dir_for(role, config_root) / "game.toml"
    if not path.is_file():
        raise ConfigError(f"missing per-peer config file: {path}")
    with path.open("rb") as f:
        return tomllib.load(f)


def load_strategy_class(role: AgentRole, config_root: Path) -> type[BrainBase]:
    """Load role's own `[strategy]` `{role}_class` key (Sec. 6.1.2).

    E.g. for role=THIEF, reads `thief_class = "my_team.strategy:MyBrain"`
    from config/thief/game.toml -- never the other role's key or file.
    Falls back to the built-in ManhattanHeuristicBrain (docs/PLAN.md
    ADR-010's chosen baseline) if the key is absent or commented out.
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
