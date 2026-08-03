"""Unit tests for the thin Tkinter GUI layer (Chapter 7).

Tkinter works headlessly on this platform (verified: Tk() constructs and
widgets can be inspected/invoked without ever calling mainloop() or
showing a window -- root.withdraw() keeps it off-screen). These tests
exercise real widget construction, state, and button wiring rather than
mocking Tkinter away, since the actual risk in a "thin wiring" layer is a
typo in a widget option name or a wrong callback, which only a real
widget catches.
"""

import dataclasses
import tkinter as tk

from police_thief.domain.belief import BeliefMap
from police_thief.domain.board import Board, BoardConfig, Position
from police_thief.domain.live_view_model import TurnState, build_live_view_model
from police_thief.domain.replay import ReplaySession
from police_thief.domain.scent import ScentConfig, ScentField
from police_thief.gui.live_gui import LiveGUI
from police_thief.gui.replay_gui import ReplayGUI
from police_thief.services.commit_reveal import LogEntry, commit

# tk_root/root fixtures live in tests/unit/conftest.py, shared across every
# GUI test file -- Tkinter does not reliably support creating more than one
# session-scoped Tk() root within a single process.


def _belief_peaked_at(grid_size: int, peak: Position) -> tuple[Board, BeliefMap]:
    board = Board(BoardConfig(grid_size=grid_size, max_barriers=14))
    scent = ScentField(grid_size=grid_size, config=ScentConfig())
    scent.emit(peak)
    belief = BeliefMap(board)
    belief.update_from_scent(scent)
    return board, belief


def test_live_gui_constructs_one_cell_rect_per_board_position(root):
    gui = LiveGUI(root, grid_size=7)
    assert len(gui._rects) == 49


def test_live_gui_render_updates_the_banner_text_and_color(root):
    board, belief = _belief_peaked_at(7, Position(5, 5))
    vm = build_live_view_model(Position(0, 0), belief, board, TurnState.YOUR_TURN)
    gui = LiveGUI(root, grid_size=7)
    gui.render(vm)
    assert gui.banner.cget("text") == "YOUR TURN"
    assert gui.banner.cget("fg") == "#2e7d32"


def test_live_gui_render_colors_the_belief_peak_cell(root):
    board, belief = _belief_peaked_at(7, Position(5, 5))
    vm = build_live_view_model(Position(0, 0), belief, board, TurnState.YOUR_TURN)
    gui = LiveGUI(root, grid_size=7)
    gui.render(vm)
    rect_id = gui._rects[(5, 5)]
    assert gui.canvas.itemcget(rect_id, "fill") == "#c80000"


def test_live_gui_render_outlines_only_the_own_position_cell(root):
    board, belief = _belief_peaked_at(7, Position(5, 5))
    vm = build_live_view_model(Position(2, 2), belief, board, TurnState.YOUR_TURN)
    gui = LiveGUI(root, grid_size=7)
    gui.render(vm)
    own_rect = gui._rects[(2, 2)]
    other_rect = gui._rects[(0, 0)]
    assert gui.canvas.itemcget(own_rect, "outline") == "#000000"
    assert gui.canvas.itemcget(other_rect, "outline") == "#cccccc"


def test_live_gui_locked_banner_renders_gray(root):
    board, belief = _belief_peaked_at(7, Position(5, 5))
    vm = build_live_view_model(Position(0, 0), belief, board, TurnState.LOCKED)
    gui = LiveGUI(root, grid_size=7)
    gui.render(vm)
    assert gui.banner.cget("text") == "LOCKED"
    assert gui.banner.cget("fg") == "#616161"


def test_live_gui_render_shows_a_barrier_cell_in_its_distinct_color(root):
    board, belief = _belief_peaked_at(7, Position(5, 5))
    board.place_barrier(Position(5, 4), Position(5, 5))
    vm = build_live_view_model(Position(0, 0), belief, board, TurnState.YOUR_TURN)
    gui = LiveGUI(root, grid_size=7)
    gui.render(vm)
    rect_id = gui._rects[(5, 5)]
    assert gui.canvas.itemcget(rect_id, "fill") == "#2b2b2b"


def test_live_gui_step_label_increments_on_every_render(root):
    board, belief = _belief_peaked_at(7, Position(5, 5))
    vm = build_live_view_model(Position(0, 0), belief, board, TurnState.YOUR_TURN)
    gui = LiveGUI(root, grid_size=7)
    assert gui.step_label.cget("text") == "Step 0"
    gui.render(vm)
    assert gui.step_label.cget("text") == "Step 1"
    gui.render(vm)
    assert gui.step_label.cget("text") == "Step 2"


