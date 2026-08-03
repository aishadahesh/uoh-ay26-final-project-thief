"""Unit tests for the interactive play engine (domain/interactive_match.py).

Pure logic, no Tkinter -- the same "test the domain layer directly, the GUI
just renders it" split established since Chapter 7's LiveViewModel tests.
"""

import pytest

from police_thief.domain.board import Board, BoardConfig, Move, MoveRejectedError, Position
from police_thief.domain.interactive_match import (
    MODE_LABELS,
    GameMode,
    InteractiveMatch,
    PlayerType,
    controller_for,
)
from police_thief.domain.scoring import MatchOutcome
from police_thief.shared.constants import AgentRole


def _match(
    mode: GameMode,
    grid_size: int = 7,
    max_barriers: int = 14,
    max_moves: int = 35,
    cop=None,
    thief=None,
):
    board = Board(BoardConfig(grid_size=grid_size, max_barriers=max_barriers))
    return InteractiveMatch(
        board,
        cop_start=cop or Position(0, 0),
        thief_start=thief or Position(3, 3),
        mode=mode,
        max_moves=max_moves,
    )


def test_every_game_mode_has_a_label():
    assert set(MODE_LABELS) == set(GameMode)


@pytest.mark.parametrize(
    ("mode", "cop_type", "thief_type"),
    [
        (GameMode.AGENT_VS_AGENT, PlayerType.AGENT, PlayerType.AGENT),
        (GameMode.HUMAN_COP_VS_AGENT, PlayerType.HUMAN, PlayerType.AGENT),
        (GameMode.AGENT_VS_HUMAN_THIEF, PlayerType.AGENT, PlayerType.HUMAN),
        (GameMode.HUMAN_VS_HUMAN, PlayerType.HUMAN, PlayerType.HUMAN),
    ],
)
def test_controller_for_matches_each_modes_intent(mode, cop_type, thief_type):
    assert controller_for(mode, AgentRole.COP) is cop_type
    assert controller_for(mode, AgentRole.THIEF) is thief_type


def test_cop_moves_first_by_this_projects_own_documented_choice():
    match = _match(GameMode.AGENT_VS_AGENT)
    assert match.current_role is AgentRole.COP


def test_is_human_turn_reflects_the_mode_and_current_role():
    match = _match(GameMode.HUMAN_COP_VS_AGENT)  # cop moves first, and cop is human here
    assert match.is_human_turn() is True
    match.apply_move(Move.STAY)
    assert match.is_human_turn() is False  # now the thief's (agent's) turn


def test_legal_moves_reflects_the_current_movers_own_position():
    match = _match(GameMode.AGENT_VS_AGENT, cop=Position(0, 0))
    assert set(match.legal_moves()) == {Move.SOUTH, Move.EAST, Move.STAY}


def test_visible_view_for_current_has_a_belief_and_no_opponent_position_when_an_agent_is_involved():
    match = _match(GameMode.HUMAN_COP_VS_AGENT)
    view = match.visible_view_for_current()
    assert view.belief is not None
    assert view.opponent_position is None
    assert view.own_position == Position(0, 0)
    assert view.own_role is AgentRole.COP


def test_visible_view_for_current_shows_both_true_positions_in_human_vs_human_mode():
    """The one deliberate, user-confirmed exception to Local Truth."""
    match = _match(GameMode.HUMAN_VS_HUMAN)
    view = match.visible_view_for_current()
    assert view.belief is None
    assert view.opponent_position == Position(3, 3)


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
