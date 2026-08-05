"""Shared Manhattan-distance search helper (Chapter 6, Sec. 6.3.2).

Mandatory formula: D = |x_cop - x_target| + |y_cop - y_target|. Used both
by Chapter 3/4's placeholder policies (domain/simulation.py) and by the
real strategy module's ManhattanHeuristicBrain (domain/strategy/) -- one
implementation, not two copies of the same search loop (DRY).
"""

from __future__ import annotations

from police_thief.domain.board import Board, Move, MoveRejectedError, Position

ORTHOGONAL_MOVES = (Move.NORTH, Move.SOUTH, Move.EAST, Move.WEST)


def manhattan_distance(a: Position, b: Position) -> int:
    """D = |x_cop - x_target| + |y_cop - y_target| (Sec. 6.3.2)."""
    return abs(a.row - b.row) + abs(a.col - b.col)


def greedy_manhattan_move(board: Board, own: Position, target: Position, *, chase: bool) -> Move:
    """The single best orthogonal move toward (`chase=True`) or away from
    (`chase=False`) `target`, per Sec. 6.3.3's worked example: try every
    legal move, keep whichever minimizes/maximizes Manhattan distance.
    """
    best_move, best_distance = Move.STAY, manhattan_distance(own, target)
    for move in ORTHOGONAL_MOVES:
        try:
            candidate = board.apply_move(own, move)
        except MoveRejectedError:
            continue
        distance = manhattan_distance(candidate, target)
        improves = distance < best_distance if chase else distance > best_distance
        if improves:
            best_move, best_distance = move, distance
    return best_move


def thief_escape_score(
    board: Board, own: Position, threat: Position, move: Move
) -> tuple[int, int, int]:
    """Rank a legal escape by threat distance, future exits, then movement.

    Pure distance can make a thief oscillate along an edge or enter a cell
    with no useful exit. Mobility breaks equal-distance ties without
    weakening the mandatory Manhattan-distance objective.
    """
    destination = board.apply_move(own, move)
    distance = manhattan_distance(destination, threat)
    exits = sum(candidate is not Move.STAY for candidate in board.legal_moves(destination))
    moved = int(move is not Move.STAY)
    return distance, exits, moved


def strategic_thief_move(board: Board, own: Position, threat: Position) -> Move:
    """Choose the safest legal escape while avoiding unnecessary dead ends."""
    return max(
        board.legal_moves(own),
        key=lambda move: thief_escape_score(board, own, threat, move),
    )
