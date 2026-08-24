"""Widget construction for the distributed-match command center.

Split out of `network_match_app.py` so the 65-line `_build` tree lives
apart from the threading, serving and event-drain logic it decorates.
Mixed in rather than made a collaborator so `NetworkMatchApp` keeps
`self.shell`/`self.settings` attribute access and its own method names.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from police_thief.gui.theme import COLORS, FONT, MONO_FONT

__all__ = ["NetworkMatchLayoutMixin"]


class NetworkMatchLayoutMixin:
    """Builds the static widget tree onto `self.shell`."""

    def _build(self) -> None:
        header = ttk.Frame(self.shell, style="App.TFrame")
        header.pack(fill="x", pady=(0, 18))
        title = ttk.Frame(header, style="App.TFrame")
        title.pack(side="left")
        ttk.Label(title, text="SHADOWGRID", style="Title.TLabel").pack(anchor="w")
        ttk.Label(title, text="DISTRIBUTED MCP ARENA", style="Subtitle.TLabel").pack(anchor="w")
        self.new_game_button = ttk.Button(
            header,
            text="NEW GAME",
            style="Secondary.TButton",
            command=self._new_game,
        )
        self.new_game_button.pack(side="right")

        cards = ttk.Frame(self.shell, style="App.TFrame")
        cards.pack(fill="x")
        for label, value in (
            ("ROLE", self.settings.role.value.upper()),
            ("LOCAL ENDPOINT", f"0.0.0.0:{self.settings.local_port}/mcp"),
            ("GAME", f"{self.settings.game_id} / G{self.settings.sub_game_number:02d}"),
        ):
            card = ttk.Frame(cards, style="Card.TFrame", padding=14)
            card.pack(side="left", fill="x", expand=True, padx=5)
            ttk.Label(card, text=label, style="CardText.TLabel").pack(anchor="w")
            ttk.Label(card, text=value, style="CardTitle.TLabel").pack(anchor="w", pady=(4, 0))

        endpoint = ttk.Frame(self.shell, style="Card.TFrame", padding=18)
        endpoint.pack(fill="x", pady=16)
        ttk.Label(endpoint, text="PEER ROUTING", style="CardTitle.TLabel").pack(anchor="w")
        for caption, value in (
            ("SHARE WITH OPPONENT", self.settings.public_url),
            ("OPPONENT URL", self.settings.opponent_url),
        ):
            tk.Label(
                endpoint,
                text=f"{caption:<22} {value}",
                bg=COLORS["surface"],
                fg=COLORS["accent"],
                font=(MONO_FONT, 9),
                anchor="w",
            ).pack(fill="x", pady=(8, 0))

        console = ttk.Frame(self.shell, style="Card.TFrame", padding=18)
        console.pack(fill="both", expand=True)
        ttk.Label(console, text="SECURE MATCH TELEMETRY", style="CardTitle.TLabel").pack(anchor="w")
        self.status = tk.Label(
            console,
            text="INITIALIZING PEER",
            bg=COLORS["surface"],
            fg=COLORS["warning"],
            font=(FONT, 11, "bold"),
            anchor="w",
        )
        self.status.pack(fill="x", pady=(8, 10))
        self.log = tk.Text(
            console,
            bg=COLORS["surface_alt"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            state="disabled",
            font=(MONO_FONT, 9),
            padx=12,
            pady=12,
            height=14,
        )
        self.log.pack(fill="both", expand=True)
