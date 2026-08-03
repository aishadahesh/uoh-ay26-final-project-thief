"""Unit tests for the interactive PlayApp window (real Tkinter widgets).

Turn advancement for an agent-controlled side is normally scheduled via
`root.after(...)` -- tests monkeypatch `after` to capture the scheduled
callback instead of letting a real Tkinter timer fire, then invoke it
directly, the same pattern already used for ReplayGUI's Play/Pause tests.

`messagebox.showinfo` is monkeypatched to a no-op recorder: a real modal
dialog must never block an automated test run.
"""

import tkinter as tk
from tkinter import messagebox

from police_thief.domain.board import Board, BoardConfig, Move, Position
from police_thief.domain.interactive_match import GameMode, InteractiveMatch
from police_thief.gui.play_app import PlayApp
from police_thief.shared.constants import AgentRole


def _match(
    mode: GameMode, cop=None, thief=None, max_moves: int = 35, max_barriers: int = 14
) -> InteractiveMatch:
    board = Board(BoardConfig(grid_size=7, max_barriers=max_barriers))
    return InteractiveMatch(board, cop or Position(0, 0), thief or Position(3, 3), mode, max_moves)


def _no_schedule(monkeypatch):
    """Prevent any real root.after() callback from firing during a test."""
    monkeypatch.setattr(tk.Misc, "after", lambda self, ms, func=None, *a: None)


def test_starting_on_a_human_turn_enables_only_the_legal_move_buttons(root, monkeypatch):
    _no_schedule(monkeypatch)
    match = _match(GameMode.HUMAN_COP_VS_AGENT, cop=Position(0, 0))  # cop moves first, human here
    app = PlayApp(root, match)
    app.start()
    assert app.move_buttons[Move.SOUTH].cget("state") == "normal"
    assert app.move_buttons[Move.EAST].cget("state") == "normal"
    assert app.move_buttons[Move.STAY].cget("state") == "normal"
    assert app.move_buttons[Move.NORTH].cget("state") == "disabled"
    assert app.move_buttons[Move.WEST].cget("state") == "disabled"


def test_starting_on_an_agent_turn_disables_every_control_and_schedules_the_agent(
    root, monkeypatch
):
    scheduled = []
    monkeypatch.setattr(tk.Misc, "after", lambda self, ms, func: scheduled.append(func))
    match = _match(GameMode.AGENT_VS_HUMAN_THIEF)  # cop moves first, and cop is the agent here
    app = PlayApp(root, match)
    app.start()
    assert all(b.cget("state") == "disabled" for b in app.move_buttons.values())
    assert app.barrier_button.cget("state") == "disabled"
    assert len(scheduled) == 1


def test_clicking_a_move_button_applies_the_move_and_advances(root, monkeypatch):
    _no_schedule(monkeypatch)
    match = _match(GameMode.HUMAN_COP_VS_AGENT, cop=Position(0, 0))
    app = PlayApp(root, match)
    app.start()
    app.move_buttons[Move.EAST].invoke()
    assert match.positions[AgentRole.COP] == Position(0, 1)
    assert match.current_role is AgentRole.THIEF


def test_clicking_an_illegal_move_button_is_a_no_op(root, monkeypatch):
    _no_schedule(monkeypatch)
    match = _match(GameMode.HUMAN_COP_VS_AGENT, cop=Position(0, 0))
    app = PlayApp(root, match)
    app.start()
    app._on_human_move(
        Move.NORTH
    )  # off the board -- disabled, but call the handler directly to prove it's a no-op
    assert match.positions[AgentRole.COP] == Position(0, 0)
    assert match.turns_played == 0


def test_clicking_a_legal_board_cell_applies_the_corresponding_move(root, monkeypatch):
    _no_schedule(monkeypatch)
    match = _match(GameMode.HUMAN_COP_VS_AGENT, cop=Position(3, 2), thief=Position(6, 6))
    app = PlayApp(root, match)
    app.start()
    app._on_cell_click(3, 3)  # East of (3,2)
    assert match.positions[AgentRole.COP] == Position(3, 3)


def test_clicking_a_cell_that_is_not_a_legal_move_is_a_no_op(root, monkeypatch):
    _no_schedule(monkeypatch)
    match = _match(GameMode.HUMAN_COP_VS_AGENT, cop=Position(0, 0))
    app = PlayApp(root, match)
    app.start()
    app._on_cell_click(6, 6)
    assert match.turns_played == 0


def test_toggling_barrier_mode_then_clicking_places_a_barrier(root, monkeypatch):
    _no_schedule(monkeypatch)
    match = _match(GameMode.HUMAN_COP_VS_AGENT, cop=Position(0, 0), thief=Position(6, 6))
    app = PlayApp(root, match)
    app.start()
    app._toggle_barrier_mode()
    assert app._barrier_mode is True
    app._on_cell_click(0, 1)
    assert match.board.is_blocked(Position(0, 1))
    assert app._barrier_mode is False  # reset after placing


