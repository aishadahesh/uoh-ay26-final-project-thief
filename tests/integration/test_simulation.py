"""Integration tests: a full local match end-to-end (Chapter 3 / Stage-1 milestone).

No networking, no crypto -- just board + movement + barriers + capture +
scoring wired together and proven to run a complete match with no crash.
"""

from pathlib import Path

from police_thief.domain.board import BoardConfig, Move, Position
from police_thief.domain.scent import ScentConfig
from police_thief.domain.scoring import MatchOutcome, ScoringTable
from police_thief.domain.simulation import run_local_match
from police_thief.shared.game_config import MatchParameters, load_match_parameters


def test_full_match_with_shipped_config_completes_with_no_crash():
    params = load_match_parameters(Path("config/game.json"))
    result = run_local_match(params)
    assert result.outcome in {MatchOutcome.CAPTURE, MatchOutcome.SURVIVAL}
    assert result.turns_played <= params.max_moves


def test_open_board_with_fleeing_thief_ends_in_survival():
    """On the shipped 7x7 config, a naive greedy chase never catches a naive greedy flee."""
    params = load_match_parameters(Path("config/game.json"))
    result = run_local_match(params)
    assert result.outcome is MatchOutcome.SURVIVAL
    assert (result.cop_score, result.thief_score) == (5, 10)
    assert result.turns_played == params.max_moves


def test_cop_adjacent_to_thief_captures_on_the_first_turn():
    params = MatchParameters(
        board=BoardConfig(grid_size=7, max_barriers=14),
        scoring=ScoringTable(),
        scent=ScentConfig(),
        cop_start=Position(0, 0),
        thief_start=Position(0, 1),
        max_moves=35,
        survival_threshold=35,
    )
    result = run_local_match(params)
    assert result.outcome is MatchOutcome.CAPTURE
    assert (result.cop_score, result.thief_score) == (20, 5)
    assert result.turns_played == 1


def test_thief_leaving_the_arena_counts_as_capture_in_local_match():
    params = MatchParameters(
        board=BoardConfig(grid_size=7, max_barriers=14),
        scoring=ScoringTable(),
        scent=ScentConfig(),
        cop_start=Position(6, 6),
        thief_start=Position(0, 0),
        max_moves=35,
        survival_threshold=35,
    )

    result = run_local_match(
        params,
        cop_policy=lambda _board, _own, _target: Move.STAY,
        thief_policy=lambda _board, _own, _target: Move.NORTH,
    )

    assert result.outcome is MatchOutcome.CAPTURE
    assert (result.cop_score, result.thief_score) == (20, 5)
    assert result.turns_played == 1


def test_cop_illegal_move_counts_as_technical_loss_in_local_match():
    params = MatchParameters(
        board=BoardConfig(grid_size=7, max_barriers=14),
        scoring=ScoringTable(),
        scent=ScentConfig(),
        cop_start=Position(0, 0),
        thief_start=Position(6, 6),
        max_moves=35,
        survival_threshold=35,
    )

    result = run_local_match(
        params,
        cop_policy=lambda _board, _own, _target: Move.NORTH,
        thief_policy=lambda _board, _own, _target: Move.STAY,
    )

    assert result.outcome is MatchOutcome.TECHNICAL_LOSS
    assert (result.cop_score, result.thief_score) == (0, 0)
    assert result.turns_played == 1


def test_max_moves_is_a_hard_cap_even_if_survival_threshold_is_higher():
    """docs/TODO.md T0137 precedence decision: max_moves always wins as a safety net.

    If survival_threshold > max_moves (a misconfiguration the loader doesn't
    forbid), the loop exhausts max_moves first and still resolves to
    SURVIVAL rather than running forever or raising.
    """
    params = MatchParameters(
        board=BoardConfig(grid_size=7, max_barriers=14),
        scoring=ScoringTable(),
        scent=ScentConfig(),
        cop_start=Position(0, 0),
        thief_start=Position(6, 6),
        max_moves=3,
        survival_threshold=10,
    )
    result = run_local_match(params)
    assert result.outcome is MatchOutcome.SURVIVAL
    assert result.turns_played == 3


def test_max_moves_cap_ends_a_stalemate_style_match():
    """A thief that can always out-flee a naive cop survives exactly to max_moves."""
    params = MatchParameters(
        board=BoardConfig(grid_size=7, max_barriers=14),
        scoring=ScoringTable(),
        scent=ScentConfig(),
        cop_start=Position(0, 0),
        thief_start=Position(6, 6),
        max_moves=5,
        survival_threshold=5,
    )
    result = run_local_match(params)
    assert result.outcome is MatchOutcome.SURVIVAL
    assert result.turns_played == 5
