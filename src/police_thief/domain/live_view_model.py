"""Live GUI view-model: local-truth-only presentation logic (Chapter 7).

docs/tasks.md Sec. 7.2-7.3: each side's interface displays only its own
position, its own belief map about the opponent, and a turn-state banner --
never the opponent's true position ("no bird's-eye view", Sec. 7.2.1, and
Sec. 7.3.3's explicit FORBIDDEN). This module is presentation-logic only
(color/text mapping), framework-agnostic so it can be unit-tested without a
real display; gui/live_gui.py wires it to actual Tkinter widgets.

build_live_view_model has no parameter through which an opponent's true
Position could even be passed -- this is a structural guarantee, the same
pattern BrainBase (Chapter 6) uses for the move-decision boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from police_thief.domain.belief import BeliefMap
from police_thief.domain.board import Board, Position

_LOW_COLOR = (255, 255, 255)  # white: no believed presence
_HIGH_COLOR = (200, 0, 0)  # deep red: highest believed presence in this map
_BARRIER_COLOR = "#2b2b2b"  # near-black: a permanently blocked cell, never a belief gradient


class TurnState(StrEnum):
    """Sec. 7.3.4: reflects the async commit/acknowledge/reveal handshake."""

    YOUR_TURN = "YOUR_TURN"
    LOCKED = "LOCKED"


_TURN_BANNER_TEXT = {TurnState.YOUR_TURN: "YOUR TURN", TurnState.LOCKED: "LOCKED"}
_TURN_BANNER_COLOR = {TurnState.YOUR_TURN: "#2e7d32", TurnState.LOCKED: "#616161"}  # green / gray


def belief_to_color(intensity: float, max_intensity: float) -> str:
    """Map a belief value to a hex color on a white-to-red gradient.

    Normalized to the map's own current peak (`max_intensity`) rather than
    a fixed absolute scale, so both a near-uniform prior and a sharply
    peaked posterior render sensibly.
    """
    ratio = 0.0 if max_intensity <= 0 else min(1.0, max(0.0, intensity / max_intensity))
    r = round(_LOW_COLOR[0] + (_HIGH_COLOR[0] - _LOW_COLOR[0]) * ratio)
    g = round(_LOW_COLOR[1] + (_HIGH_COLOR[1] - _LOW_COLOR[1]) * ratio)
    b = round(_LOW_COLOR[2] + (_HIGH_COLOR[2] - _LOW_COLOR[2]) * ratio)
    return f"#{r:02x}{g:02x}{b:02x}"


@dataclass(frozen=True)
class CellView:
    position: Position
    color: str
    is_own_position: bool
    is_blocked: bool


@dataclass(frozen=True)
class LiveViewModel:
    """Everything the Live GUI needs to render -- and nothing more.

    `role_label`/`visited` are additive, keyword-only, defaulted fields (see
    `build_live_view_model`) -- a caller wanting a plain rendering (as every
    call site did before this field existed) gets identical output; a caller
    that wants the richer agent-marker/trail rendering opts in explicitly.
    Neither field can hold anything about the *opponent* -- `visited` is
    documented, by the one parameter name through which a caller could ever
    populate it, as this side's own trail only.
    """

    own_position: Position
    cells: tuple[CellView, ...]
    turn_state: TurnState
    turn_banner_text: str
    turn_banner_color: str
    role_label: str = "•"
    visited: frozenset[Position] = field(default_factory=frozenset)


def build_live_view_model(
    own_position: Position,
    belief: BeliefMap,
    board: Board,
    turn_state: TurnState,
    *,
    role_label: str = "•",
    visited: frozenset[Position] = frozenset(),
) -> LiveViewModel:
    """The single conversion point from raw belief data to a renderable model.

    Barrier cells (docs/tasks.md T0405) always render as a distinct, fixed
    color -- never a belief gradient -- since they structurally can never
    hold the opponent (Chapter 6's BeliefMap already excludes them from the
    tracked distribution; this is that same fact, made visible).

    `role_label`/`visited` are this side's own, caller-supplied information
    only (e.g. "C" for the cop, and the set of cells it has itself occupied
    so far) -- there is still no parameter here through which an opponent's
    true position could ever be represented.
    """
    grid_size = board.config.grid_size
    all_positions = [Position(r, c) for r in range(grid_size) for c in range(grid_size)]
    max_intensity = max((belief.belief_at(p) for p in all_positions), default=0.0)
    cells = tuple(
        CellView(
            position=p,
            color=_BARRIER_COLOR
            if board.is_blocked(p)
            else belief_to_color(belief.belief_at(p), max_intensity),
            is_own_position=(p == own_position),
            is_blocked=board.is_blocked(p),
        )
        for p in all_positions
    )
    return LiveViewModel(
        own_position=own_position,
        cells=cells,
        turn_state=turn_state,
        turn_banner_text=_TURN_BANNER_TEXT[turn_state],
        turn_banner_color=_TURN_BANNER_COLOR[turn_state],
        role_label=role_label,
        visited=visited,
    )
