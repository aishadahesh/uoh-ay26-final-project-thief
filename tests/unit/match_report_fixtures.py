"""Shared fixtures for the match-report tests: a signed Step-0 declaration
and a short run of log entries.

Extracted when `test_match_reports.py` was split by theme."""

from police_thief.services.commit_reveal import LogEntry, commit
from police_thief.services.step0 import (
    Step0Declaration,
    gather_hardware_spec,
    sign_step0,
)


def _signed_step0(game_id: str = "G001", sub_game_number: int = 1):
    hardware = gather_hardware_spec(llm_model="template")
    declaration = Step0Declaration(
        hardware=hardware,
        code_version="1.00",
        team_name="TeamCop",
        game_id=game_id,
        sub_game_number=sub_game_number,
        git_commit_hash="abc123",
        config_fingerprint="deadbeef",
    )
    return sign_step0(declaration, shared_key=b"shared-secret")


def _log_entries(n: int = 2) -> list[LogEntry]:
    entries = []
    for i in range(n):
        c = commit(state={"turn": i}, move="N", intent=True)
        entries.append(
            LogEntry(state={"turn": i}, move="N", intent=True, nonce=c.nonce, h_commit=c.h_commit)
        )
    return entries
