"""Single-process local simulation harness (Chapters 3-4).

Placeholder-policy only: real strategic decision-making is Chapter 6's
domain (heuristics, a custom algorithm, or optionally reinforcement
learning). The policies here exist purely to prove the board/movement/
barrier/capture/scoring/scent logic plays a full, legal match end-to-end
with no crash -- no networking, no crypto, no belief modeling yet.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from police_thief.domain.board import Board, Move, MoveRejectedError, Position
from police_thief.domain.capture import check_capture, is_boxed_in
from police_thief.domain.heuristics import greedy_manhattan_move
from police_thief.domain.scent import ScentField
from police_thief.domain.scoring import MatchOutcome, ScoringTable, score_for
from police_thief.shared.game_config import MatchParameters

Policy = Callable[[Board, Position, Position], Move]


def _is_out_of_bounds_rejection(exc: MoveRejectedError) -> bool:
    return "leaves the board" in str(exc)


@dataclass(frozen=True)
class MatchResult:
    """The final outcome of one simulated match.

    cop_scent/thief_scent are each side's *own* emitted trail at match end
    (named after who emits it, not who reads it -- docs/tasks.md Sec. 4.1.3).
    Exposed for inspection/testing only; no policy in this chapter reads
    them to make a decision -- that is Chapter 6's belief-map territory.
    """

    outcome: MatchOutcome
    cop_score: int
    thief_score: int
    turns_played: int
    cop_scent: ScentField
    thief_scent: ScentField


def move_toward_policy(board: Board, own: Position, target: Position) -> Move:
    """Placeholder: greedily reduce Manhattan distance to `target`.

    This "cheats" relative to real strategy (Chapter 6): it takes the
    opponent's true position directly rather than a belief-map estimate,
    which is fine for a placeholder proving the board/scent/scoring logic
    works, but would violate partial observability for a real brain. See
    domain/strategy/manhattan_brain.py for the belief-map-respecting
    equivalent, which shares this module's search logic via
    domain/heuristics.py rather than duplicating it.
    """
    return greedy_manhattan_move(board, own, target, chase=True)


def move_away_policy(board: Board, own: Position, threat: Position) -> Move:
    """Placeholder: greedily increase Manhattan distance from `threat`. See
    move_toward_policy's docstring for why this is a placeholder, not real
    strategy.
    """
    return greedy_manhattan_move(board, own, threat, chase=False)


def run_local_match(
    params: MatchParameters,
    cop_policy: Policy = move_toward_policy,
    thief_policy: Policy = move_away_policy,
) -> MatchResult:
    """Alternate cop/thief turns until capture, survival, or max_moves.

    max_moves vs. survival_threshold precedence (docs/TODO.md T0137):
    survival_threshold is checked every turn and is expected to be <=
    max_moves; max_moves is a hard safety cap that also resolves to a
    SURVIVAL outcome if somehow reached first, so the match always
    terminates deterministically either way.

    Scent (Chapter 4): every turn, after each side's move resolves, that
    side's own ScentField decays (the whole board's forgetting step) and
    then emits fresh around its new position -- reproducing the mandatory
    tau(t+1) = max(0, (1-rho)*tau(t) + delta_tau) equation in two calls.
    """
    board = Board(params.board)
    cop_pos, thief_pos = params.cop_start, params.thief_start
    scoring: ScoringTable = params.scoring
    cop_scent = ScentField(params.board.grid_size, params.scent)
    thief_scent = ScentField(params.board.grid_size, params.scent)

    def finish(outcome: MatchOutcome, turn: int) -> MatchResult:
        cop_score, thief_score = score_for(outcome, scoring)
        return MatchResult(outcome, cop_score, thief_score, turn, cop_scent, thief_scent)

    for turn in range(1, params.max_moves + 1):
        try:
            cop_pos = board.apply_move(cop_pos, cop_policy(board, cop_pos, thief_pos))
        except MoveRejectedError:
            return finish(MatchOutcome.TECHNICAL_LOSS, turn)
        cop_scent.decay()
        cop_scent.emit(cop_pos)
        if check_capture(cop_pos, thief_pos):
            return finish(MatchOutcome.CAPTURE, turn)

        # Not exercised by any current test: the placeholder policies (this
        # chapter's scope) never place barriers, so a mid-match boxed-in
        # thief cannot occur yet. The check stays here because it is
        # correct and forward-looking -- Chapter 6's barrier-placing
        # strategies will reach it -- not because it is currently dead code
        # by mistake. board.py/test_capture.py already prove is_boxed_in()
        # itself is correct in isolation.
        if is_boxed_in(board, thief_pos):
            return finish(MatchOutcome.CAPTURE, turn)
        try:
            thief_pos = board.apply_move(thief_pos, thief_policy(board, thief_pos, cop_pos))
        except MoveRejectedError as exc:
            if _is_out_of_bounds_rejection(exc):
                return finish(MatchOutcome.CAPTURE, turn)
            return finish(MatchOutcome.TECHNICAL_LOSS, turn)
        thief_scent.decay()
        thief_scent.emit(thief_pos)
        if check_capture(cop_pos, thief_pos):
            # Also not exercised: the greedy flee policy never steps onto
            # the cop's cell by construction. Kept for defensive symmetry
            # with the pre-thief-move capture check above.
            return finish(MatchOutcome.CAPTURE, turn)

        if turn >= params.survival_threshold:
            return finish(MatchOutcome.SURVIVAL, turn)

    return finish(MatchOutcome.SURVIVAL, params.max_moves)
