"""Corner and boundary discipline: keeping interior escape options alive
rather than being sealed against an edge.

Split by theme out of the original `test_tactical_planner.py`."""

from police_thief.domain.board import Board, BoardConfig, Move, Position
from police_thief.domain.strategy.tactical_planner import TacticalPlanner
from police_thief.shared.constants import AgentRole
from tests.unit.tactical_planner_helpers import (
    _belief_at,
)


def test_thief_avoids_deeper_boundary_cells_before_police_can_seal_corner():
    """Regression for G003 g02/g04/g06."""
    board = Board(BoardConfig(grid_size=7, max_barriers=14))
    cop = Position(2, 4)
    plan = TacticalPlanner(AgentRole.THIEF, strategy_seed=2).evaluate(
        board,
        Position(1, 5),
        _belief_at(board, cop),
        known_opponent_position=cop,
    )

    assert Move.NORTH not in plan.allowed_moves
    assert Move.EAST not in plan.allowed_moves
    assert plan.selected is Move.STAY


def test_thief_does_not_enter_corner_when_no_interior_escape_exists():
    board = Board(BoardConfig(grid_size=7, max_barriers=14))
    cop = Position(1, 4)
    plan = TacticalPlanner(AgentRole.THIEF, strategy_seed=2).evaluate(
        board,
        Position(0, 5),
        _belief_at(board, cop),
        known_opponent_position=cop,
    )

    assert plan.selected is Move.STAY
    assert Move.EAST not in plan.allowed_moves


def test_thief_escapes_last_corridor_instead_of_reentering_barrier_ring():
    """G005 g04: (3,3) had three blocked exits and was about to be sealed."""
    board = Board(BoardConfig(grid_size=7, max_barriers=14))
    for row, col in (
        (2, 2), (2, 3), (2, 4), (3, 4), (4, 2), (4, 3), (4, 4),
    ):
        board.apply_declared_barrier(Position(row, col))
    plan = TacticalPlanner(AgentRole.THIEF, strategy_seed=6).evaluate(
        board,
        Position(3, 2),
        _belief_at(board, Position(5, 1)),
        known_opponent_position=Position(5, 1),
    )

    assert plan.selected is Move.WEST
    assert Move.EAST not in plan.allowed_moves
    assert Move.STAY not in plan.allowed_moves
