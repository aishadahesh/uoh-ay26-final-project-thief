"""Unit tests for the real Gmail OAuth transport (Chapter 9 / App. A).

The genuinely untestable boundary here is the same one this project has
drawn consistently since Chapter 5/6: a real interactive OAuth consent
flow (opens a real browser against a real Google account) and a real
network call to the live Gmail API. Everything up to that boundary --
fast-fail validation, error translation from a real HttpError into this
project's own typed exceptions -- is tested for real, using the actual
`googleapiclient`/`google-auth` libraries (the optional `email` dependency
group) against a hand-built fake service object, never a real network call.

Tests needing the optional dependency group skip cleanly (`importorskip`)
in an environment where `uv sync --extra email` hasn't been run, rather
than failing the whole suite over an intentionally-optional dependency.
"""

import pytest

from police_thief.services.gmail_oauth import GmailOAuthError, load_credentials

googleapiclient = pytest.importorskip("googleapiclient")


def test_load_credentials_fails_fast_with_no_import_when_neither_file_exists(tmp_path):
    """Neither credentials.json nor token.json exist -- this must be
    detectable without ever importing the optional Google libraries."""
    with pytest.raises(GmailOAuthError, match="neither"):
        load_credentials(tmp_path / "credentials.json", tmp_path / "token.json")


def test_load_credentials_raises_a_clear_error_on_a_malformed_token_file(tmp_path):
    token_path = tmp_path / "token.json"
    token_path.write_text("not valid json at all", encoding="utf-8")
    with pytest.raises(GmailOAuthError, match="not valid JSON"):
        load_credentials(tmp_path / "credentials.json", token_path)


def test_get_service_raises_gmail_oauth_error_not_a_raw_exception(tmp_path):
    from police_thief.services.gmail_oauth import get_service

    with pytest.raises(GmailOAuthError):
        get_service(tmp_path / "credentials.json", tmp_path / "token.json")


def _make_http_error(status: int):
    import httplib2
    from googleapiclient.errors import HttpError

    resp = httplib2.Response({"status": status})
    return HttpError(resp, b"error body")


def test_transport_for_service_returns_the_real_send_response_on_success():
    from unittest.mock import MagicMock

    from police_thief.services.gmail_oauth import _transport_for_service

    service = MagicMock()
    service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
        "id": "msg1"
    }
    transport = _transport_for_service(service)

    assert transport("rawbase64") == {"id": "msg1"}
    service.users.return_value.messages.return_value.send.assert_called_once_with(
        userId="me", body={"raw": "rawbase64"}
    )


def test_transport_for_service_translates_http_429_to_rate_limited_error():
    from unittest.mock import MagicMock

    from police_thief.services.gmail_oauth import _transport_for_service
    from police_thief.services.gmail_report_sender import GmailRateLimitedError

    service = MagicMock()
    service.users.return_value.messages.return_value.send.return_value.execute.side_effect = (
        _make_http_error(429)
    )
    transport = _transport_for_service(service)

    with pytest.raises(GmailRateLimitedError):
        transport("rawbase64")


def test_transport_for_service_translates_other_http_errors_to_send_error():
    from unittest.mock import MagicMock

    from police_thief.services.gmail_oauth import _transport_for_service
    from police_thief.services.gmail_report_sender import GmailSendError

    service = MagicMock()
    service.users.return_value.messages.return_value.send.return_value.execute.side_effect = (
        _make_http_error(500)
    )
    transport = _transport_for_service(service)

    with pytest.raises(GmailSendError):
        transport("rawbase64")


def test_scopes_are_send_only_per_the_least_privilege_mandate():
    """docs/tasks.md App. A Sec. 12.1.3/12.2.3: gmail.send only, never a
    broader scope like gmail.modify -- deliberately narrower than the
    scope used in the prior project this flow was ported from."""
    from police_thief.services.gmail_oauth import SCOPES

    assert SCOPES == ["https://www.googleapis.com/auth/gmail.send"]


def test_build_gmail_api_transport_propagates_credential_loading_failure(tmp_path):
    from police_thief.services.gmail_oauth import build_gmail_api_transport

    with pytest.raises(GmailOAuthError):
        build_gmail_api_transport(tmp_path / "credentials.json", tmp_path / "token.json")


def test_load_credentials_returns_an_already_valid_cached_token_without_touching_the_flow(
    tmp_path, monkeypatch
):
    """A valid, unexpired cached token must short-circuit straight through --
    never touching InstalledAppFlow's real interactive browser consent flow,
    which is the one piece of this module that genuinely cannot run inside
    an automated session."""
    from unittest.mock import MagicMock

    from google.oauth2.credentials import Credentials

    token_path = tmp_path / "token.json"
    token_path.write_text("{}", encoding="utf-8")
    fake_creds = MagicMock()
    fake_creds.expired = False
    fake_creds.valid = True
    monkeypatch.setattr(Credentials, "from_authorized_user_file", lambda *a, **k: fake_creds)

    result = load_credentials(tmp_path / "credentials.json", token_path)

    assert result is fake_creds


