"""The final result report: repo cross-links, token-usage honesty, and
whether two teams' reports agree.

Split by theme out of the original `test_match_reports.py`."""

from police_thief.services.match_reports import (
    RepoCrossLinks,
    build_match_result,
    load_match_result_dict,
    results_agree,
    save_match_result,
    sha256_of_log,
)
from police_thief.services.step0 import (
    TokenUsage,
)
from tests.unit.match_report_fixtures import (
    _log_entries,
)


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


def test_results_agree_true_for_matching_reports():
    entries = _log_entries(2)
    tokens = TokenUsage()
    links = RepoCrossLinks("a", "b", "c", "d")
    own = build_match_result("G001", 1, 20, 5, "capture", True, entries, tokens, links)
    opponent = build_match_result("G001", 1, 20, 5, "capture", True, entries, tokens, links)
    assert results_agree(own, opponent) is True


def test_results_agree_false_on_a_score_disagreement():
    entries = _log_entries(2)
    tokens = TokenUsage()
    links = RepoCrossLinks("a", "b", "c", "d")
    own = build_match_result("G001", 1, 20, 5, "capture", True, entries, tokens, links)
    opponent = build_match_result("G001", 1, 15, 5, "capture", True, entries, tokens, links)
    assert results_agree(own, opponent) is False
