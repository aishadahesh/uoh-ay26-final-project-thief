"""CLI readiness checks must be non-destructive and secret-free."""

import json

from police_thief.main import main, parse_args
from police_thief.services.doctor import run_doctor
from police_thief.shared.constants import AgentRole


def test_doctor_offline_json_contains_no_secret_values(tmp_path):
    report = run_doctor(
        role=AgentRole.THIEF,
        config_root=tmp_path / "missing-config",
        game_config=tmp_path / "missing-game.json",
        repo_root=tmp_path,
        offline=True,
        check_opponent=False,
    )
    payload = json.dumps(report.to_dict())
    assert "token contents" not in payload
    assert report.exit_code == 1


def test_doctor_cli_writes_json_output(tmp_path, capsys):
    output = tmp_path / "doctor.json"
    try:
        main(["doctor", "--offline", "--json-output", str(output)])
    except SystemExit as exc:
        assert exc.code == 0
    captured = capsys.readouterr()
    assert "doctor role=thief" in captured.out
    assert output.is_file()
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["role"] == "thief"
    assert data["exit_code"] == 0


def test_smoke_test_requires_non_counted_flag():
    args = parse_args(["peer", "--role", "thief", "--smoke-test", "--non-counted"])
    assert args.smoke_test is True
    assert args.non_counted is True

    try:
        main(["peer", "--role", "thief", "--smoke-test"])
    except SystemExit as exc:
        assert (
            exc.code
            == "--smoke-test requires --non-counted so it cannot be mistaken for a league result"
        )
