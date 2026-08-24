"""Shared match builder for the interactive-play test modules.

Extracted when `test_interactive_match.py` was split by theme."""


from police_thief.domain.board import Board, BoardConfig, Position
from police_thief.domain.interactive_match import (
    GameMode,
    InteractiveMatch,
)


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
