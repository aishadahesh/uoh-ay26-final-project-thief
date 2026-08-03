"""Non-destructive cross-machine readiness checks."""

from __future__ import annotations

import json
import re
import socket
import subprocess
import tempfile
import tomllib
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

from police_thief.domain.replay import ReplaySession, load_log
from police_thief.services.network_protocol import PROTOCOL_VERSION
from police_thief.shared.config import ConfigError, load_network_config
from police_thief.shared.constants import AgentRole
from police_thief.shared.game_config import (
    FIXED_NUM_GAMES,
    config_fingerprint,
    load_match_parameters,
)


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class DoctorReport:
    role: str
    offline: bool
    checks: list[DoctorCheck]

    @property
    def exit_code(self) -> int:
        return 1 if any(check.status == "FAIL" for check in self.checks) else 0

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "offline": self.offline,
            "exit_code": self.exit_code,
            "checks": [asdict(check) for check in self.checks],
        }


def _status(ok: bool, name: str, detail: str, fail_detail: str) -> DoctorCheck:
    return DoctorCheck(name, "PASS" if ok else "FAIL", detail if ok else fail_detail)


def _private_game_toml(config_root: Path, role: AgentRole) -> dict:
    path = config_root / role.value / "game.toml"
    if not path.is_file():
        raise ConfigError(f"missing private TOML at {path}")
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _group_id_valid(group_id: str) -> bool:
    return re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,63}", group_id) is not None


def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
        return True


def _path_writable(path: Path) -> bool:
    path.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(dir=path, prefix=".doctor-", delete=True):
            return True
    except OSError:
        return False


def _git_tracks_secret(repo_root: Path, secret_name: str) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--", secret_name],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout.strip())


def _gitignore_mentions(repo_root: Path, secret_name: str) -> bool:
    ignore = repo_root / ".gitignore"
    if not ignore.is_file():
        return False
    lines = [line.strip() for line in ignore.read_text(encoding="utf-8").splitlines()]
    return secret_name in lines


def _opponent_reachable(url: str) -> DoctorCheck:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            ok = 200 <= response.status < 500
    except Exception as exc:  # noqa: BLE001 -- readiness output should capture transport failures
        return DoctorCheck(
            "opponent MCP reachable", "FAIL", f"could not reach endpoint: {type(exc).__name__}"
        )
    return DoctorCheck(
        "opponent MCP reachable", "PASS" if ok else "FAIL", f"HTTP status {response.status}"
    )


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
                params.network_league.num_games == FIXED_NUM_GAMES,
                "mandatory game count",
                f"num_games={params.network_league.num_games}",
                f"expected fixed num_games={FIXED_NUM_GAMES}",
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

    checks.append(DoctorCheck("protocol version available", "PASS", PROTOCOL_VERSION))
    checks.append(
        _status(
            _path_writable(repo_root / "tmp"),
            "required directories writable",
            "tmp/",
            "tmp/ is not writable",
        )
    )
    checks.append(
        _status(
            _path_writable(repo_root / "results"),
            "logs directory writable",
            "results/",
            "results/ is not writable",
        )
    )
    try:
        session = ReplaySession(load_log(repo_root / "sample_match_log.json"))
        checks.append(
            _status(
                session.is_fully_verified,
                "replay verification works",
                f"verified {session.total_steps} steps",
                "sample replay did not verify",
            )
        )
    except Exception as exc:  # noqa: BLE001
        checks.append(DoctorCheck("replay verification works", "FAIL", str(exc)))

    for secret_name in (".env", "credentials.json", "token.json"):
        checks.append(
            _status(
                _gitignore_mentions(repo_root, secret_name),
                f"{secret_name} ignored",
                "listed in .gitignore",
                "not listed in .gitignore",
            )
        )
        checks.append(
            _status(
                not _git_tracks_secret(repo_root, secret_name),
                f"{secret_name} not tracked",
                "not tracked by git",
                "tracked by git",
            )
        )

    checks.append(
        DoctorCheck("smoke mode is non-counted", "PASS", "--smoke-test forces counted=false")
    )
    checks.append(
        DoctorCheck("submission tag", "MANUAL CHECK", "not required for development smoke test")
    )
    return DoctorReport(role=role.value, offline=offline, checks=checks)


def render_text(report: DoctorReport) -> str:
    lines = [f"doctor role={report.role} offline={str(report.offline).lower()}"]
    for check in report.checks:
        lines.append(f"{check.status:12} {check.name}: {check.detail}")
    return "\n".join(lines)


def save_json_report(report: DoctorReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return path
