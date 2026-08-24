"""The report is structured JSON, never free text, and is encoded for the
Gmail API without corruption.

Split by theme out of the original `test_gmail_report_sender.py`."""

import base64
import json
from email import message_from_bytes

from police_thief.services.gmail_report_sender import (
    build_report_email,
    encode_for_gmail_api,
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
