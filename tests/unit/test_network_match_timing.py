from police_thief.services.network_match import (
    BOUNDARY_FIRST_TURN_TIMEOUT_SECONDS,
    _turn_timeout,
)


def test_first_turn_uses_boundary_timeout() -> None:
    assert _turn_timeout(120.0, 1) == BOUNDARY_FIRST_TURN_TIMEOUT_SECONDS


def test_later_turns_keep_response_timeout() -> None:
    assert _turn_timeout(120.0, 2) == 120.0
