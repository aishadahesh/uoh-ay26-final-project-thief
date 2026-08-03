"""Unit tests for the four mandatory match-lifecycle JSON reports (Chapter 9, Sec. 9.3.16-9.3.22)."""

from police_thief.domain.replay import load_log, save_log
from police_thief.services.commit_reveal import LogEntry, commit
from police_thief.services.match_reports import (
    MatchReportError,
    RepoCrossLinks,
    TeamInfo,
    build_config_snapshot,
    build_declaration,
    build_match_result,
    config_filename,
    declaration_filename,
    load_config_snapshot_dict,
    load_declaration_dict,
    load_match_result_dict,
    log_filename,
    result_filename,
    results_agree,
    save_config_snapshot,
    save_declaration,
    save_match_result,
    sha256_of_log,
)
from police_thief.services.step0 import (
    Step0Declaration,
    TokenUsage,
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


def test_match_result_round_trips_and_includes_all_four_repo_links(tmp_path):
    entries = _log_entries(2)
    tokens = TokenUsage()
    tokens.add(100, 50)
    links = RepoCrossLinks(
        team_a_cop_repo="a-cop",
        team_a_thief_repo="a-thief",
        team_b_cop_repo="b-cop",
        team_b_thief_repo="b-thief",
    )
    result = build_match_result("G001", 1, 20, 5, "capture", True, entries, tokens, links)
    save_match_result(result, tmp_path)

    loaded = load_match_result_dict(tmp_path, "G001")
    assert loaded["cop_score"] == 20
    assert loaded["thief_score"] == 5
    assert loaded["total_tokens_used"] == 150
    assert loaded["token_usage_available"] is True
    assert loaded["repo_links"] == {
        "team_a_cop_repo": "a-cop",
        "team_a_thief_repo": "a-thief",
        "team_b_cop_repo": "b-cop",
        "team_b_thief_repo": "b-thief",
    }
    assert loaded["log_sha256"] == sha256_of_log(entries)


def test_results_agree_true_for_matching_reports():
    entries = _log_entries(2)
    tokens = TokenUsage()
    links = RepoCrossLinks("a", "b", "c", "d")
    own = build_match_result("G001", 1, 20, 5, "capture", True, entries, tokens, links)
    opponent = build_match_result("G001", 1, 20, 5, "capture", True, entries, tokens, links)
    assert results_agree(own, opponent) is True


def test_match_result_marks_unavailable_token_usage_explicitly(tmp_path):
    entries = _log_entries(1)
    result = build_match_result(
        "G-TOKENS",
        1,
        5,
        10,
        "survival",
        True,
        entries,
        TokenUsage(),
        RepoCrossLinks("a", "b", "c", "d"),
    )
    save_match_result(result, tmp_path)

    loaded = load_match_result_dict(tmp_path, "G-TOKENS")
    assert loaded["total_tokens_used"] == 0
    assert loaded["token_usage_available"] is False


def test_results_agree_false_on_a_score_disagreement():
    entries = _log_entries(2)
    tokens = TokenUsage()
    links = RepoCrossLinks("a", "b", "c", "d")
    own = build_match_result("G001", 1, 20, 5, "capture", True, entries, tokens, links)
    opponent = build_match_result("G001", 1, 15, 5, "capture", True, entries, tokens, links)
    assert results_agree(own, opponent) is False


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
