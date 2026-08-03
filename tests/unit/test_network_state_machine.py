"""Tests for the explicit cross-machine network runtime state machine."""

import pytest

from police_thief.services.network_state_machine import (
    NetworkEvent,
    NetworkRuntimeStateMachine,
    NetworkState,
    NetworkStateError,
)


def _ready_machine() -> NetworkRuntimeStateMachine:
    machine = NetworkRuntimeStateMachine()
    machine.transition(NetworkEvent.START)
    machine.transition(NetworkEvent.OPPONENT_CONNECTED)
    machine.transition(NetworkEvent.TERMS_VERIFIED)
    machine.transition(NetworkEvent.STEP0_EXCHANGED)
    return machine


def test_network_state_machine_happy_path_to_completed():
    machine = _ready_machine()
    machine.transition(NetworkEvent.LOCAL_TURN, turn_number=1)
    machine.transition(NetworkEvent.MOVE_COMPUTED, turn_number=1)
    machine.transition(NetworkEvent.COMMIT_SENT, turn_number=1)
    machine.transition(NetworkEvent.TURN_DATA_EXCHANGED, turn_number=1)
    machine.transition(NetworkEvent.TURN_VERIFIED, turn_number=1)
    machine.apply_turn_once(1)
    machine.transition(NetworkEvent.TURN_APPLIED, turn_number=1)
    machine.transition(NetworkEvent.MATCH_FINISHED)
    machine.transition(NetworkEvent.AUDIT_VERIFIED)
    assert machine.transition(NetworkEvent.REPORT_WRITTEN) == NetworkState.COMPLETED


def test_network_state_machine_rejects_illegal_transition():
    machine = NetworkRuntimeStateMachine()
    with pytest.raises(NetworkStateError, match="illegal transition"):
        machine.transition(NetworkEvent.MATCH_FINISHED)


def test_network_state_machine_rejects_duplicate_turn_application():
    machine = _ready_machine()
    machine.apply_turn_once(2)
    with pytest.raises(NetworkStateError, match="already been applied"):
        machine.apply_turn_once(2)


@pytest.mark.parametrize(
    ("event", "terminal"),
    [
        (NetworkEvent.STALE_EVENT, NetworkState.PROTOCOL_FAILURE),
        (NetworkEvent.FUTURE_EVENT, NetworkState.PROTOCOL_FAILURE),
        (NetworkEvent.MALFORMED_MESSAGE, NetworkState.PROTOCOL_FAILURE),
        (NetworkEvent.TIMEOUT, NetworkState.TECHNICAL_LOSS),
        (NetworkEvent.DISCONNECT, NetworkState.TECHNICAL_LOSS),
    ],
)
def test_network_state_machine_maps_failures_to_terminal_states(event, terminal):
    machine = _ready_machine()
    assert machine.transition(event) == terminal
    with pytest.raises(NetworkStateError, match="terminal state"):
        machine.transition(NetworkEvent.RETRY)


def test_network_state_machine_retry_does_not_advance_wait_state():
    machine = NetworkRuntimeStateMachine()
    machine.transition(NetworkEvent.START)
    assert machine.transition(NetworkEvent.RETRY) == NetworkState.WAITING_FOR_OPPONENT
