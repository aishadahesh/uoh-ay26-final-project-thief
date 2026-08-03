"""Interactive command-center GUI for local Police-Thief matches."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from contextlib import suppress
from tkinter import messagebox, ttk

from police_thief.domain.board import Move, MoveRejectedError, Position
from police_thief.domain.interactive_match import MODE_LABELS, InteractiveMatch
from police_thief.domain.live_view_model import TurnState, build_live_view_model
from police_thief.domain.scoring import MatchOutcome
from police_thief.gui.board_canvas import BoardCanvas
from police_thief.gui.theme import COLORS, FONT, MONO_FONT, configure_window, install_styles
from police_thief.services.gemini_agent import GeminiAgentAdvisor, TacticalContext
from police_thief.shared.constants import AgentRole

AGENT_MOVE_DELAY_MS = 500
_ROLE_LABEL = {AgentRole.COP: "C", AgentRole.THIEF: "T"}
_ROLE_FILL = {AgentRole.COP: COLORS["cop"], AgentRole.THIEF: COLORS["thief"]}
_BARRIER_COLOR = COLORS["barrier"]
_DIRECTIONS = [
    ("N", "NORTH", "↑"),
    ("S", "SOUTH", "↓"),
    ("E", "EAST", "→"),
    ("W", "WEST", "←"),
    ("HOLD", "STAY", "•"),
]
_KEY_MOVES = {
    "<Up>": Move.NORTH,
    "<Down>": Move.SOUTH,
    "<Right>": Move.EAST,
    "<Left>": Move.WEST,
    "<space>": Move.STAY,
}
_OUTCOME_TEXT = {MatchOutcome.CAPTURE: "Capture!", MatchOutcome.SURVIVAL: "The thief survives!"}


class PlayApp:
    """Drive one InteractiveMatch through a polished, keyboard-friendly UI."""

    def __init__(
        self,
        master: tk.Misc,
        match: InteractiveMatch,
        gemini_advisor: GeminiAgentAdvisor | None = None,
        on_new_game: Callable[[], bool] | None = None,
    ) -> None:
        self.master = master
        self.match = match
        self.gemini_advisor = gemini_advisor
        self.on_new_game = on_new_game
        self._barrier_mode = False
        self._agent_after_id: str | None = None
        self._paused = False
        self._closed = False
        configure_window(master, title="ShadowGrid | Tactical Command", min_size=(900, 650))
        install_styles(master)

        self.shell = ttk.Frame(master, style="App.TFrame", padding=22)
        self.shell.pack(fill="both", expand=True)
        header = ttk.Frame(self.shell, style="App.TFrame")
        header.pack(fill="x", pady=(0, 16))
        title_box = ttk.Frame(header, style="App.TFrame")
        title_box.pack(side="left")
        ttk.Label(title_box, text="SHADOWGRID", style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_box, text=MODE_LABELS[match.mode].upper(), style="Subtitle.TLabel").pack(
            anchor="w"
        )
        header_actions = ttk.Frame(header, style="App.TFrame")
        header_actions.pack(side="right")
        self.new_game_button = tk.Button(
            header_actions,
            text="↻  NEW GAME",
            command=self._request_new_game,
            bg=COLORS["surface"],
            fg=COLORS["text"],
            activebackground=COLORS["border"],
            activeforeground=COLORS["text"],
            relief="flat",
            bd=0,
            padx=14,
            pady=10,
            font=(FONT, 9, "bold"),
            cursor="hand2",
        )
        self.new_game_button.pack(side="left", padx=(0, 10))
        self.status_label = tk.Label(
            header_actions,
            font=(FONT, 12, "bold"),
            bg=COLORS["surface_alt"],
            fg=COLORS["accent"],
            padx=18,
            pady=10,
        )
        self.status_label.pack(side="right")

        content = ttk.Frame(self.shell, style="App.TFrame")
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)
        board_card = ttk.Frame(content, style="Card.TFrame", padding=18)
        ttk.Label(board_card, text="TACTICAL MAP", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            board_card,
            text="Select a glowing legal cell or use the movement console.",
            style="CardText.TLabel",
        ).pack(anchor="w", pady=(2, 12))
        board_wrap = tk.Frame(board_card, bg=COLORS["surface"])
        board_wrap.pack(expand=True)
        self.canvas = BoardCanvas(board_wrap, grid_size=match.board.config.grid_size, cell_size=54)
        self.canvas.configure(bg=COLORS["surface"], highlightbackground=COLORS["border"])
        self.canvas.pack()

        sidebar = ttk.Frame(content, style="Card.TFrame", padding=18, width=300)
        sidebar.grid(row=0, column=1, sticky="ns", padx=(14, 0))
        sidebar.grid_propagate(False)
        board_card.grid(row=0, column=0, sticky="nsew")
        ttk.Label(sidebar, text="MISSION TELEMETRY", style="CardTitle.TLabel").pack(anchor="w")
        telemetry = ttk.Frame(sidebar, style="Surface.TFrame")
        telemetry.pack(fill="x", pady=(10, 18))
        self.turn_label = ttk.Label(telemetry, style="Telemetry.TLabel")
        self.turn_label.pack(fill="x")
        self.role_label = ttk.Label(telemetry, style="Telemetry.TLabel")
        self.role_label.pack(fill="x")
        self.barriers_label = ttk.Label(telemetry, style="Telemetry.TLabel")
        self.barriers_label.pack(fill="x")
        self.gemini_label = tk.Label(
            sidebar,
            text="GEMINI  OFFLINE",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(MONO_FONT, 8, "bold"),
            justify="left",
            wraplength=250,
        )
        self.gemini_label.pack(fill="x", pady=(0, 18))

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
            master.bind(sequence, lambda _event, m=move: self._on_human_move(m))
        master.bind("b", lambda _event: self._toggle_barrier_mode())

    def start(self) -> None:
        self._advance()

    def _advance(self) -> None:
        if self._closed or self._paused:
            return
        if self.match.is_finished:
            self._show_result()
            return
        if self.match.is_human_turn():
            self._enable_human_controls()
        else:
            self._disable_human_controls()
            self._agent_after_id = self.master.after(AGENT_MOVE_DELAY_MS, self._agent_turn)
        self._render()

    def _agent_turn(self) -> None:
        self._agent_after_id = None
        if self._closed or self._paused or self.match.is_finished:
            return
        self.status_label.config(
            text=f"◌  {self.match.current_role.value.upper()} / GEMINI THINKING"
        )
        self.master.update_idletasks()
        self.match.apply_move(
            self.match.agent_move(self._gemini_move if self.gemini_advisor else None)
        )
        self._advance()

    def _request_new_game(self) -> None:
        """Pause this match while the owner reopens the mission selector."""
        if self.on_new_game is None or self._closed:
            return
        self._paused = True
        if self._agent_after_id is not None:
            with suppress(tk.TclError):
                self.master.after_cancel(self._agent_after_id)
            self._agent_after_id = None
        changed = self.on_new_game()
        if not changed and not self._closed:
            self._paused = False
            self._advance()

    def close(self) -> None:
        """Stop pending callbacks, remove bindings, and destroy this session UI."""
        self._closed = True
        if self._agent_after_id is not None:
            with suppress(tk.TclError):
                self.master.after_cancel(self._agent_after_id)
            self._agent_after_id = None
        for sequence in (*_KEY_MOVES, "b"):
            self.master.unbind(sequence)
        self.shell.destroy()

    def _gemini_move(
        self,
        role: AgentRole,
        own_position: Position,
        belief_peak: Position,
        legal_moves: tuple[Move, ...],
        fallback: Move,
    ) -> Move:
        """Bridge the pure match callback to the external Gemini service."""
        if self.gemini_advisor is None:
            return fallback
        decision = self.gemini_advisor.choose_move(
            TacticalContext(
                role=role,
                own_position=own_position,
                belief_peak=belief_peak,
                legal_moves=legal_moves,
                turn_number=self.match.turns_played + 1,
                max_turns=self.match.max_moves,
                remaining_barriers=self.match.board.remaining_barrier_budget,
            ),
            fallback,
        )
        prefix = "FALLBACK" if decision.used_fallback else "GEMINI"
        color = COLORS["warning"] if decision.used_fallback else COLORS["accent"]
        self.gemini_label.config(
            text=f"{prefix}  {decision.move.name}\n{decision.rationale}", fg=color
        )
        return decision.move

    def _on_human_move(self, move: Move) -> None:
        if (
            self.match.is_finished
            or not self.match.is_human_turn()
            or move not in self.match.legal_moves()
        ):
            return
        self._barrier_mode = False
        self.match.apply_move(move)
        self._advance()

    def _toggle_barrier_mode(self) -> None:
        if (
            self.match.is_finished
            or not self.match.is_human_turn()
            or self.match.current_role is not AgentRole.COP
        ):
            return
        self._barrier_mode = not self._barrier_mode
        self._render()

    def _on_cell_click(self, row: int, col: int) -> None:
        if self.match.is_finished or not self.match.is_human_turn():
            return
        position = Position(row, col)
        if self._barrier_mode:
            try:
                self.match.place_barrier(position)
            except (MoveRejectedError, ValueError):
                return
            self._barrier_mode = False
            self._advance()
            return
        move = next((m for m, p in self.match.legal_moves().items() if p == position), None)
        if move is not None:
            self.match.apply_move(move)
            self._advance()

    def _enable_human_controls(self) -> None:
        legal = self.match.legal_moves()
        for move, button in self.move_buttons.items():
            button.config(state="normal" if move in legal else "disabled")
        is_cop = self.match.current_role is AgentRole.COP
        self.barrier_button.config(state="normal" if is_cop else "disabled")
        self.canvas.set_click_handler(self._on_cell_click)

    def _disable_human_controls(self) -> None:
        for button in self.move_buttons.values():
            button.config(state="disabled")
        self.barrier_button.config(state="disabled")
        self.canvas.set_click_handler(None)
        self._barrier_mode = False

    def _render(self) -> None:
        view = self.match.visible_view_for_current()
        human_turn = self.match.is_human_turn()
        turn_word = "YOUR" if human_turn else "AGENT"
        role_name = view.own_role.value.upper()
        self.status_label.config(text=f"●  {role_name} / {turn_word} TURN")
        self.turn_label.config(
            text=f"TURN      {self.match.turns_played + 1:02} / {self.match.max_moves:02}"
        )
        self.role_label.config(text=f"ACTIVE    {role_name}")
        barriers_used = (
            self.match.board.config.max_barriers - self.match.board.remaining_barrier_budget
        )
        self.barriers_label.config(
            text=f"BARRIERS  {barriers_used:02} / {self.match.board.config.max_barriers:02}"
        )
        self.barrier_button.config(
            text="CANCEL PLACEMENT" if self._barrier_mode else "＋  DEPLOY BARRIER"
        )
        self.canvas.clear_markers()
        legal_cells = (
            {(p.row, p.col) for p in self.match.legal_moves().values()}
            if human_turn and not self._barrier_mode
            else set()
        )
        self.canvas.highlight_legal_cells(legal_cells)
        if view.belief is not None:
            vm = build_live_view_model(
                view.own_position,
                view.belief,
                self.match.board,
                TurnState.YOUR_TURN if human_turn else TurnState.LOCKED,
                role_label=_ROLE_LABEL[view.own_role],
            )
            for cell in vm.cells:
                self.canvas.set_cell_color(cell.position.row, cell.position.col, cell.color)
            self.canvas.draw_agent(
                view.own_position.row,
                view.own_position.col,
                _ROLE_LABEL[view.own_role],
                _ROLE_FILL[view.own_role],
            )
        else:
            for row in range(self.match.board.config.grid_size):
                for col in range(self.match.board.config.grid_size):
                    pos = Position(row, col)
                    self.canvas.set_cell_color(
                        row,
                        col,
                        _BARRIER_COLOR if self.match.board.is_blocked(pos) else COLORS["cell"],
                    )
            self.canvas.draw_agent(
                view.own_position.row,
                view.own_position.col,
                _ROLE_LABEL[view.own_role],
                _ROLE_FILL[view.own_role],
            )
            if view.opponent_position is not None:
                other = AgentRole.THIEF if view.own_role is AgentRole.COP else AgentRole.COP
                self.canvas.draw_agent(
                    view.opponent_position.row,
                    view.opponent_position.col,
                    _ROLE_LABEL[other],
                    _ROLE_FILL[other],
                )

    def _show_result(self) -> None:
        self._disable_human_controls()
        text = _OUTCOME_TEXT.get(self.match.outcome, str(self.match.outcome))
        self.status_label.config(text=f"MATCH OVER / {text}", fg=COLORS["success"])
        messagebox.showinfo("Match Over", text)
