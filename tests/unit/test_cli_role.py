"""Unit tests for the thief-repo CLI role defaults (main.py's `serve` subcommand).

This repository is submitted as the thief side only (see README.md "Role
support in this repository"). `serve`/PDF-compatible `peer` must default to
`--role thief`, and `--role cop` / `--role police` must still parse (local
opponent peer for interop testing) but must announce, every time, that it
isn't a supported submission role here.
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


def test_serve_still_accepts_cop_role_for_local_interop_testing():
    args = main.parse_args(["serve", "--role", "cop"])
    assert args.role == AgentRole.COP.value


def test_serve_accepts_pdf_police_role_alias_for_local_interop_testing():
    args = main.parse_args(["serve", "--role", "police"])
    assert main._coerce_role(args.role) is AgentRole.COP


def test_peer_alias_defaults_to_thief_for_pdf_how_to_run_command():
    args = main.parse_args(["peer"])
    assert args.command == "peer"
    assert args.role == AgentRole.THIEF.value


def test_peer_alias_accepts_pdf_police_role():
    args = main.parse_args(["peer", "--role", "police"])
    assert main._coerce_role(args.role) is AgentRole.COP


def test_replay_accepts_pdf_log_flag(tmp_path):
    log = tmp_path / "police_match.json"
    args = main.parse_args(["replay", "--log", str(log)])
    assert args.log_file == log


def test_serve_rejects_unknown_role():
    with pytest.raises(SystemExit):
        main.parse_args(["serve", "--role", "referee"])


def _boom(role, config_root):
    raise RuntimeError("stop before networking")


def test_serve_prints_unsupported_notice_for_cop_role(monkeypatch, capsys):
    """--role cop must announce it is a local-only opponent peer, not a submission role."""
    monkeypatch.setattr(main, "load_network_config", _boom)

    args = main.parse_args(["serve", "--role", "cop"])
    with pytest.raises(RuntimeError, match="stop before networking"):
        main._serve(args)

    captured = capsys.readouterr()
    assert "not a supported submission role" in captured.err
    assert "sibling cop repository" in captured.err


def test_serve_prints_unsupported_notice_for_police_role(monkeypatch, capsys):
    """PDF-compatible --role police must announce local-only opponent mode."""
    monkeypatch.setattr(main, "load_network_config", _boom)

    args = main.parse_args(["peer", "--role", "police"])
    with pytest.raises(RuntimeError, match="stop before networking"):
        main._serve(args)

    captured = capsys.readouterr()
    assert "not a supported submission role" in captured.err
    assert "police" in captured.err


def test_serve_thief_role_prints_no_unsupported_notice(monkeypatch, capsys):
    monkeypatch.setattr(main, "load_network_config", _boom)

    args = main.parse_args(["serve", "--role", "thief"])
    with pytest.raises(RuntimeError, match="stop before networking"):
        main._serve(args)

    captured = capsys.readouterr()
    assert "not a supported submission role" not in captured.err
