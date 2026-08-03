"""The Replay Viewer: scrubbing controls + cryptographic verification stamp
(Chapter 7, Sec. 7.4-7.5).

Thin wiring only -- every verification decision already happened in
domain/replay.py::ReplaySession (which itself reuses Chapter 5's audit_log).
This class just displays "VERIFIED OK" (green) or "TAMPERED" (red) per
step and lets a human scrub forward/backward/auto-play/jump; it recomputes
no cryptography of its own.

Also renders a best-effort board view: `LogEntry.state` is intentionally
generic (Any) at the crypto layer (see domain/replay.py's own docstring),
so this recognizes only the one concrete shape this project's Orchestrator
(Chapter 8) actually produces -- `{"row": int, "col": int}` -- and silently
skips board drawing for any other shape (e.g. the synthetic states used in
several unit tests) rather than guessing or crashing. This closes
docs/tasks.md T0431 ("visual replay of board state alongside the
verification stamps"), previously deferred for exactly this genericness
reason.
"""

from __future__ import annotations

import tkinter as tk
from typing import Any

from police_thief.domain.replay import VERIFIED_OK, ReplaySession
from police_thief.gui.board_canvas import BoardCanvas
from police_thief.gui.theme import COLORS, FONT, MONO_FONT, configure_window, install_styles

_STATUS_COLOR = {VERIFIED_OK: "#2e7d32", "TAMPERED": "#c62828"}  # green / red
_STATUS_TEXT = {VERIFIED_OK: "Verified OK", "TAMPERED": "TAMPERED"}
_DEFAULT_GRID_SIZE = 7
_PLAYBACK_DELAY_MS = 500
_TRAIL_DOT_COLOR = "#9e9e9e"
_MARKER_FILL = "#6a1b9a"
_MARKER_LABEL = "•"


def _extract_position(state: Any) -> tuple[int, int] | None:
    """Recognize only `{"row": int, "col": int}` -- any other shape means
    "nothing to draw here", never a guess."""
    if (
        isinstance(state, dict)
        and isinstance(state.get("row"), int)
        and isinstance(state.get("col"), int)
    ):
        return state["row"], state["col"]
    return None


class ReplayGUI:
    """Prev/Next/Play-driven scrubber over a ReplaySession, with a status stamp."""

    def __init__(
        self, master: tk.Misc, session: ReplaySession, grid_size: int = _DEFAULT_GRID_SIZE
    ) -> None:
        self.master = master
        self.session = session
        self._playing = False

        configure_window(master, title="ShadowGrid | Integrity Replay", min_size=(760, 560))
        install_styles(master)
        master.configure(bg=COLORS["bg"])
        tk.Label(
            master,
            text="INTEGRITY REPLAY",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=(FONT, 19, "bold"),
        ).pack(anchor="w", padx=24, pady=(20, 0))
        tk.Label(
            master,
            text="CRYPTOGRAPHIC WITNESS  •  COMMIT / REVEAL AUDIT",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(FONT, 9),
        ).pack(anchor="w", padx=24)

        self.step_label = tk.Label(
            master, bg=COLORS["bg"], fg=COLORS["muted"], font=(FONT, 11, "bold")
        )
        self.step_label.pack(pady=(14, 0))
        self.status_label = tk.Label(master, bg=COLORS["bg"], font=(FONT, 16, "bold"))
        self.status_label.pack(pady=(2, 8))

        self.canvas = BoardCanvas(master, grid_size)
        self.canvas.pack()

        self.detail_label = tk.Label(
            master,
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=(MONO_FONT, 9),
            justify="left",
            padx=16,
            pady=10,
        )
        self.detail_label.pack(fill="x", padx=24, pady=10)

        buttons = tk.Frame(master)
        buttons.pack()
        self.prev_button = tk.Button(buttons, text="< Previous", command=self._on_previous)
        self.prev_button.pack(side="left")
        self.play_button = tk.Button(buttons, text="Play", command=self._on_toggle_play)
        self.play_button.pack(side="left", padx=6)
        self.next_button = tk.Button(buttons, text="Next >", command=self._on_next)
        self.next_button.pack(side="left")

        jump_bar = tk.Frame(master)
        jump_bar.pack()
        tk.Label(jump_bar, text="Go to step:").pack(side="left")
        self.jump_entry = tk.Entry(jump_bar, width=5)
        self.jump_entry.pack(side="left")
        self.jump_button = tk.Button(jump_bar, text="Go", command=self._on_jump)
        self.jump_button.pack(side="left", padx=6)

        self.summary_label = tk.Label(master, bg=COLORS["bg"], fg=COLORS["muted"], font=(FONT, 9))
        self.summary_label.pack()
        self.summary_label.config(
            text=f"{session.verified_count} verified / {session.tampered_count} tampered "
            f"(of {session.total_steps} total steps)"
        )

        self._render_current()

    def _on_previous(self) -> None:
        self._stop_playing()
        self.session.previous()
        self._render_current()

    def _on_next(self) -> None:
        self.session.next()
        self._render_current()
        if self._playing and self.session.current_step.index >= self.session.total_steps - 1:
            self._stop_playing()

    def _stop_playing(self) -> None:
        self._playing = False
        self.play_button.config(text="Play")

    def _on_toggle_play(self) -> None:
        self._playing = not self._playing
        self.play_button.config(text="Pause" if self._playing else "Play")
        if self._playing:
            self._tick()

    def _tick(self) -> None:
        if not self._playing:
            return
        self._on_next()
        if self._playing:
            self.master.after(_PLAYBACK_DELAY_MS, self._tick)

    def _on_jump(self) -> None:
        try:
            target = int(self.jump_entry.get()) - 1
        except ValueError:
            return
        target = max(0, min(target, self.session.total_steps - 1))
        self._stop_playing()
        self.session.jump_to(target)
        self._render_current()

    def _render_current(self) -> None:
        step = self.session.current_step
        self.step_label.config(text=f"Step {step.index + 1} / {self.session.total_steps}")
        self.status_label.config(text=_STATUS_TEXT[step.status], fg=_STATUS_COLOR[step.status])
        self.detail_label.config(
            text=f"move={step.entry.move!r}\nintent={step.entry.intent!r}\nh_commit={step.entry.h_commit[:16]}..."
        )
        self._render_board(step.index)

    def _render_board(self, current_index: int) -> None:
        self.canvas.clear_markers()
        trail = [
            pos
            for entry in self.session.entries[: current_index + 1]
            if (pos := _extract_position(entry.state)) is not None
        ]
        for row, col in trail[:-1]:
            self.canvas.draw_dot(row, col, _TRAIL_DOT_COLOR)
        if trail:
            self.canvas.draw_agent(*trail[-1], _MARKER_LABEL, _MARKER_FILL)