def test_get_service_builds_a_real_offline_discovery_client_for_a_valid_cached_token(
    tmp_path, monkeypatch
):
    """googleapiclient's static discovery document is bundled, so a genuine
    Resource object can be built and inspected without any real network
    call or real OAuth consent -- only the actual message-send call is the
    untestable network boundary."""
    from unittest.mock import MagicMock

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import Resource

    from police_thief.services.gmail_oauth import get_service

    token_path = tmp_path / "token.json"
    token_path.write_text("{}", encoding="utf-8")
    fake_creds = MagicMock()
    fake_creds.expired = False
    fake_creds.valid = True
    monkeypatch.setattr(Credentials, "from_authorized_user_file", lambda *a, **k: fake_creds)

    service = get_service(tmp_path / "credentials.json", token_path)

    assert isinstance(service, Resource)


def test_load_credentials_refreshes_an_expired_token_with_a_refresh_token(tmp_path, monkeypatch):
    """An expired-but-refreshable cached token must call refresh() rather
    than falling through to the interactive consent flow."""
    from unittest.mock import MagicMock

    from google.oauth2.credentials import Credentials

    token_path = tmp_path / "token.json"
    token_path.write_text("{}", encoding="utf-8")
    credentials_path = tmp_path / "credentials.json"
    credentials_path.write_text("{}", encoding="utf-8")
    fake_creds = MagicMock()
    fake_creds.expired = True
    fake_creds.refresh_token = "a-refresh-token"
    fake_creds.valid = True
    monkeypatch.setattr(Credentials, "from_authorized_user_file", lambda *a, **k: fake_creds)

    result = load_credentials(credentials_path, token_path)

    assert fake_creds.refresh.called
    assert result is fake_creds


def test_load_credentials_runs_the_consent_flow_and_writes_a_fresh_token_when_none_is_cached(
    tmp_path, monkeypatch
):
    """No cached token at all -> the one-time interactive consent flow runs
    (fully mocked here -- no real browser opens) and the resulting
    credentials are persisted to token_path for next time."""
    from unittest.mock import MagicMock

    from google_auth_oauthlib.flow import InstalledAppFlow

    token_path = tmp_path / "token.json"  # does not exist yet
    credentials_path = tmp_path / "credentials.json"
    credentials_path.write_text("{}", encoding="utf-8")
    fake_new_creds = MagicMock()
    fake_new_creds.to_json.return_value = '{"fake": true}'
    fake_flow = MagicMock()
    fake_flow.run_local_server.return_value = fake_new_creds
    monkeypatch.setattr(InstalledAppFlow, "from_client_secrets_file", lambda *a, **k: fake_flow)

    result = load_credentials(credentials_path, token_path)

    assert fake_flow.run_local_server.called
    assert token_path.is_file()
    assert token_path.read_text(encoding="utf-8") == '{"fake": true}'
    assert result is fake_new_creds


def test_load_credentials_raises_when_the_cached_token_is_invalid_and_no_credentials_file_exists(
    tmp_path, monkeypatch
):
    """An invalid, non-refreshable cached token with no credentials.json to
    re-authorize against must fail with a clear, actionable message rather
    than attempting (and crashing inside) the consent flow."""
    from unittest.mock import MagicMock

    from google.oauth2.credentials import Credentials

    token_path = tmp_path / "token.json"
    token_path.write_text("{}", encoding="utf-8")
    fake_creds = MagicMock()
    fake_creds.expired = False
    fake_creds.valid = False
    monkeypatch.setattr(Credentials, "from_authorized_user_file", lambda *a, **k: fake_creds)

    with pytest.raises(GmailOAuthError, match="does not.*exist to re-authorize"):
        load_credentials(tmp_path / "credentials.json", token_path)


def test_build_gmail_api_transport_returns_a_callable_transport_for_a_valid_cached_token(
    tmp_path, monkeypatch
):
    from unittest.mock import MagicMock

    from google.oauth2.credentials import Credentials

    from police_thief.services.gmail_oauth import build_gmail_api_transport

    token_path = tmp_path / "token.json"
    token_path.write_text("{}", encoding="utf-8")
    fake_creds = MagicMock()
    fake_creds.expired = False
    fake_creds.valid = True
    monkeypatch.setattr(Credentials, "from_authorized_user_file", lambda *a, **k: fake_creds)

    transport = build_gmail_api_transport(tmp_path / "credentials.json", token_path)

    assert callable(transport)
