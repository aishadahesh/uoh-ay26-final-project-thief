"""Real Gmail API transport via OAuth 2.0 (Chapter 9 / App. A).

Closes the one deferred piece of Chapter 9's Gmail pipeline. Everything in
`gmail_report_sender.py` -- MIME construction, JSON-only enforcement,
base64url encoding, Gatekeeper gating, 429 backoff -- was already real and
fully tested against an injectable `Transport` callable
(`Callable[[str], dict]`). This module is that transport's one real
implementation: `build_gmail_api_transport()` returns a callable that
sends through a genuine, OAuth-authorized Gmail API service and slots
directly into `send_match_report` with no change to that already-tested
pipeline.

The OAuth flow itself (`InstalledAppFlow` + a cached, auto-refreshed
`token.json`) is the exact pattern already proven working, for this same
Google account, in a separate prior course project -- ported here with one
deliberate correction: App. A Sec. 12.1.3/12.2.3 mandates the `gmail.send`
scope only ("Least Privilege... never a broader scope like mail.google.com
or gmail.modify"), narrower than that prior project's `gmail.modify`.

Requires the optional `email` dependency group (`uv sync --extra email`)
and a real `credentials.json` (never committed -- see `.gitignore`) placed
at the project root. The one-time interactive consent flow that produces
`token.json` opens a real browser against a real Google account, so it
cannot be run inside an automated coding session -- completing it once is
a manual activation step for you, documented in
`docs/PRD_gmail_gatekeeper.md`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from police_thief.services.gmail_report_sender import (
    GmailRateLimitedError,
    GmailSendError,
    Transport,
)

if TYPE_CHECKING:
    from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
HTTP_TOO_MANY_REQUESTS = 429


class GmailOAuthError(RuntimeError):
    """Raised when the OAuth dependency, credentials, or token setup is missing/invalid."""


def load_credentials(credentials_path: Path, token_path: Path) -> Credentials:
    """Load a cached token (refreshing it if expired), or run the one-time
    interactive consent flow if no valid token exists yet.

    Fails fast, before importing anything, if neither file exists at all --
    that failure mode needs no optional dependency installed to detect or
    to test.
    """
    if not token_path.is_file() and not credentials_path.is_file():
        raise GmailOAuthError(
            f"neither {token_path} nor {credentials_path} exist -- download credentials.json "
            "from the Google Cloud Console (docs/tasks.md App. A, Step D) and place it at the "
            "project root; never commit it (see .gitignore)"
        )
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise GmailOAuthError(
            "google-api-python-client/google-auth-oauthlib not installed; run `uv sync --extra email`"
        ) from exc

    try:
        creds = (
            Credentials.from_authorized_user_file(str(token_path), SCOPES)
            if token_path.is_file()
            else None
        )
    except ValueError as exc:
        # A malformed/corrupted token.json otherwise surfaces as a raw
        # JSONDecodeError/ValueError -- caught here and re-raised as our
        # own typed error so a bad cached token degrades to "re-authorize
        # via credentials.json," not a crash.
        raise GmailOAuthError(
            f"token at {token_path} is not valid JSON/credentials data: {exc}"
        ) from exc
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not credentials_path.is_file():
            raise GmailOAuthError(
                f"token at {token_path} is missing/invalid and {credentials_path} does not "
                "exist to re-authorize -- download it from the Google Cloud Console"
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
        creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def get_service(credentials_path: Path, token_path: Path) -> Any:
    """Build a real, `gmail.send`-authorized Gmail API service object."""
    try:
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise GmailOAuthError(
            "google-api-python-client not installed; run `uv sync --extra email`"
        ) from exc
    creds = load_credentials(credentials_path, token_path)
    return build("gmail", "v1", credentials=creds)


def _transport_for_service(service: Any) -> Transport:
    """Wrap an already-authorized Gmail API service object as a `Transport`.

    Split from `build_gmail_api_transport` so the HTTP-429/error-translation
    logic can be tested directly against a hand-built fake service object,
    without needing real OAuth credentials to reach this code path at all.
    """

    def transport(raw_message: str) -> dict:
        from googleapiclient.errors import HttpError

        try:
            return service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
        except HttpError as exc:
            status = getattr(getattr(exc, "resp", None), "status", None)
            if status == HTTP_TOO_MANY_REQUESTS:
                raise GmailRateLimitedError(str(exc)) from exc
            raise GmailSendError(str(exc)) from exc

    return transport


def build_gmail_api_transport(credentials_path: Path, token_path: Path) -> Transport:
    """Return a `Transport` backed by the real Gmail API, ready to pass
    straight into `gmail_report_sender.send_match_report`.

    HTTP 429 from the API is translated into `GmailRateLimitedError` (so
    the caller's existing backoff logic handles it); any other API error
    becomes `GmailSendError` -- the same two exception types
    `send_match_report` already knows how to handle, unchanged.
    """
    service = get_service(credentials_path, token_path)
    return _transport_for_service(service)
