"""Explicit network-runtime state machine for cross-machine peer matches."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class NetworkState(StrEnum):
    INITIALIZING = "INITIALIZING"
    WAITING_FOR_OPPONENT = "WAITING_FOR_OPPONENT"
    NEGOTIATING_CONFIG = "NEGOTIATING_CONFIG"
    EXCHANGING_STEP0 = "EXCHANGING_STEP0"
    READY = "READY"
    COMPUTING_MOVE = "COMPUTING_MOVE"
    COMMITTING = "COMMITTING"
    WAITING_FOR_REMOTE_COMMIT = "WAITING_FOR_REMOTE_COMMIT"
    EXCHANGING_TURN_DATA = "EXCHANGING_TURN_DATA"
    VERIFYING_TURN = "VERIFYING_TURN"
    APPLYING_TURN = "APPLYING_TURN"
    FINAL_AUDIT = "FINAL_AUDIT"
    REPORTING = "REPORTING"
    COMPLETED = "COMPLETED"
    TECHNICAL_LOSS = "TECHNICAL_LOSS"
    PROTOCOL_FAILURE = "PROTOCOL_FAILURE"


class NetworkEvent(StrEnum):
    START = "START"
    OPPONENT_CONNECTED = "OPPONENT_CONNECTED"
    TERMS_VERIFIED = "TERMS_VERIFIED"
    STEP0_EXCHANGED = "STEP0_EXCHANGED"
    LOCAL_TURN = "LOCAL_TURN"
    REMOTE_TURN = "REMOTE_TURN"
    MOVE_COMPUTED = "MOVE_COMPUTED"
    COMMIT_SENT = "COMMIT_SENT"
    COMMIT_RECEIVED = "COMMIT_RECEIVED"
    TURN_DATA_EXCHANGED = "TURN_DATA_EXCHANGED"
    TURN_VERIFIED = "TURN_VERIFIED"
    TURN_APPLIED = "TURN_APPLIED"
    MATCH_FINISHED = "MATCH_FINISHED"
    AUDIT_VERIFIED = "AUDIT_VERIFIED"
    REPORT_WRITTEN = "REPORT_WRITTEN"
    RETRY = "RETRY"
    STALE_EVENT = "STALE_EVENT"
    FUTURE_EVENT = "FUTURE_EVENT"
    TIMEOUT = "TIMEOUT"
    DISCONNECT = "DISCONNECT"
    MALFORMED_MESSAGE = "MALFORMED_MESSAGE"
    LOCAL_FAILURE = "LOCAL_FAILURE"


class NetworkStateError(RuntimeError):
    """Raised when a network event is illegal for the current state."""


TERMINAL_STATES = frozenset(
    {NetworkState.COMPLETED, NetworkState.TECHNICAL_LOSS, NetworkState.PROTOCOL_FAILURE}
)

_TRANSITIONS: dict[tuple[NetworkState, NetworkEvent], NetworkState] = {
    (NetworkState.INITIALIZING, NetworkEvent.START): NetworkState.WAITING_FOR_OPPONENT,
    (
        NetworkState.WAITING_FOR_OPPONENT,
        NetworkEvent.OPPONENT_CONNECTED,
    ): NetworkState.NEGOTIATING_CONFIG,
    (NetworkState.NEGOTIATING_CONFIG, NetworkEvent.TERMS_VERIFIED): NetworkState.EXCHANGING_STEP0,
    (NetworkState.EXCHANGING_STEP0, NetworkEvent.STEP0_EXCHANGED): NetworkState.READY,
    (NetworkState.READY, NetworkEvent.LOCAL_TURN): NetworkState.COMPUTING_MOVE,
    (NetworkState.READY, NetworkEvent.REMOTE_TURN): NetworkState.WAITING_FOR_REMOTE_COMMIT,
    (NetworkState.COMPUTING_MOVE, NetworkEvent.MOVE_COMPUTED): NetworkState.COMMITTING,
    (NetworkState.COMMITTING, NetworkEvent.COMMIT_SENT): NetworkState.EXCHANGING_TURN_DATA,
    (
        NetworkState.WAITING_FOR_REMOTE_COMMIT,
        NetworkEvent.COMMIT_RECEIVED,
    ): NetworkState.EXCHANGING_TURN_DATA,
    (
        NetworkState.EXCHANGING_TURN_DATA,
        NetworkEvent.TURN_DATA_EXCHANGED,
    ): NetworkState.VERIFYING_TURN,
    (NetworkState.VERIFYING_TURN, NetworkEvent.TURN_VERIFIED): NetworkState.APPLYING_TURN,
    (NetworkState.APPLYING_TURN, NetworkEvent.TURN_APPLIED): NetworkState.READY,
    (NetworkState.READY, NetworkEvent.MATCH_FINISHED): NetworkState.FINAL_AUDIT,
    (NetworkState.FINAL_AUDIT, NetworkEvent.AUDIT_VERIFIED): NetworkState.REPORTING,
    (NetworkState.REPORTING, NetworkEvent.REPORT_WRITTEN): NetworkState.COMPLETED,
    (NetworkState.WAITING_FOR_OPPONENT, NetworkEvent.RETRY): NetworkState.WAITING_FOR_OPPONENT,
    (
        NetworkState.WAITING_FOR_REMOTE_COMMIT,
        NetworkEvent.RETRY,
    ): NetworkState.WAITING_FOR_REMOTE_COMMIT,
    (NetworkState.EXCHANGING_TURN_DATA, NetworkEvent.RETRY): NetworkState.EXCHANGING_TURN_DATA,
}

_TECHNICAL_LOSS_EVENTS = frozenset(
    {
        NetworkEvent.TIMEOUT,
        NetworkEvent.DISCONNECT,
        NetworkEvent.LOCAL_FAILURE,
    }
)
_PROTOCOL_FAILURE_EVENTS = frozenset(
    {
        NetworkEvent.STALE_EVENT,
        NetworkEvent.FUTURE_EVENT,
        NetworkEvent.MALFORMED_MESSAGE,
    }
)


@dataclass
class NetworkRuntimeStateMachine:
    state: NetworkState = NetworkState.INITIALIZING
    applied_turns: set[int] = field(default_factory=set)
    history: list[dict[str, str | int]] = field(default_factory=list)

    def transition(self, event: NetworkEvent, *, turn_number: int | None = None) -> NetworkState:
        if self.state in TERMINAL_STATES:
            raise NetworkStateError(f"terminal state {self.state} cannot transition on {event}")
        previous = self.state
        if event in _TECHNICAL_LOSS_EVENTS:
            self.state = NetworkState.TECHNICAL_LOSS
        elif event in _PROTOCOL_FAILURE_EVENTS:
            self.state = NetworkState.PROTOCOL_FAILURE
        else:
            try:
                self.state = _TRANSITIONS[(self.state, event)]
            except KeyError as exc:
                raise NetworkStateError(f"illegal transition {self.state} + {event}") from exc
        self.history.append(
            {
                "from": previous.value,
                "event": event.value,
                "turn_number": turn_number if turn_number is not None else -1,
                "to": self.state.value,
            }
        )
        return self.state

    def apply_turn_once(self, turn_number: int) -> None:
        if turn_number in self.applied_turns:
            raise NetworkStateError(f"turn {turn_number} has already been applied")
        self.applied_turns.add(turn_number)
