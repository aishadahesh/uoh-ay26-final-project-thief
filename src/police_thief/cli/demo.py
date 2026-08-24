"""The `demo` subcommand: run a scripted local demonstration."""

from __future__ import annotations

import argparse
import tkinter as tk

from police_thief.cli.args import (
    _coerce_role,
)
from police_thief.domain.belief import BeliefMap
from police_thief.domain.board import Board, BoardConfig, Position
from police_thief.domain.heuristics import greedy_manhattan_move
from police_thief.domain.live_view_model import TurnState, build_live_view_model
from police_thief.domain.scent import ScentConfig, ScentField
from police_thief.gui.live_gui import LiveGUI
from police_thief.shared.constants import AgentRole


def _demo(args: argparse.Namespace) -> None:
    """A standalone Live GUI demo: one selected side's local-truth view.

    Not a real match -- no networking, no commit-reveal, no strategy module
    (Chapter 6's ManhattanHeuristicBrain isn't even used here). This is just
    the Chapter 4 scent field + Chapter 6 belief map + Chapter 3 greedy
    Manhattan search, wired to the real Chapter 7 LiveGUI for screenshot and
    smoke-test use.
    """
    view_role = _coerce_role(args.role)
    board = Board(BoardConfig(grid_size=7, max_barriers=14))
    cop_pos = Position(0, 0)
    thief_pos = Position(3, 4)  # off-center: avoids the thief camping in a
    # corner for several turns maximizing distance from the cop, which would
    # otherwise build up one dominant scent blob and make the belief's guess
    # look artificially "stuck" instead of visibly tracking the chase
    scent = {
        AgentRole.COP: ScentField(grid_size=board.config.grid_size, config=ScentConfig()),
        AgentRole.THIEF: ScentField(grid_size=board.config.grid_size, config=ScentConfig()),
    }
    belief = {AgentRole.COP: BeliefMap(board), AgentRole.THIEF: BeliefMap(board)}
    visited: set[Position] = {thief_pos if view_role is AgentRole.THIEF else cop_pos}

    root = tk.Tk()
    root.title(f"Live GUI Demo - {view_role.value.title()}'s View")
    gui = LiveGUI(root, grid_size=board.config.grid_size)

    def step(turn: int) -> None:
        nonlocal cop_pos, thief_pos
        if turn >= args.turns or cop_pos == thief_pos:
            return
        thief_guess = belief[AgentRole.THIEF].arg_max()
        thief_pos = board.apply_move(
            thief_pos, greedy_manhattan_move(board, thief_pos, thief_guess, chase=False)
        )
        scent[AgentRole.THIEF].decay()
        scent[AgentRole.THIEF].emit(thief_pos)
        belief[AgentRole.COP].update_from_scent(scent[AgentRole.THIEF])

        cop_guess = belief[AgentRole.COP].arg_max()
        cop_pos = board.apply_move(
            cop_pos, greedy_manhattan_move(board, cop_pos, cop_guess, chase=True)
        )
        scent[AgentRole.COP].decay()
        scent[AgentRole.COP].emit(cop_pos)
        belief[AgentRole.THIEF].update_from_scent(scent[AgentRole.COP])

        own_pos = thief_pos if view_role is AgentRole.THIEF else cop_pos
        visited.add(own_pos)

        turn_state = TurnState.YOUR_TURN if turn % 2 == 0 else TurnState.LOCKED
        view_model = build_live_view_model(
            own_pos,
            belief[view_role],
            board,
            turn_state,
            role_label=view_role.value[:1].upper(),
            visited=frozenset(visited),
        )
        gui.render(view_model)
        root.after(args.delay_ms, step, turn + 1)

    step(0)
    root.mainloop()
