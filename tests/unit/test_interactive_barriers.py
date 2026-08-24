"""Barrier placement and agent-driven turns, including a thief boxed in by
barriers being treated as captured.

Split by theme out of the original `test_interactive_match.py`."""

import pytest

from police_thief.domain.board import Board, BoardConfig, Move, MoveRejectedError, Position
from police_thief.domain.interactive_match import (
    GameMode,
    InteractiveMatch,
)
from police_thief.domain.scoring import MatchOutcome
from police_thief.shared.constants import AgentRole
from tests.unit.interactive_helpers import (
    _match,
)


def test_place_barrier_consumes_the_cops_turn():
    match = _match(GameMode.HUMAN_COP_VS_AGENT, cop=Position(3, 2), thief=Position(6, 6))
    match.place_barrier(Position(2, 2))
    assert match.board.is_blocked(Position(2, 2))
    assert match.current_role is AgentRole.THIEF
    assert match.turns_played == 1


def test_place_barrier_on_the_thiefs_cell_captures_it():
    match = _match(GameMode.HUMAN_COP_VS_AGENT, cop=Position(3, 2), thief=Position(3, 3))
    match.place_barrier(Position(3, 3))
    assert match.outcome is MatchOutcome.CAPTURE


def test_place_barrier_rejects_an_illegal_target():
    match = _match(GameMode.HUMAN_COP_VS_AGENT, cop=Position(3, 2))
    with pytest.raises(MoveRejectedError):
        match.place_barrier(Position(0, 0))  # nowhere near the cop


def test_place_barrier_rejects_when_it_is_not_the_cops_turn():
    match = _match(GameMode.HUMAN_VS_HUMAN)  # cop moves first
    match.apply_move(Move.STAY)  # now it's the thief's turn
    with pytest.raises(ValueError, match="only the cop"):
        match.place_barrier(Position(3, 2))


def test_place_barrier_raises_once_the_match_is_already_finished():
    match = _match(GameMode.HUMAN_COP_VS_AGENT, cop=Position(3, 2), thief=Position(3, 3))
    match.place_barrier(Position(3, 3))  # captures
    with pytest.raises(RuntimeError, match="already finished"):
        match.place_barrier(Position(0, 1))


def test_agent_move_chases_toward_the_belief_peak_for_the_cop():
    match = _match(GameMode.AGENT_VS_AGENT, cop=Position(0, 0), thief=Position(0, 6))
    # seed a belief peak near the thief by emitting its scent first
    match.scent[AgentRole.THIEF].emit(Position(0, 6))
    match.belief[AgentRole.COP].update_from_scent(match.scent[AgentRole.THIEF])
    move = match.agent_move()
    assert move in {
        Move.EAST,
        Move.STAY,
    }  # moving toward (0,6) from (0,0) means East (or STAY if not improving)


def test_agent_move_accepts_an_advisors_legal_choice():
    match = _match(GameMode.AGENT_VS_AGENT, cop=Position(0, 0))
    selected = match.agent_move(lambda _role, _own, _belief, _legal, _fallback: Move.SOUTH)
    assert selected is Move.SOUTH


def test_agent_move_rejects_an_advisors_illegal_choice_and_uses_fallback():
    match = _match(GameMode.AGENT_VS_AGENT, cop=Position(0, 0))
    baseline = match.agent_move()
    selected = match.agent_move(lambda _role, _own, _belief, _legal, _fallback: Move.NORTH)
    assert selected is baseline


def test_a_thief_boxed_in_by_barriers_is_treated_as_captured_on_the_next_action():
    """Sec. 3.3.5: a thief with no legal move left counts as captured, even
    if the action that triggered the check wasn't aimed at it directly."""
    board = Board(BoardConfig(grid_size=7, max_barriers=14))
    thief_pos = Position(3, 3)
    for neighbor in board.neighbors(thief_pos):
        board.place_barrier(
            neighbor, neighbor
        )  # box the thief in directly via the low-level Board API
    match = InteractiveMatch(
        board, Position(0, 0), thief_pos, GameMode.HUMAN_COP_VS_AGENT, max_moves=35
    )

    match.place_barrier(Position(1, 0))  # any legal cop action, unrelated to the thief's box
    assert match.outcome is MatchOutcome.CAPTURE
