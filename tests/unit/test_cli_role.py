"""Unit tests for the thief-repo CLI role defaults (main.py's `serve` subcommand).

This repository is submitted as the thief side only (see README.md "Role
support in this repository"). `serve`/PDF-compatible `peer` must accept only
`--role thief`; Police games belong to the independent Cop repository.
"""

from __future__ import annotations

import pytest

from police_thief import main
from police_thief.shared.constants import AgentRole


def test_serve_role_defaults_to_thief():
    args = main.parse_args(["serve"])
    assert args.role == AgentRole.THIEF.value


def test_serve_accepts_explicit_thief_role():
    args = main.parse_args(["serve", "--role", "thief"])
    assert args.role == AgentRole.THIEF.value


def test_serve_rejects_cop_role():
    with pytest.raises(SystemExit):
        main.parse_args(["serve", "--role", "cop"])


def test_serve_rejects_police_role_alias():
    with pytest.raises(SystemExit):
        main.parse_args(["serve", "--role", "police"])


def test_peer_alias_defaults_to_thief_for_pdf_how_to_run_command():
    args = main.parse_args(["peer"])
    assert args.command == "peer"
    assert args.role == AgentRole.THIEF.value


def test_peer_alias_rejects_police_role():
    with pytest.raises(SystemExit):
        main.parse_args(["peer", "--role", "police"])


def test_replay_accepts_pdf_log_flag(tmp_path):
    log = tmp_path / "police_match.json"
    args = main.parse_args(["replay", "--log", str(log)])
    assert args.log_file == log


def test_serve_rejects_unknown_role():
    with pytest.raises(SystemExit):
        main.parse_args(["serve", "--role", "referee"])


def _boom(role, config_root):
    raise RuntimeError("stop before networking")


def test_serve_thief_role_reaches_role_specific_config(monkeypatch, capsys):
    monkeypatch.setattr(main, "load_network_config", _boom)

    args = main.parse_args(["serve", "--role", "thief", "--single-subgame"])
    with pytest.raises(RuntimeError, match="stop before networking"):
        main._serve(args)

    captured = capsys.readouterr()
    assert captured.err == ""
