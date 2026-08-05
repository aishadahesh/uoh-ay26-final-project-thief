"""The Manhattan-distance heuristic strategy track (Chapter 6, Sec. 6.2.2/6.3).

One of three algorithmically-equal tracks (heuristic / custom / optional
RL) -- per docs/PLAN.md ADR-010, this is the team's chosen baseline. Moves
toward (cop) or away from (thief) the belief map's current best guess,
never the opponent's true position, using the mandatory Manhattan-distance
formula (Sec. 6.3.2) shared with the Chapter 3/4 placeholder policies via
domain/heuristics.py.
"""

from __future__ import annotations

from police_thief.domain.belief import BeliefMap
from police_thief.domain.board import Board, Move, Position
from police_thief.domain.heuristics import (
    greedy_manhattan_move,
    manhattan_distance,
    strategic_thief_move,
)
from police_thief.domain.strategy.brain_base import BrainBase
from police_thief.shared.constants import AgentRole


class ManhattanHeuristicBrain(BrainBase):
    """Chases the belief peak if `role` is COP, flees it if THIEF."""

    def __init__(self, role: AgentRole) -> None:
        self.role = role

    def _decide_move(self, board: Board, own: Position, belief: BeliefMap) -> Move:
        target = belief.arg_max()
        if self.role is AgentRole.THIEF:
            return strategic_thief_move(board, own, target)
        return greedy_manhattan_move(board, own, target, chase=True)

    def _pick_move(self, board: Board, own: Position, belief: BeliefMap) -> Position | None:
        """Cop-only: barrier the neighbor closest to the believed target,
        progressively narrowing the thief's viable path space
        (Sec. 3.3.8's "spatial-engineering" framing).
        """
        if self.role is not AgentRole.COP or board.remaining_barrier_budget <= 0:
            return None
        neighbors = board.neighbors(own)
        if not neighbors:
            return None
        target = belief.arg_max()
        return min(neighbors, key=lambda n: manhattan_distance(n, target))
