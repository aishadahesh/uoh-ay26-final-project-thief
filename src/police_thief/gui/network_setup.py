"""Configuration dialog for cross-computer Agent-vs-Agent matches."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from police_thief.gui.network_setup_fields import _BuildFormMixin
from police_thief.gui.network_setup_form import _FormMixin
from police_thief.gui.network_setup_start import _StartMixin
from police_thief.gui.theme import COLORS, configure_window, install_styles
from police_thief.services.network_match import NetworkMatchSettings
from police_thief.services.network_match_config import (
    DEFAULT_REPORT_EMAIL,
    load_network_defaults,
    validate_mcp_url,
)

__all__ = [
    "DEFAULT_REPORT_EMAIL", "NetworkSetupDialog", "load_network_defaults", "validate_mcp_url",
]


class NetworkSetupDialog(_BuildFormMixin, _FormMixin, _StartMixin):
    def __init__(self, master: tk.Misc, project_root: Path) -> None:
        self.project_root = project_root
        defaults_path = project_root / "config" / "network_match.json"
        try:
            defaults = load_network_defaults(defaults_path, project_root)
        except (OSError, ValueError) as exc:
            messagebox.showwarning(
                "Network defaults",
                f"{exc}\n\nBuilt-in defaults will be used.",
                parent=master,
            )
            defaults = {}
        self.result: NetworkMatchSettings | None = None
        self.window = tk.Toplevel(master)
        configure_window(self.window, title="ShadowGrid | Network Match", min_size=(660, 560))
        install_styles(self.window)
        screen_height = self.window.winfo_screenheight()
        window_height = min(820, max(600, screen_height - 120))
        self.window.geometry(f"800x{window_height}")
        self.vars = {
            "role": tk.StringVar(value=defaults.get("role", "thief")),
            "port": tk.StringVar(value=defaults.get("port", "8802")),
            "opponent": tk.StringVar(
                value=defaults.get("opponent", "https://opponent.example/mcp")
            ),
            "public": tk.StringVar(value=defaults.get("public", "https://your-tunnel.example/mcp")),
            "game": tk.StringVar(value=defaults.get("game", "G001")),
            "subgame": tk.StringVar(value=defaults.get("subgame", "1")),
            "output": tk.StringVar(
                value=defaults.get("output", str(project_root / "results" / "network"))
            ),
            "team1_name": tk.StringVar(value=defaults.get("team1_name", "")),
            "team1_member1": tk.StringVar(value=defaults.get("team1_member1", "")),
            "team1_member2": tk.StringVar(value=defaults.get("team1_member2", "")),
            "team2_name": tk.StringVar(value=defaults.get("team2_name", "")),
            "team2_member1": tk.StringVar(value=defaults.get("team2_member1", "")),
            "team2_member2": tk.StringVar(value=defaults.get("team2_member2", "")),
            "own_cop": tk.StringVar(value=defaults.get("own_cop", "")),
            "own_thief": tk.StringVar(value=defaults.get("own_thief", "")),
            "opponent_cop": tk.StringVar(value=defaults.get("opponent_cop", "")),
            "opponent_thief": tk.StringVar(value=defaults.get("opponent_thief", "")),
            "secret": tk.StringVar(value=defaults.get("secret", "")),
            "email": tk.BooleanVar(value=defaults.get("email", False)),
            "email_recipient": tk.StringVar(
                value=defaults.get("email_recipient", DEFAULT_REPORT_EMAIL),
            ),
        }
        viewport = tk.Frame(self.window, bg=COLORS["bg"])
        viewport.pack(fill="both", expand=True)
        canvas = tk.Canvas(
            viewport,
            bg=COLORS["bg"],
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        shell = ttk.Frame(canvas, style="App.TFrame", padding=28)
        shell_window = canvas.create_window((0, 0), window=shell, anchor="nw")

        def resize_content(_event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def resize_width(event) -> None:
            canvas.itemconfigure(shell_window, width=event.width)

        def scroll(event) -> None:
            canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

        shell.bind("<Configure>", resize_content)
        canvas.bind("<Configure>", resize_width)
        self.window.bind_all("<MouseWheel>", scroll)
        self.window.protocol("WM_DELETE_WINDOW", self._close)
        ttk.Label(shell, text="NETWORK MATCH", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            shell, text="TWO COMPUTERS  •  FASTMCP  •  SIGNED MOVES", style="Subtitle.TLabel"
        ).pack(anchor="w", pady=(0, 18))
        self._build_form(shell)

    def _close(self) -> None:
        self.window.unbind_all("<MouseWheel>")
        if self.window.grab_current() is self.window:
            self.window.grab_release()
        self.window.destroy()






    def show(self) -> NetworkMatchSettings | None:
        self.window.wait_window()
        return self.result