def test_live_gui_draws_an_agent_marker_with_the_role_label(root):
    board, belief = _belief_peaked_at(7, Position(5, 5))
    vm = build_live_view_model(Position(2, 2), belief, board, TurnState.YOUR_TURN, role_label="C")
    gui = LiveGUI(root, grid_size=7)
    gui.render(vm)
    texts = [
        gui.canvas.itemcget(item, "text")
        for item in gui.canvas.find_all()
        if gui.canvas.type(item) == "text"
    ]
    assert "C" in texts


def test_live_gui_draws_a_trail_dot_for_each_visited_cell_except_the_current_one(root):
    board, belief = _belief_peaked_at(7, Position(5, 5))
    visited = frozenset({Position(0, 0), Position(1, 1), Position(2, 2)})  # includes own position
    vm = build_live_view_model(Position(2, 2), belief, board, TurnState.YOUR_TURN, visited=visited)
    gui = LiveGUI(root, grid_size=7)
    gui.render(vm)
    # 2 trail dots (own position excluded) + 1 agent marker (oval + text) = 4 marker ids
    assert len(gui.canvas._marker_ids) == 4


def test_live_gui_clears_previous_markers_on_re_render_rather_than_accumulating(root):
    board, belief = _belief_peaked_at(7, Position(5, 5))
    vm = build_live_view_model(
        Position(2, 2), belief, board, TurnState.YOUR_TURN, visited=frozenset({Position(0, 0)})
    )
    gui = LiveGUI(root, grid_size=7)
    gui.render(vm)
    first_count = len(gui.canvas._marker_ids)
    gui.render(vm)
    assert len(gui.canvas._marker_ids) == first_count


def _make_entries(n: int) -> list[LogEntry]:
    entries = []
    for i in range(n):
        c = commit(state={"turn": i}, move="N", intent=True)
        entries.append(
            LogEntry(state={"turn": i}, move="N", intent=True, nonce=c.nonce, h_commit=c.h_commit)
        )
    return entries


def test_replay_gui_shows_step_one_of_n_on_construction(root):
    session = ReplaySession(_make_entries(5))
    gui = ReplayGUI(root, session)
    assert gui.step_label.cget("text") == "Step 1 / 5"


def test_replay_gui_shows_verified_ok_in_green_on_a_clean_log(root):
    session = ReplaySession(_make_entries(3))
    gui = ReplayGUI(root, session)
    assert gui.status_label.cget("text") == "Verified OK"
    assert gui.status_label.cget("fg") == "#2e7d32"


def test_replay_gui_shows_tampered_in_red_at_the_tampered_step(root):
    entries = _make_entries(4)
    tampered = list(entries)
    tampered[1] = dataclasses.replace(tampered[1], move="TAMPERED")
    session = ReplaySession(tampered)
    gui = ReplayGUI(root, session)
    gui.next_button.invoke()  # advance to step index 1 (the tampered one)
    assert gui.status_label.cget("text") == "TAMPERED"
    assert gui.status_label.cget("fg") == "#c62828"


def test_replay_gui_next_button_advances_the_step_label(root):
    session = ReplaySession(_make_entries(4))
    gui = ReplayGUI(root, session)
    gui.next_button.invoke()
    assert gui.step_label.cget("text") == "Step 2 / 4"


def test_replay_gui_previous_button_retreats_the_step_label(root):
    session = ReplaySession(_make_entries(4))
    gui = ReplayGUI(root, session)
    gui.next_button.invoke()
    gui.next_button.invoke()
    gui.prev_button.invoke()
    assert gui.step_label.cget("text") == "Step 2 / 4"


def test_replay_gui_detail_label_reflects_the_current_steps_move(root):
    session = ReplaySession(_make_entries(2))
    gui = ReplayGUI(root, session)
    assert "move='N'" in gui.detail_label.cget("text")


def test_replay_gui_summary_label_shows_verified_and_tampered_counts(root):
    entries = _make_entries(5)
    tampered = list(entries)
    tampered[2] = dataclasses.replace(tampered[2], move="X")
    session = ReplaySession(tampered)
    gui = ReplayGUI(root, session)
    assert gui.summary_label.cget("text") == "2 verified / 3 tampered (of 5 total steps)"


def _make_positional_entries(coords: list[tuple[int, int]]) -> list[LogEntry]:
    entries = []
    for row, col in coords:
        c = commit(state={"row": row, "col": col}, move="N", intent=True)
        entries.append(
            LogEntry(
                state={"row": row, "col": col},
                move="N",
                intent=True,
                nonce=c.nonce,
                h_commit=c.h_commit,
            )
        )
    return entries


