"""Shared visual language for the Police-Thief desktop interfaces."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

COLORS = {
    "bg": "#07111f",
    "surface": "#0d1b2d",
    "surface_alt": "#12243a",
    "border": "#233b57",
    "text": "#eaf2ff",
    "muted": "#8da4bf",
    "accent": "#22d3ee",
    "accent_hover": "#67e8f9",
    "cop": "#2563eb",
    "thief": "#f43f5e",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "cell": "#f8fafc",
    "grid": "#cbd5e1",
    "barrier": "#1e293b",
}

FONT = "Segoe UI"
MONO_FONT = "Cascadia Mono"


def configure_window(window: tk.Misc, *, title: str, min_size: tuple[int, int]) -> None:
    """Apply consistent window-level behavior without assuming a concrete root type."""
    window.winfo_toplevel().title(title)
    window.winfo_toplevel().configure(bg=COLORS["bg"])
    window.winfo_toplevel().minsize(*min_size)


def install_styles(master: tk.Misc) -> ttk.Style:
    """Install the shared ttk theme and return it for optional local extensions."""
    style = ttk.Style(master)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    style.configure("App.TFrame", background=COLORS["bg"])
    style.configure("Card.TFrame", background=COLORS["surface"])
    style.configure("Surface.TFrame", background=COLORS["surface_alt"])
    style.configure(
        "Title.TLabel",
        background=COLORS["bg"],
        foreground=COLORS["text"],
        font=(FONT, 22, "bold"),
    )
    style.configure(
        "Subtitle.TLabel",
        background=COLORS["bg"],
        foreground=COLORS["muted"],
        font=(FONT, 10),
    )
    style.configure(
        "CardTitle.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["text"],
        font=(FONT, 11, "bold"),
    )
    style.configure(
        "CardText.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["muted"],
        font=(FONT, 9),
    )
    style.configure(
        "Telemetry.TLabel",
        background=COLORS["surface_alt"],
        foreground=COLORS["text"],
        font=(MONO_FONT, 10, "bold"),
        padding=(10, 7),
    )
    style.configure(
        "Accent.TButton",
        background=COLORS["accent"],
        foreground=COLORS["bg"],
        font=(FONT, 10, "bold"),
        padding=(14, 9),
        borderwidth=0,
    )
    style.map(
        "Accent.TButton",
        background=[("active", COLORS["accent_hover"]), ("disabled", COLORS["border"])],
        foreground=[("disabled", COLORS["muted"])],
    )
    style.configure(
        "Secondary.TButton",
        background=COLORS["surface_alt"],
        foreground=COLORS["text"],
        font=(FONT, 9, "bold"),
        padding=(11, 8),
        borderwidth=1,
    )
    style.map(
        "Secondary.TButton",
        background=[("active", COLORS["border"]), ("disabled", COLORS["surface"])],
        foreground=[("disabled", COLORS["muted"])],
    )
    return style
