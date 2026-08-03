"""Unit tests for verbal hints and bluff detection (Chapter 6)."""

import pytest

from police_thief.domain.board import Board, BoardConfig, Move, Position
from police_thief.domain.hints import (
    MAX_HINT_WORDS,
    Hint,
    HintWordLimitError,
    TemplateHintProvider,
    detect_bluff,
    enforce_word_limit,
    parse_claimed_direction,
)
from police_thief.domain.scent import ScentConfig, ScentField


def test_enforce_word_limit_accepts_text_at_the_limit():
    enforce_word_limit(" ".join(["word"] * MAX_HINT_WORDS))


def test_enforce_word_limit_rejects_text_over_the_limit():
    with pytest.raises(HintWordLimitError):
        enforce_word_limit(" ".join(["word"] * (MAX_HINT_WORDS + 1)))


def test_template_provider_truthful_hint_matches_the_real_move():
    hint = TemplateHintProvider().generate(true_move=Move.NORTH, tell_truth=True)
    assert hint.intent_truthful is True
    assert parse_claimed_direction(hint) is Move.NORTH


def test_template_provider_lie_claims_the_configured_false_move():
    hint = TemplateHintProvider().generate(
        true_move=Move.NORTH, tell_truth=False, false_move=Move.SOUTH
    )
    assert hint.intent_truthful is False
    assert parse_claimed_direction(hint) is Move.SOUTH


def test_template_provider_output_always_respects_the_word_limit():
    for move in Move:
        hint = TemplateHintProvider().generate(true_move=move, tell_truth=True)
        assert len(hint.text.split()) <= MAX_HINT_WORDS


def test_template_provider_defaults_to_the_mandatory_word_limit():
    assert TemplateHintProvider().max_words == MAX_HINT_WORDS


def test_template_provider_respects_a_config_supplied_word_limit():
    provider = TemplateHintProvider(max_words=3)  # "I moved north." is exactly 3 words
    hint = provider.generate(true_move=Move.NORTH, tell_truth=True)
    assert hint.text == "I moved north."


def test_template_provider_rejects_a_config_supplied_word_limit_too_low_for_any_phrase():
    provider = TemplateHintProvider(max_words=1)
    with pytest.raises(HintWordLimitError):
        provider.generate(true_move=Move.NORTH, tell_truth=True)


def test_enforce_word_limit_respects_a_custom_max_words():
    enforce_word_limit("one two three", max_words=3)
    with pytest.raises(HintWordLimitError):
        enforce_word_limit("one two three four", max_words=3)


def test_template_phrases_never_contain_a_raw_coordinate_pattern():
    """Sec. 6.4.1/T0301: hints must never leak raw grid coordinates. True by
    construction (fixed phrase strings, no interpolated position values),
    verified directly rather than only assumed.
    """
    for move in Move:
        hint = TemplateHintProvider().generate(true_move=move, tell_truth=True)
        assert not any(ch.isdigit() for ch in hint.text)


def test_parse_claimed_direction_returns_none_for_unrecognized_text():
    assert parse_claimed_direction(Hint(text="gibberish nonsense", intent_truthful=True)) is None


def test_detect_bluff_returns_false_for_unparseable_hints():
    board = Board(BoardConfig(grid_size=7, max_barriers=14))
    scent = ScentField(grid_size=7, config=ScentConfig())
    hint = Hint(text="not a template phrase", intent_truthful=True)
    assert detect_bluff(hint, Position(3, 3), scent, board) is False


def test_detect_bluff_returns_false_with_no_scent_evidence_yet():
    board = Board(BoardConfig(grid_size=7, max_barriers=14))
    scent = ScentField(grid_size=7, config=ScentConfig())  # nothing emitted yet
    hint = TemplateHintProvider().generate(true_move=Move.NORTH, tell_truth=True)
    assert detect_bluff(hint, Position(3, 3), scent, board) is False


def test_detect_bluff_catches_a_lie_reproducing_the_worked_example():
    """docs/tasks.md Sec. 4.3.4: thief actually moves one way, claims another
    -- the real scent trail (truthful) exposes the verbal claim (a lie).
    """
    board = Board(BoardConfig(grid_size=7, max_barriers=14))
    scent = ScentField(grid_size=7, config=ScentConfig())
    prev = Position(3, 3)
    true_move = Move.SOUTH
    actual_new_pos = board.apply_move(prev, true_move)
    scent.emit(actual_new_pos)

    lie = TemplateHintProvider().generate(
        true_move=true_move, tell_truth=False, false_move=Move.NORTH
    )
    assert detect_bluff(lie, prev, scent, board) is True


def test_detect_bluff_does_not_flag_a_truthful_hint_in_the_same_scenario():
    board = Board(BoardConfig(grid_size=7, max_barriers=14))
    scent = ScentField(grid_size=7, config=ScentConfig())
    prev = Position(3, 3)
    true_move = Move.SOUTH
    actual_new_pos = board.apply_move(prev, true_move)
    scent.emit(actual_new_pos)

    truth = TemplateHintProvider().generate(true_move=true_move, tell_truth=True)
    assert detect_bluff(truth, prev, scent, board) is False


def test_detect_bluff_handles_a_cell_with_no_orthogonal_neighbors():
    """Defensive-only branch: unreachable via the config loader (which
    enforces grid_size >= 7), but a 1x1 board constructed directly bypasses
    that floor -- proving detect_bluff degrades to False rather than crashing.
    """
    board = Board(BoardConfig(grid_size=1, max_barriers=14))
    scent = ScentField(grid_size=1, config=ScentConfig())
    hint = Hint(text="I stayed put.", intent_truthful=True)
    assert detect_bluff(hint, Position(0, 0), scent, board) is False


def test_detect_bluff_flags_a_claim_to_leave_the_board_as_suspicious():
    board = Board(BoardConfig(grid_size=7, max_barriers=14))
    scent = ScentField(grid_size=7, config=ScentConfig())
    corner = Position(0, 0)
    scent.emit(board.apply_move(corner, Move.EAST))
    lie = Hint(text="I moved north.", intent_truthful=False)  # north from (0,0) is off-board
    assert detect_bluff(lie, corner, scent, board) is True