def test_barrier_button_is_disabled_when_the_human_controls_the_thief(root, monkeypatch):
    _no_schedule(monkeypatch)
    match = _match(GameMode.AGENT_VS_HUMAN_THIEF)
    match.apply_move(Move.STAY)  # cop (agent) moves first via direct call; now thief's (human) turn
    app = PlayApp(root, match)
    app.start()
    assert app.barrier_button.cget("state") == "disabled"


def test_agent_turn_callback_applies_the_agents_move_and_advances(root, monkeypatch):
    scheduled = []
    monkeypatch.setattr(tk.Misc, "after", lambda self, ms, func: scheduled.append(func))
    match = _match(GameMode.AGENT_VS_HUMAN_THIEF)
    app = PlayApp(root, match)
    app.start()
    assert match.current_role is AgentRole.COP
    scheduled.pop()()  # fire the scheduled agent turn
    assert match.current_role is AgentRole.THIEF
    assert match.turns_played == 1


def test_human_vs_human_mode_draws_both_true_positions(root, monkeypatch):
    _no_schedule(monkeypatch)
    match = _match(GameMode.HUMAN_VS_HUMAN)
    app = PlayApp(root, match)
    app.start()
    assert len(app.canvas._marker_ids) == 4  # two agent markers (oval + text each)


def test_a_stale_scheduled_agent_turn_after_the_match_already_ended_is_a_no_op(root, monkeypatch):
    """`after()` isn't cancelled when the match ends some other way -- a
    stale scheduled agent turn firing afterward must not crash or apply a
    move to a finished match."""
    scheduled = []
    monkeypatch.setattr(tk.Misc, "after", lambda self, ms, func: scheduled.append(func))
    match = _match(GameMode.AGENT_VS_HUMAN_THIEF, cop=Position(3, 2), thief=Position(3, 3))
    app = PlayApp(root, match)
    app.start()
    stale_agent_turn = scheduled.pop()
    match.apply_move(Move.EAST)  # the agent (cop) captures immediately via a direct call
    assert match.is_finished is True
    stale_agent_turn()  # must not raise or double-apply
    assert match.turns_played == 1


def test_toggle_barrier_mode_is_a_no_op_when_it_is_not_the_humans_turn(root, monkeypatch):
    _no_schedule(monkeypatch)
    match = _match(GameMode.AGENT_VS_HUMAN_THIEF)  # cop (agent) moves first
    app = PlayApp(root, match)
    app.start()
    app._toggle_barrier_mode()
    assert app._barrier_mode is False


def test_cell_click_is_a_no_op_when_it_is_not_the_humans_turn(root, monkeypatch):
    _no_schedule(monkeypatch)
    match = _match(GameMode.AGENT_VS_HUMAN_THIEF)  # cop (agent) moves first
    app = PlayApp(root, match)
    app.start()
    app._on_cell_click(3, 4)
    assert match.turns_played == 0


def test_clicking_an_illegal_barrier_target_in_barrier_mode_is_a_no_op(root, monkeypatch):
    _no_schedule(monkeypatch)
    match = _match(GameMode.HUMAN_COP_VS_AGENT, cop=Position(0, 0))
    app = PlayApp(root, match)
    app.start()
    app._toggle_barrier_mode()
    app._on_cell_click(6, 6)  # nowhere near the cop -- MoveRejectedError inside place_barrier
    assert match.turns_played == 0
    assert app._barrier_mode is True  # unchanged -- the attempt never completed


def test_match_end_disables_controls_and_shows_a_result_message(root, monkeypatch):
    _no_schedule(monkeypatch)
    shown = []
    monkeypatch.setattr(messagebox, "showinfo", lambda title, message: shown.append(message))
    match = _match(GameMode.HUMAN_COP_VS_AGENT, cop=Position(3, 2), thief=Position(3, 3))
    app = PlayApp(root, match)
    app.start()
    app._on_human_move(Move.EAST)  # captures immediately
    assert match.is_finished is True
    assert shown == ["Capture!"]
    assert all(b.cget("state") == "disabled" for b in app.move_buttons.values())
    assert "Capture!" in app.status_label.cget("text")


def test_new_game_button_calls_the_session_callback(root, monkeypatch):
    _no_schedule(monkeypatch)
    calls = []
    app = PlayApp(
        root, _match(GameMode.HUMAN_VS_HUMAN), on_new_game=lambda: calls.append(True) or True
    )
    app.start()
    app.new_game_button.invoke()
    assert calls == [True]


def test_canceling_new_game_resumes_the_current_match(root, monkeypatch):
    _no_schedule(monkeypatch)
    match = _match(GameMode.HUMAN_VS_HUMAN)
    app = PlayApp(root, match, on_new_game=lambda: False)
    app.start()
    app.new_game_button.invoke()
    assert app._paused is False
    assert app.shell.winfo_exists()


def test_close_destroys_the_session_shell(root, monkeypatch):
    _no_schedule(monkeypatch)
    app = PlayApp(root, _match(GameMode.HUMAN_VS_HUMAN))
    shell = app.shell
    app.start()
    app.close()
    assert app._closed is True
    assert not shell.winfo_exists()
