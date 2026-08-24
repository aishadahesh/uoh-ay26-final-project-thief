"""Mode vocabulary and local truth: who controls each role, who moves first,
and what the current mover is allowed to see.

Split by theme out of the original `test_interactive_match.py`."""

import pytest

from police_thief.domain.board import Move, Position
from police_thief.domain.interactive_match import (
    MODE_LABELS,
    GameMode,
    PlayerType,
    controller_for,
)
from police_thief.shared.constants import AgentRole
from tests.unit.interactive_helpers import (
    _match,
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
