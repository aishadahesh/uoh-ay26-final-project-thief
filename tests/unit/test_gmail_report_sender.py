"""Unit tests for Gmail report sending: MIME construction, encoding, and the
Gatekeeper-guarded 429-backoff send pipeline (Chapter 9, Sec. 9.3.1-9.3.15).

The real, OAuth-authenticated Gmail API is never contacted here -- an
injectable `transport` callable stands in for it (see the module docstring
in gmail_report_sender.py for why the real one can't be built in this
session). What's under test is the pipeline's own logic: MIME/JSON-only
construction, base64url encoding, Gatekeeper gating, and 429 backoff.
"""

import base64
import json
from datetime import date
from email import message_from_bytes

from police_thief.services.anomaly_detector import AnomalyDetector
from police_thief.services.gatekeeper import Gatekeeper, GatekeeperBlockReason, Http429BackoffPolicy
from police_thief.services.gmail_report_sender import (
    GmailRateLimitedError,
    GmailSendError,
    build_report_email,
    encode_for_gmail_api,
    send_match_report,
)
from police_thief.services.quota_manager import QuotaManager
from police_thief.services.token_bucket import TokenBucket

DAY_1 = date(2026, 7, 16)


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


def _make_gatekeeper(tmp_path, **overrides):
    clock = FakeClock()
    defaults = {"quota": 10, "capacity": 10, "refill_rate": 1.0, "max_sends": 10, "window": 60.0}
    defaults.update(overrides)
    return Gatekeeper(
        QuotaManager(
            daily_threshold=defaults["quota"], persist_path=tmp_path / "q.json", today=lambda: DAY_1
        ),
        TokenBucket(
            capacity=defaults["capacity"], refill_rate=defaults["refill_rate"], clock=clock
        ),
        AnomalyDetector(
            max_sends_in_window=defaults["max_sends"],
            window_seconds=defaults["window"],
            clock=clock,
        ),
    )


def test_build_report_email_attaches_json_not_free_text():
    message = build_report_email(
        "lecturer@example.com",
        "Match Report",
        {"cop_score": 20, "thief_score": 5},
        "result_G1.json",
    )
    raw = message.as_bytes()
    parsed = message_from_bytes(raw)
    assert parsed["to"] == "lecturer@example.com"
    assert parsed["subject"] == "Match Report"

    attachments = [part for part in parsed.walk() if part.get_filename() == "result_G1.json"]
    assert len(attachments) == 1
    payload = json.loads(attachments[0].get_payload(decode=True))
    assert payload == {"cop_score": 20, "thief_score": 5}


def test_build_report_email_rejects_a_free_text_string_payload_at_runtime():
    """Sec. 9.3.15 is [FORBIDDEN], not a style preference -- this must be a
    real runtime rejection, not just a type hint Python never checks."""
    try:
        build_report_email("a@b.com", "s", "just some free text report", "f.json")
        raise AssertionError("expected TypeError")
    except TypeError as exc:
        assert "forbidden" in str(exc)


def test_encode_for_gmail_api_produces_valid_urlsafe_base64():
    message = build_report_email("a@b.com", "s", {"x": 1}, "f.json")
    encoded = encode_for_gmail_api(message)
    assert isinstance(encoded, str)
    decoded = base64.urlsafe_b64decode(encoded.encode("ascii"))
    assert b"f.json" in decoded


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
