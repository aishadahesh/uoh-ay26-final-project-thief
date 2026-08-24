"""Report files on disk: mandatory naming, declaration and config-snapshot
round-trips, log hashing, and error handling for bad input.

Split by theme out of the original `test_match_reports.py`."""

from police_thief.domain.replay import load_log, save_log
from police_thief.services.commit_reveal import LogEntry
from police_thief.services.match_reports import (
    MatchReportError,
    TeamInfo,
    build_config_snapshot,
    build_declaration,
    config_filename,
    declaration_filename,
    load_config_snapshot_dict,
    load_declaration_dict,
    load_match_result_dict,
    log_filename,
    result_filename,
    save_config_snapshot,
    save_declaration,
    sha256_of_log,
)
from tests.unit.match_report_fixtures import (
    _log_entries,
    _signed_step0,
)


def test_filenames_follow_the_mandatory_pattern_and_namespace_by_game_and_subgame():
    assert declaration_filename("G001") == "declaration_G001.json"
    assert config_filename("G001", 1) == "config_G001_g01.json"
    assert log_filename("G001", 12) == "log_G001_g12.json"
    assert result_filename("G001") == "result_G001.json"


def test_declaration_round_trips_including_nested_step0_and_hardware(tmp_path):
    signed = _signed_step0()
    team = TeamInfo(
        team_name="TeamCop",
        members=("Alice", "Bob"),
        cop_repo_url="https://github.com/x/cop",
        thief_repo_url="https://github.com/x/thief",
    )
    declaration = build_declaration("G001", 1, team, signed, token_budget_per_series=200_000)
    save_declaration(declaration, tmp_path)

    loaded = load_declaration_dict(tmp_path, "G001")
    assert loaded["game_id"] == "G001"
    assert loaded["team"]["members"] == ["Alice", "Bob"]
    assert loaded["step0"]["declaration"]["hardware"]["os_name"] != ""
    assert loaded["step0"]["signature"] == signed.signature


def test_config_snapshot_round_trips(tmp_path):
    snapshot = build_config_snapshot("G001", 1, {"grid_size": 7, "max_barriers": 14}, "cafefeed")
    save_config_snapshot(snapshot, tmp_path)

    loaded = load_config_snapshot_dict(tmp_path, "G001", 1)
    assert loaded["config"] == {"grid_size": 7, "max_barriers": 14}
    assert loaded["config_sha256"] == "cafefeed"


def test_log_file_reuses_chapter_7s_save_log_and_load_log_exactly(tmp_path):
    entries = _log_entries(3)
    path = tmp_path / log_filename("G001", 1)
    save_log(entries, path)
    assert load_log(path) == entries


def test_sha256_of_log_is_stable_and_detects_any_change():
    entries = _log_entries(2)
    digest_a = sha256_of_log(entries)
    digest_b = sha256_of_log(entries)
    assert digest_a == digest_b

    tampered = list(entries)
    tampered[0] = LogEntry(
        state={"turn": 999},
        move="N",
        intent=True,
        nonce=entries[0].nonce,
        h_commit=entries[0].h_commit,
    )
    assert sha256_of_log(tampered) != digest_a


def test_loading_a_missing_report_raises_a_clear_error(tmp_path):
    try:
        load_declaration_dict(tmp_path, "NO_SUCH_GAME")
        raise AssertionError("expected MatchReportError")
    except MatchReportError:
        pass


def test_loading_a_malformed_json_report_raises_a_clear_error(tmp_path):
    path = tmp_path / result_filename("G002")
    path.write_text("{not valid json", encoding="utf-8")
    try:
        load_match_result_dict(tmp_path, "G002")
        raise AssertionError("expected MatchReportError")
    except MatchReportError:
        pass
