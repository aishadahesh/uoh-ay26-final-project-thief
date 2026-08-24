"""The setup dialog's form rows and action buttons.

Split out of network_setup.py: `NetworkSetupDialog.__init__` was 154 lines,
of which everything after the window and variable setup was one flat run of
row construction. Moved verbatim into `_build_form`, which `__init__` now
calls as its last step.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from police_thief.gui.theme import COLORS, FONT

__all__ = ["_BuildFormMixin"]


class _BuildFormMixin:
    """Lays out every labelled row and the dialog's buttons."""

    def _build_form(self, shell: ttk.Frame) -> None:
        self._fixed_row(shell, "This computer's role", "role")
        self._row(shell, "Local MCP port", "port")
        self._row(shell, "Opponent public URL (must end /mcp)", "opponent")
        self._row(shell, "This peer's public tunnel URL", "public")
        self._row(shell, "Shared game ID", "game")
        self._row(shell, "Sub-game number", "subgame")
        self._section_label(shell, "TEAM 1 - THIS COMPUTER")
        self._row(shell, "Team 1 name", "team1_name")
        self._row(shell, "Team 1 - member 1", "team1_member1")
        self._row(shell, "Team 1 - member 2", "team1_member2")
        self._row(shell, "Team 1 Cop / Thief repository URLs", "own_cop", second_key="own_thief")
        self._section_label(shell, "TEAM 2 - OPPONENT")
        self._row(shell, "Team 2 name", "team2_name")
        self._row(shell, "Team 2 - member 1", "team2_member1")
        self._row(shell, "Team 2 - member 2", "team2_member2")
        self._row(
            shell,
            "Team 2 Cop / Thief repository URLs",
            "opponent_cop",
            second_key="opponent_thief",
        )
        self._row(shell, "Shared match secret (same on both computers)", "secret", secret=True)
        self._row(shell, "JSON output directory", "output")
        tk.Checkbutton(
            shell,
            text="Automatically email result JSON after mutual match completion",
            variable=self.vars["email"],
            bg=COLORS["bg"],
            fg=COLORS["text"],
            selectcolor=COLORS["surface_alt"],
            activebackground=COLORS["bg"],
            activeforeground=COLORS["text"],
            font=(FONT, 9),
            command=self._toggle_email,
        ).pack(anchor="w", pady=12)
        ttk.Label(shell, text="Result email recipient", style="Subtitle.TLabel").pack(
            anchor="w",
            pady=(0, 3),
        )
        self.email_entry = tk.Entry(
            shell,
            textvariable=self.vars["email_recipient"],
            bg=COLORS["surface_alt"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            font=(FONT, 10),
            disabledbackground=COLORS["surface"],
            disabledforeground=COLORS["muted"],
        )
        self.email_entry.pack(fill="x", ipady=5)
        self._toggle_email()
        tk.Label(
            shell,
            text="Run an ngrok/Localtonet tunnel to the local port. Give your public /mcp URL to the opponent, and paste their URL above.",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            wraplength=650,
            justify="left",
            padx=14,
            pady=12,
        ).pack(fill="x", pady=(6, 18))
        buttons = ttk.Frame(shell, style="App.TFrame")
        buttons.pack(fill="x")
        ttk.Button(buttons, text="CANCEL", style="Secondary.TButton", command=self._close).pack(
            side="left"
        )
        self.start_button = ttk.Button(
            buttons, text="START NETWORK PEER →", style="Accent.TButton", command=self._start
        )
        self.start_button.pack(side="right")
        self.window.update_idletasks()
        self.window.deiconify()
        self.window.lift()
        self.window.grab_set()
