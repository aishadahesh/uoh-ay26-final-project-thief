"""The single gateway coordinating all sub-systems (Chapter 8, Sec. 8.1-8.2).

Sec. 8.2.1: every sub-module knows the Orchestrator alone -- no module
directly knows and calls another module. The Orchestrator itself contains
NO decision-making or communication logic; its role is purely coordination.
Diagram 12's five named sub-systems (Sec. 8.3.8) are all wired here: MCP
Connector (Chapter 2), Decision Module (Chapter 6's BrainBase), Log
Manager, Deadline Tracker, and Watchdog.

This also closes a gap left open since Chapter 2: mcp_server.py's
MoveEnvelope always carried a placeholder signed_move/signature pair,
explicitly documented there as "signature becomes a real SHA-256
commitment in Chapter 5/6." run_turn() below is the first place that
placeholder is replaced with an actual commitment hash, sent over a real
MCP call wrapped in a real deadline.
"""

from __future__ import annotations

from dataclasses import dataclass

from police_thief.domain.belief import BeliefMap
from police_thief.domain.board import Board, Move, Position
from police_thief.domain.strategy.brain_base import BrainBase
from police_thief.services.commit_reveal import LogEntry, commit, verify
from police_thief.services.deadline_tracker import DeadlineExceededError, DeadlineTracker
from police_thief.services.log_manager import LogManager
from police_thief.services.mcp_client import PeerClientError, send_move_async
from police_thief.services.state_machine import MatchState, MatchStateMachine
from police_thief.services.watchdog import Watchdog


class TechnicalLossError(RuntimeError):
    """Raised internally whenever a turn cannot complete legally."""


@dataclass(frozen=True)
class TurnResult:
    """What one orchestrated turn produced -- state alone if it failed."""

    state: MatchState
    move: Move | None
    h_commit: str | None


class Orchestrator:
    """Drives one side's per-turn pipeline through the legal state machine."""

    def __init__(
        self,
        brain: BrainBase,
        opponent_url: str,
        deadline_tracker: DeadlineTracker,
        watchdog: Watchdog,
        log_manager: LogManager,
    ) -> None:
        self.brain = brain
        self.opponent_url = opponent_url
        self.deadline_tracker = deadline_tracker
        self.watchdog = watchdog
        self.log_manager = log_manager
        self.state_machine = MatchStateMachine()

    async def run_turn(self, board: Board, own_position: Position, belief: BeliefMap) -> TurnResult:
        """One full WAITING_FOR_OPPONENT -> ... -> WAITING_FOR_OPPONENT cycle,
        or a transition to TECHNICAL_LOSS on any failure along the way.
        """
        self.watchdog.heartbeat()
        try:
            self.state_machine.transition(MatchState.COMPUTING_MOVE)
            move = self.brain._decide_move(board, own_position, belief)

            self.state_machine.transition(MatchState.COMMITTING)
            board_state = {"row": own_position.row, "col": own_position.col}
            commitment = commit(state=board_state, move=move, intent=True)
            await self.deadline_tracker.call(
                lambda: send_move_async(
                    self.opponent_url,
                    signed_move=commitment.h_commit,
                    signature="commit",
                    timeout=self.deadline_tracker.timeout_seconds,
                )
            )

            self.state_machine.transition(MatchState.AWAITING_REVEAL)
            self.state_machine.transition(MatchState.VERIFYING)
            if not verify(board_state, move, True, commitment.nonce, commitment.h_commit):
                raise TechnicalLossError("self-verification failed immediately after commit")

            self.log_manager.record(
                LogEntry(
                    state=board_state,
                    move=move,
                    intent=True,
                    nonce=commitment.nonce,
                    h_commit=commitment.h_commit,
                )
            )
            self.state_machine.transition(MatchState.WAITING_FOR_OPPONENT)
            self.watchdog.heartbeat()
            return TurnResult(
                state=self.state_machine.state, move=move, h_commit=commitment.h_commit
            )
        except (DeadlineExceededError, PeerClientError, TechnicalLossError):
            self.state_machine.transition(MatchState.TECHNICAL_LOSS)
            return TurnResult(state=self.state_machine.state, move=None, h_commit=None)
