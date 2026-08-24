"""Delivery behaviour under the rate limiter: first-attempt success,
gatekeeper refusal, 429 retry budget, and hard failures.

Split by theme out of the original `test_gmail_report_sender.py`."""


from police_thief.services.gatekeeper import GatekeeperBlockReason, Http429BackoffPolicy
from police_thief.services.gmail_report_sender import (
    GmailRateLimitedError,
    GmailSendError,
    send_match_report,
)
from tests.unit.gmail_helpers import (
    _make_gatekeeper,
)


def test_send_match_report_succeeds_on_first_attempt(tmp_path):
    gk = _make_gatekeeper(tmp_path)
    calls = []

    def transport(raw):
        calls.append(raw)
        return {"id": "msg-1"}

    result = send_match_report(
        gk,
        transport,
        Http429BackoffPolicy(5.0, 3),
        "a@b.com",
        "s",
        {"x": 1},
        "f.json",
        sleep=lambda s: None,
    )
    assert result.sent is True
    assert len(result.attempts) == 1
    assert result.attempts[0].success is True
    assert len(calls) == 1


def test_send_match_report_is_blocked_by_the_gatekeeper_before_any_transport_call(tmp_path):
    gk = _make_gatekeeper(tmp_path, quota=0)
    calls = []

    result = send_match_report(
        gk,
        lambda raw: calls.append(raw),
        Http429BackoffPolicy(5.0, 3),
        "a@b.com",
        "s",
        {"x": 1},
        "f.json",
    )
    assert result.sent is False
    assert result.blocked_reason == GatekeeperBlockReason.QUOTA_EXCEEDED
    assert calls == []  # never even attempted a network call


def test_send_match_report_recovers_after_a_429_within_retry_budget(tmp_path):
    gk = _make_gatekeeper(tmp_path)
    calls = {"n": 0}

    def flaky_transport(raw):
        calls["n"] += 1
        if calls["n"] < 2:
            raise GmailRateLimitedError("429")
        return {"id": "msg-ok"}

    sleeps = []
    result = send_match_report(
        gk,
        flaky_transport,
        Http429BackoffPolicy(5.0, 3),
        "a@b.com",
        "s",
        {"x": 1},
        "f.json",
        sleep=sleeps.append,
    )
    assert result.sent is True
    assert calls["n"] == 2
    assert sleeps == [5.0]
    assert [a.success for a in result.attempts] == [False, True]


def test_send_match_report_exhausts_retries_on_persistent_429(tmp_path):
    gk = _make_gatekeeper(tmp_path)
    calls = {"n": 0}

    def always_429(raw):
        calls["n"] += 1
        raise GmailRateLimitedError("429")

    sleeps = []
    result = send_match_report(
        gk,
        always_429,
        Http429BackoffPolicy(5.0, 2),
        "a@b.com",
        "s",
        {"x": 1},
        "f.json",
        sleep=sleeps.append,
    )
    assert result.sent is False
    assert calls["n"] == 3  # 1 initial + 2 retries
    assert sleeps == [5.0, 5.0]
    assert all(a.reason == "rate_limited_429" for a in result.attempts)


def test_send_match_report_stops_immediately_on_a_non_429_hard_failure(tmp_path):
    gk = _make_gatekeeper(tmp_path)
    calls = {"n": 0}

    def hard_fail(raw):
        calls["n"] += 1
        raise GmailSendError("invalid credentials")

    result = send_match_report(
        gk,
        hard_fail,
        Http429BackoffPolicy(5.0, 3),
        "a@b.com",
        "s",
        {"x": 1},
        "f.json",
        sleep=lambda s: None,
    )
    assert result.sent is False
    assert calls["n"] == 1  # never retried a non-429 failure
    assert result.attempts[0].reason == "invalid credentials"
