"""The end-of-game audit envelope and the reciprocal record verification."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from police_thief.services.protocol_constants import (
    WIRE_ROLES,
    NetworkProtocolError,
)
from police_thief.services.protocol_crypto import verify_record


@dataclass(frozen=True)
class AuditPayload:
    sender: str
    records: list[dict]
    result_claim: str
    token_usage: dict | None = None
    consensus_sha: str | None = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        if self.consensus_sha is None:
            payload.pop("consensus_sha")
        return payload

    @classmethod
    def from_dict(cls, data: dict) -> AuditPayload:
        try:
            payload = cls(**data)
        except (TypeError, ValueError) as exc:
            raise NetworkProtocolError(f"malformed audit payload: {exc}") from exc
        if payload.sender not in WIRE_ROLES.values() or not isinstance(payload.records, list):
            raise NetworkProtocolError("invalid audit sender or records")
        if payload.consensus_sha is not None and (
            not isinstance(payload.consensus_sha, str)
            or len(payload.consensus_sha) != 64
            or any(char not in "0123456789abcdef" for char in payload.consensus_sha)
        ):
            raise NetworkProtocolError("consensus_sha must be 64 lowercase hexadecimal characters")
        return payload


@dataclass(frozen=True)
class AuditVerification:
    """Detailed audit verdict separating malformed evidence from forgery."""

    verified: bool
    failed_steps: tuple[int, ...]
    cryptographic_failure: bool
    errors: tuple[str, ...]


def audit_records(
    records: list[dict],
    expected_commits: dict[int, str],
    *,
    match_id: str | None = None,
    require_step0: bool = False,
) -> tuple[bool, list[int]]:
    verdict = verify_audit_records(
        records, expected_commits, match_id=match_id, require_step0=require_step0,
    )
    return verdict.verified, list(verdict.failed_steps)


def verify_audit_records(
    records: list[dict],
    expected_commits: dict[int, str],
    *,
    match_id: str | None = None,
    require_step0: bool = False,
) -> AuditVerification:
    """Return an evidence-rich audit verdict for outcome adjudication."""
    failed: list[int] = []
    errors: list[str] = []
    cryptographic_failure = False
    seen: set[int] = set()
    saw_step0 = False
    for index, record in enumerate(records):
        try:
            step = int(record["payload"]["step"])
            commit = str(record["commit"])
        except (KeyError, TypeError, ValueError):
            failed.append(-1)
            errors.append(
                f"records[{index}] must contain payload.step and top-level commit"
            )
            continue
        if step == 0:
            duplicate_step0 = saw_step0
            correct_type = record["payload"].get("type") == "system_spec"
            valid_commit = verify_record(record)
            valid_step0 = not duplicate_step0 and correct_type and valid_commit
            saw_step0 = True
            if not valid_step0:
                failed.append(0)
                if duplicate_step0:
                    errors.append("duplicate Step-0 system_spec record")
                if not correct_type:
                    errors.append("Step 0 must have payload.type='system_spec'")
                if not valid_commit:
                    cryptographic_failure = True
                    errors.append("Step-0 nonce/commit verification failed")
            continue
        if step in seen:
            failed.append(step)
            errors.append(f"duplicate revealed step {step}")
            continue
        seen.add(step)
        record_match_id = record.get("payload", {}).get("match_id")
        expected = expected_commits.get(step)
        if expected is None:
            failed.append(step)
            errors.append(f"unexpected revealed step {step} had no live commitment")
            continue
        if expected != commit:
            failed.append(step)
            cryptographic_failure = True
            errors.append(f"step {step} does not match its live commitment")
            continue
        if not verify_record(record):
            failed.append(step)
            cryptographic_failure = True
            errors.append(f"step {step} nonce/commit verification failed")
            continue
        if match_id is not None and record_match_id != match_id:
            failed.append(step)
            errors.append(f"step {step} belongs to a different match")
    missing = sorted(set(expected_commits) - seen)
    if missing:
        failed.extend(missing)
        cryptographic_failure = True
        errors.extend(f"missing reveal for committed step {step}" for step in missing)
    if require_step0 and not saw_step0:
        failed.append(0)
        errors.append("required Step-0 system_spec record is missing")
    return AuditVerification(
        verified=not failed,
        failed_steps=tuple(failed),
        cryptographic_failure=cryptographic_failure,
        errors=tuple(errors),
    )
