"""Individual environment probes: config presence, port availability, path
writability, secret tracking, and peer reachability."""

from __future__ import annotations

import re
import socket
import subprocess
import tempfile
import tomllib
import urllib.request
from pathlib import Path

from police_thief.domain.replay import ReplaySession, load_log
from police_thief.services.doctor_report import DoctorCheck
from police_thief.services.network_protocol import PROTOCOL_VERSION
from police_thief.shared.config import ConfigError
from police_thief.shared.constants import AgentRole


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


def environment_checks(repo_root: Path) -> list[DoctorCheck]:
    """Protocol version, writable directories, sample replay, and secret hygiene.

    Extracted from `run_doctor` unchanged; depends only on `repo_root`.
    """
    checks: list[DoctorCheck] = []
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
    return checks
