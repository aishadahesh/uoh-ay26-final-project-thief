"""Applying a move: turn advance, legality, scent propagation, and the three
ways a match can end.

Split by theme out of the original `test_interactive_match.py`."""

import pytest

from police_thief.domain.board import Move, MoveRejectedError, Position
from police_thief.domain.interactive_match import (
    GameMode,
)
from police_thief.domain.scoring import MatchOutcome
from police_thief.shared.constants import AgentRole
from tests.unit.interactive_helpers import (
    _match,
)


def test_apply_move_updates_position_and_advances_the_turn():
    match = _match(GameMode.AGENT_VS_AGENT)
    match.apply_move(Move.EAST)
    assert match.positions[AgentRole.COP] == Position(0, 1)
    assert match.current_role is AgentRole.THIEF
    assert match.turns_played == 1


def test_apply_move_rejects_an_illegal_move():
    match = _match(GameMode.AGENT_VS_AGENT, cop=Position(0, 0))
    with pytest.raises(MoveRejectedError):
        match.apply_move(Move.NORTH)  # leaves the board


def test_thief_leaving_the_arena_counts_as_capture():
    """Appendix completion rule: a thief out-of-bounds move is captured."""
    match = _match(GameMode.HUMAN_VS_HUMAN, cop=Position(6, 6), thief=Position(0, 0))
    match.apply_move(Move.STAY)  # cop turn; now the thief is active at the top edge

    match.apply_move(Move.NORTH)

    assert match.outcome is MatchOutcome.CAPTURE
    assert match.is_finished is True


def test_apply_move_updates_the_opponents_belief_from_the_movers_scent():
    match = _match(GameMode.AGENT_VS_AGENT)
    thief_belief_before = match.belief[AgentRole.THIEF].arg_max()
    match.apply_move(Move.EAST)  # cop moves; thief's belief about the cop should update
    thief_belief_after = match.belief[AgentRole.THIEF].arg_max()
    # the thief's belief peak should now be influenced by the cop's real trail
    assert (
        thief_belief_after != thief_belief_before
        or match.belief[AgentRole.THIEF].belief_at(Position(0, 1)) > 0
    )


def test_apply_move_detects_a_capture_by_moving_onto_the_opponent():
    match = _match(GameMode.AGENT_VS_AGENT, cop=Position(3, 2), thief=Position(3, 3))
    match.apply_move(Move.EAST)
    assert match.outcome is MatchOutcome.CAPTURE
    assert match.is_finished is True


def test_apply_move_detects_survival_at_the_max_moves_cap():
    match = _match(GameMode.AGENT_VS_AGENT, max_moves=2, cop=Position(0, 0), thief=Position(6, 6))
    match.apply_move(Move.STAY)
    assert not match.is_finished
    match.apply_move(Move.STAY)
    assert match.is_finished
    assert match.outcome is MatchOutcome.SURVIVAL


def test_apply_move_raises_once_the_match_is_already_finished():
    match = _match(GameMode.AGENT_VS_AGENT, cop=Position(3, 2), thief=Position(3, 3))
    match.apply_move(Move.EAST)  # captures
    with pytest.raises(RuntimeError, match="already finished"):
        match.apply_move(Move.STAY)
