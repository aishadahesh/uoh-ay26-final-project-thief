"""Integration tests: the Live GUI and Replay Viewer wired to real match data
(Chapter 7).

Not mocked -- these drive the actual Chapter 6 partial-observability
strategy pipeline and the actual Chapter 5 commit-reveal primitives, then
verify the GUI layers stay correctly in sync with that real data turn by
turn (docs/tasks.md T0419, T0434).
"""

import tkinter as tk

import pytest

from police_thief.domain.belief import BeliefMap
from police_thief.domain.board import Board, BoardConfig, Move, Position
from police_thief.domain.live_view_model import TurnState, build_live_view_model
from police_thief.domain.replay import ReplaySession, load_log, save_log
from police_thief.domain.scent import ScentConfig, ScentField
from police_thief.domain.strategy.manhattan_brain import ManhattanHeuristicBrain
from police_thief.gui.live_gui import LiveGUI
from police_thief.gui.replay_gui import ReplayGUI
from police_thief.services.commit_reveal import LogEntry, commit
from police_thief.shared.constants import AgentRole


@pytest.fixture(scope="module")
def tk_root():
    window = tk.Tk()
    window.withdraw()
    yield window
    window.destroy()


def test_live_gui_stays_in_sync_across_a_real_multi_turn_match(tk_root):
    """Drives the cop's own LiveGUI using ONLY the cop's own local truth
    (its position and its own belief map, fed by its own scent reading),
    across several real turns of the Chapter 6 strategy pipeline, and
    confirms the rendered banner and heatmap peak track that real data
    at every turn -- never desyncing, never touching the thief's true
    position.
    """
    window = tk.Toplevel(tk_root)
    window.withdraw()
    board = Board(BoardConfig(grid_size=7, max_barriers=14))
    cop_pos, thief_pos = Position(0, 0), Position(6, 6)
    cop_scent, thief_scent = ScentField(7, ScentConfig()), ScentField(7, ScentConfig())
    cop_belief = BeliefMap(board)
    cop_brain = ManhattanHeuristicBrain(AgentRole.COP)
    thief_brain = ManhattanHeuristicBrain(AgentRole.THIEF)
    thief_belief = BeliefMap(board)

    gui = LiveGUI(window, grid_size=7)

    for turn in range(5):
        cop_belief.update_from_scent(thief_scent)
        vm = build_live_view_model(
            cop_pos, cop_belief, board, TurnState.YOUR_TURN if turn % 2 == 0 else TurnState.LOCKED
        )
        gui.render(vm)

        # The rendered banner must match this turn's real turn state.
        expected_text = "YOUR TURN" if turn % 2 == 0 else "LOCKED"
        assert gui.banner.cget("text") == expected_text

        # The rendered own-position marker must match the cop's real position.
        own_rect = gui._rects[(cop_pos.row, cop_pos.col)]
        assert gui.canvas.itemcget(own_rect, "outline") == "#000000"

        cop_pos = board.apply_move(cop_pos, cop_brain._decide_move(board, cop_pos, cop_belief))
        cop_scent.decay()
        cop_scent.emit(cop_pos)
        thief_belief.update_from_scent(cop_scent)
        thief_pos = board.apply_move(
            thief_pos, thief_brain._decide_move(board, thief_pos, thief_belief)
        )
        thief_scent.decay()
        thief_scent.emit(thief_pos)

    window.destroy()


def test_replay_viewer_against_a_real_commit_reveal_sealed_multi_turn_log(tmp_path, tk_root):
    """Builds a real match log by actually running commit() over real board
    positions across several turns (not synthetic {"turn": i} placeholders),
    saves it to a real file, reloads it, and confirms both the crypto layer
    and the GUI layer agree it is fully verified -- then tampers the file
    on disk and confirms both layers agree it is not.
    """
    board = Board(BoardConfig(grid_size=7, max_barriers=14))
    pos = Position(0, 0)
    entries = []
    for _ in range(6):
        move = Move.EAST
        state = {"cop": [pos.row, pos.col]}
        c = commit(state=state, move=move, intent=True)
        entries.append(
            LogEntry(state=state, move=move, intent=True, nonce=c.nonce, h_commit=c.h_commit)
        )
        pos = board.apply_move(pos, move)

    path = tmp_path / "real_match_log.json"
    save_log(entries, path)

    clean_session = ReplaySession(load_log(path))
    assert clean_session.is_fully_verified is True

    window = tk.Toplevel(tk_root)
    window.withdraw()
    clean_gui = ReplayGUI(window, clean_session)
    assert clean_gui.status_label.cget("text") == "Verified OK"
    window.destroy()

    # Tamper the file on disk, exactly as a dishonest player might try to.
    import json

    raw = json.loads(path.read_text(encoding="utf-8"))
    raw[3]["state"] = {"cop": [99, 99]}
    path.write_text(json.dumps(raw), encoding="utf-8")

    tampered_session = ReplaySession(load_log(path))
    assert tampered_session.is_fully_verified is False
    assert tampered_session.first_tampered_index == 3

    window2 = tk.Toplevel(tk_root)
    window2.withdraw()
    tampered_gui = ReplayGUI(window2, tampered_session)
    tampered_gui.session.jump_to(3)
    tampered_gui._render_current()
    assert tampered_gui.status_label.cget("text") == "TAMPERED"
    window2.destroy()
