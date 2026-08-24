"""Shared clock and gatekeeper doubles for the Gmail report tests.

Extracted when `test_gmail_report_sender.py` was split by theme."""

from datetime import date

from police_thief.services.anomaly_detector import AnomalyDetector
from police_thief.services.gatekeeper import Gatekeeper
from police_thief.services.quota_manager import QuotaManager
from police_thief.services.token_bucket import TokenBucket


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


DAY_1 = date(2026, 7, 16)
