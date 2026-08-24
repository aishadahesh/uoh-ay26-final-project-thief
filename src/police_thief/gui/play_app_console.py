"""The movement console: direction pad, barrier toggle and hint readout.

Split out of play_app_layout.py, which was still over the 150-line
guideline after `_build_ui` came out of `PlayApp.__init__`. Moved verbatim;
`_build_ui` now calls `_build_console(sidebar)` as its last step.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from police_thief.domain.board import Move
from police_thief.gui.play_app_layout import _DIRECTIONS, _KEY_MOVES
from police_thief.gui.theme import COLORS, FONT, MONO_FONT

__all__ = ["_ConsoleMixin"]


class _ConsoleMixin:
    """Builds the sidebar's movement console."""

    def _build_console(self, sidebar: ttk.Frame) -> None:
        ttk.Label(sidebar, text="MOVEMENT CONSOLE", style="CardTitle.TLabel").pack(anchor="w")
        pad = ttk.Frame(sidebar, style="Card.TFrame")
        pad.pack(pady=10)
        self.move_buttons: dict[Move, tk.Button] = {}
        positions = {
            Move.NORTH: (0, 1),
            Move.WEST: (1, 0),
            Move.STAY: (1, 1),
            Move.EAST: (1, 2),
            Move.SOUTH: (2, 1),
        }
        for label, move_name, icon in _DIRECTIONS:
            move = Move[move_name]
            button = tk.Button(
                pad,
                text=f"{icon}\n{label}",
                width=7,
                bg=COLORS["surface_alt"],
                fg=COLORS["text"],
                activebackground=COLORS["border"],
                activeforeground=COLORS["text"],
                disabledforeground=COLORS["muted"],
                relief="flat",
                bd=0,
                padx=7,
                pady=7,
                font=(FONT, 9, "bold"),
                command=lambda m=move: self._on_human_move(m),
            )
            button.grid(row=positions[move][0], column=positions[move][1], padx=3, pady=3)
            self.move_buttons[move] = button

        self.barrier_button = tk.Button(
            sidebar,
            text="＋  DEPLOY BARRIER",
            bg=COLORS["accent"],
            fg=COLORS["bg"],
            activebackground=COLORS["accent_hover"],
            activeforeground=COLORS["bg"],
            disabledforeground=COLORS["muted"],
            relief="flat",
            bd=0,
            padx=12,
            pady=10,
            font=(FONT, 10, "bold"),
            command=self._toggle_barrier_mode,
        )
        self.barrier_button.pack(fill="x", pady=(12, 8))
        self.hint_label = tk.Label(
            sidebar,
            text="ARROWS move  •  SPACE holds\nB toggles barrier placement",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(MONO_FONT, 8),
            justify="left",
        )
        self.hint_label.pack(anchor="w", pady=(10, 0))
        for sequence, move in _KEY_MOVES.items():
            self.master.bind(sequence, lambda _event, m=move: self._on_human_move(m))
        self.master.bind("b", lambda _event: self._toggle_barrier_mode())