def test_replay_gui_draws_no_board_markers_for_an_unrecognized_state_shape(root):
    """T0431's own resolution: LogEntry.state stays intentionally generic --
    a shape this GUI doesn't recognize (e.g. the synthetic {"turn": i} used
    elsewhere in this file) means "nothing to draw," never a crash."""
    session = ReplaySession(_make_entries(3))
    gui = ReplayGUI(root, session)
    assert gui.canvas._marker_ids == []


def test_replay_gui_draws_an_agent_marker_for_a_recognized_row_col_state(root):
    session = ReplaySession(_make_positional_entries([(0, 0), (0, 1), (1, 1)]))
    gui = ReplayGUI(root, session)
    assert len(gui.canvas._marker_ids) == 2  # just the agent marker (oval + text) at step 1


def test_replay_gui_accumulates_a_trail_as_steps_advance(root):
    session = ReplaySession(_make_positional_entries([(0, 0), (0, 1), (1, 1)]))
    gui = ReplayGUI(root, session)
    gui.next_button.invoke()
    gui.next_button.invoke()
    # 2 trail dots (steps 1-2) + 1 agent marker (oval + text) at step 3
    assert len(gui.canvas._marker_ids) == 4


def test_replay_gui_play_button_starts_paused(root):
    session = ReplaySession(_make_entries(3))
    gui = ReplayGUI(root, session)
    assert gui.play_button.cget("text") == "Play"
    assert gui._playing is False


def test_replay_gui_play_button_toggles_to_pause_and_back(root):
    session = ReplaySession(_make_entries(3))
    gui = ReplayGUI(root, session)
    gui.play_button.invoke()
    assert gui.play_button.cget("text") == "Pause"
    assert gui._playing is True
    gui.play_button.invoke()
    assert gui.play_button.cget("text") == "Play"
    assert gui._playing is False


def test_replay_gui_auto_play_advances_through_every_step_then_stops(root, monkeypatch):
    session = ReplaySession(_make_entries(4))
    gui = ReplayGUI(root, session)
    scheduled: list = []
    monkeypatch.setattr(tk.Misc, "after", lambda self, ms, func: scheduled.append(func))

    gui.play_button.invoke()
    assert gui.step_label.cget("text") == "Step 2 / 4"
    while scheduled:
        scheduled.pop(0)()
    assert gui.step_label.cget("text") == "Step 4 / 4"
    assert gui.play_button.cget("text") == "Play"  # auto-stopped at the end
    assert gui._playing is False


def test_replay_gui_a_stale_scheduled_tick_after_pause_does_nothing(root, monkeypatch):
    """`after()` isn't cancelled on pause -- a tick already scheduled before
    the user paused can still fire. It must be a no-op, not silently
    resume/advance the replay."""
    session = ReplaySession(_make_entries(4))
    gui = ReplayGUI(root, session)
    scheduled: list = []
    monkeypatch.setattr(tk.Misc, "after", lambda self, ms, func: scheduled.append(func))

    gui.play_button.invoke()  # schedules exactly one stale tick
    stale_tick = scheduled.pop()
    gui.play_button.invoke()  # pause before that tick fires
    assert gui._playing is False

    stale_tick()  # the stale, already-scheduled callback fires late
    assert gui.step_label.cget("text") == "Step 2 / 4"  # unchanged by the stale tick
    assert gui._playing is False


def test_replay_gui_previous_button_stops_auto_play(root, monkeypatch):
    session = ReplaySession(_make_entries(4))
    gui = ReplayGUI(root, session)
    monkeypatch.setattr(tk.Misc, "after", lambda self, ms, func: None)
    gui.play_button.invoke()
    assert gui._playing is True
    gui.prev_button.invoke()
    assert gui._playing is False
    assert gui.play_button.cget("text") == "Play"


def test_replay_gui_jump_to_step_moves_directly_to_the_requested_step(root):
    session = ReplaySession(_make_entries(10))
    gui = ReplayGUI(root, session)
    gui.jump_entry.insert(0, "7")
    gui.jump_button.invoke()
    assert gui.step_label.cget("text") == "Step 7 / 10"


def test_replay_gui_jump_to_step_clamps_an_out_of_range_target(root):
    session = ReplaySession(_make_entries(5))
    gui = ReplayGUI(root, session)
    gui.jump_entry.insert(0, "999")
    gui.jump_button.invoke()
    assert gui.step_label.cget("text") == "Step 5 / 5"


def test_replay_gui_jump_to_step_ignores_non_numeric_input_without_crashing(root):
    session = ReplaySession(_make_entries(5))
    gui = ReplayGUI(root, session)
    gui.jump_entry.insert(0, "not-a-number")
    gui.jump_button.invoke()  # must not raise
    assert gui.step_label.cget("text") == "Step 1 / 5"
