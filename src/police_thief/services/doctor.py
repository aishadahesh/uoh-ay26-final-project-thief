"""Non-destructive cross-machine readiness checks."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from police_thief.services.doctor_probes import (
    _group_id_valid,
    _opponent_reachable,
    _port_available,
    _private_game_toml,
    _status,
    environment_checks,
)
from police_thief.services.doctor_report import (
    DoctorCheck,
    DoctorReport,
    render_text,
    save_json_report,
)
from police_thief.shared.config import load_network_config
from police_thief.shared.constants import AgentRole
from police_thief.shared.game_config import config_fingerprint, load_match_parameters

__all__ = ["DoctorCheck", "DoctorReport", "render_text", "run_doctor", "save_json_report"]



def run_doctor(
    *,
    role: AgentRole,
    config_root: Path,
    game_config: Path,
    repo_root: Path,
    offline: bool,
    check_opponent: bool,
) -> DoctorReport:
    checks: list[DoctorCheck] = []

    try:
        params = load_match_parameters(game_config)
        checks.append(DoctorCheck("shared configuration loads", "PASS", str(game_config)))
        checks.append(
            _status(
                1 <= params.network_league.num_games <= params.network_league.max_games_per_team,
                "negotiated game count",
                f"num_games={params.network_league.num_games}",
                "num_games must be from 1 through max_games_per_team",
            )
        )
        checks.append(
            DoctorCheck(
                "configuration fingerprint generated",
                "PASS",
                config_fingerprint(game_config),
            )
        )
    except Exception as exc:  # noqa: BLE001
        checks.append(DoctorCheck("shared configuration loads", "FAIL", str(exc)))

    try:
        network = load_network_config(role, config_root)
        private = _private_game_toml(config_root, role)
        checks.append(
            DoctorCheck(
                "private configuration loads", "PASS", str(config_root / role.value / "game.toml")
            )
        )
        group_id = str(private.get("game", {}).get("group_id", ""))
        checks.append(
            _status(
                role is AgentRole.THIEF,
                "role is thief",
                role.value,
                f"doctor requested role={role.value}; this repo submits thief only",
            )
        )
        checks.append(
            _status(
                _group_id_valid(group_id),
                "group ID format valid",
                group_id or "missing",
                "group_id is missing or malformed",
            )
        )
        checks.append(
            _status(
                _port_available(network.my_port),
                "own port available",
                f"port {network.my_port}",
                f"port {network.my_port} is already in use",
            )
        )
        parsed = urlparse(network.opponent_url)
        checks.append(
            _status(
                parsed.scheme in {"http", "https"}
                and bool(parsed.netloc)
                and parsed.path.endswith("/mcp"),
                "opponent URL syntactically valid",
                f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
                "opponent_url must be http(s) and end in /mcp",
            )
        )
        email_mode = str(private.get("email", {}).get("mode", "dry_run"))
        gmail_status = "PASS" if email_mode == "dry_run" else "MANUAL CHECK"
        checks.append(
            DoctorCheck("Gmail mode operationally valid", gmail_status, f"mode={email_mode}")
        )
        if check_opponent and not offline:
            checks.append(_opponent_reachable(network.opponent_url))
        elif check_opponent:
            checks.append(
                DoctorCheck("opponent MCP reachable", "MANUAL CHECK", "offline mode requested")
            )
    except Exception as exc:  # noqa: BLE001
        checks.append(DoctorCheck("private configuration loads", "FAIL", str(exc)))

    checks.extend(environment_checks(repo_root))
    return DoctorReport(role=role.value, offline=offline, checks=checks)
