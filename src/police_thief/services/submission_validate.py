"""Validating a finished submission directory: syntax, schema, hashes,
names, values, cross-file joins, and privacy."""

from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path
from typing import Any

from police_thief.services.submission_identity import derive_game_uid
from police_thief.services.submission_schema import (
    ALLOWED_RESULTS,
    ALLOWED_ROLES,
    GIT_RE,
    GITHUB_RE,
    SCHEMA_VERSION,
    SHA256_RE,
    SIGNED_TERM_FIELDS,
    SubmissionValidationError,
    _error,
    _is_int,
    _iso,
    _read,
    _required,
    canonical_bytes,
    canonical_hash,
    submission_filenames,
)
from police_thief.shared.game_config import FIXED_TIE_SCORE


def validate_submission_directory(
    directory: Path, game_id: str,
) -> tuple[list[SubmissionValidationError], list[Path]]:
    """Validate syntax, schema, hashes, names, values, joins, and privacy."""
    errors: list[SubmissionValidationError] = []
    declaration_path = directory / f"declaration_{game_id}.json"
    declaration = _read(declaration_path, errors)
    if not isinstance(declaration, dict):
        return errors, []
    _required(declaration, declaration_path.name, {
        "schema_version", "report_type", "declaration_type", "game_id", "game_uid",
        "links", "timezone", "game_started_at", "num_sub_games",
        "max_tokens_per_game", "groups",
    }, errors)
    num_games = declaration.get("num_sub_games")
    if not _is_int(num_games) or num_games < 1:
        errors.append(_error(declaration_path.name, "num_sub_games", "positive integer", num_games, "wrong_type_or_value"))
        return errors, []
    paths = [directory / name for name in submission_filenames(game_id, num_games)]
    documents: list[tuple[str, dict[str, Any]]] = []
    for path in paths:
        doc = declaration if path == declaration_path else _read(path, errors)
        if isinstance(doc, dict):
            documents.append((path.name, doc))
    try:
        uid = str(uuid.UUID(str(declaration.get("game_uid"))))
    except (ValueError, TypeError, AttributeError):
        uid = ""
        errors.append(_error(declaration_path.name, "game_uid", "UUID string", declaration.get("game_uid"), "invalid_value"))
    for filename, doc in documents:
        for field, expected in (("schema_version", SCHEMA_VERSION), ("game_id", game_id), ("game_uid", uid)):
            if doc.get(field) != expected:
                errors.append(_error(filename, field, expected, doc.get(field), "cross_file_mismatch"))
    groups = declaration.get("groups")
    participants = list(groups.values()) if isinstance(groups, dict) else []
    if len(participants) != 2:
        errors.append(_error(declaration_path.name, "groups", "exactly two group objects", groups, "invalid_value"))
    group_ids: list[str] = []
    for index, group in enumerate(participants, 1):
        field = f"groups.group_{index}"
        if not isinstance(group, dict):
            errors.append(_error(declaration_path.name, field, "object", type(group).__name__, "wrong_type"))
            continue
        mandatory = {"group_id", "group_name", "members", "repos", "mcp_servers", "llm_model", "hardware_spec", "github_commit", "code_version", "signature"}
        _required(group, declaration_path.name, mandatory, errors)
        group_ids.append(group.get("group_id"))
        if not isinstance(group.get("members"), list) or not group.get("members"):
            errors.append(_error(declaration_path.name, f"{field}.members", "non-empty array of names", group.get("members"), "invalid_value"))
        repos = group.get("repos")
        if not isinstance(repos, dict) or set(repos) != {"cop", "thief"}:
            errors.append(_error(declaration_path.name, f"{field}.repos", "object with cop and thief", repos, "invalid_value"))
        elif any(not GITHUB_RE.match(str(url)) for url in repos.values()):
            errors.append(_error(declaration_path.name, f"{field}.repos", "GitHub repository URLs", repos, "invalid_value"))
        if not GIT_RE.match(str(group.get("github_commit", ""))):
            errors.append(_error(declaration_path.name, f"{field}.github_commit", "40 lowercase hex characters", group.get("github_commit"), "invalid_value"))
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(group.get("signature", ""))):
            errors.append(_error(declaration_path.name, f"{field}.signature", "sha256:<64 lowercase hex>", group.get("signature"), "invalid_value"))
    if not _iso(declaration.get("game_started_at")):
        errors.append(_error(declaration_path.name, "game_started_at", "ISO-8601 timestamp", declaration.get("game_started_at"), "invalid_value"))

    expected_uid = derive_game_uid(_first_terms(documents), group_ids) if len(group_ids) == 2 and _first_terms(documents) else None
    if expected_uid and uid != expected_uid:
        errors.append(_error(declaration_path.name, "game_uid", expected_uid, uid, "derivation_mismatch"))

    for number in range(1, num_games + 1):
        config_name = f"config_{game_id}_g{number:02d}.json"
        log_name = f"log_{game_id}_g{number:02d}.json"
        config = next((doc for name, doc in documents if name == config_name), None)
        log = next((doc for name, doc in documents if name == log_name), None)
        if config:
            _required(config, config_name, {"schema_version", "game_id", "game_uid", "links", "sub_game_number", "terms", "config_sha256"}, errors)
            if config.get("sub_game_number") != number:
                errors.append(_error(config_name, "sub_game_number", number, config.get("sub_game_number"), "filename_field_mismatch"))
            if not isinstance(config.get("terms"), dict) or set(config.get("terms", {})) != SIGNED_TERM_FIELDS:
                errors.append(_error(config_name, "terms", "14-key signed terms object", config.get("terms"), "invalid_value"))
            elif config.get("config_sha256") != canonical_hash(config["terms"]):
                errors.append(_error(config_name, "config_sha256", canonical_hash(config["terms"]), config.get("config_sha256"), "checksum_mismatch"))
        if log:
            _required(log, log_name, {"schema_version", "game_id", "game_uid", "links", "sub_game_number", "summary", "records"}, errors)
            if log.get("sub_game_number") != number:
                errors.append(_error(log_name, "sub_game_number", number, log.get("sub_game_number"), "filename_field_mismatch"))
            records = log.get("records")
            if not isinstance(records, list):
                errors.append(_error(log_name, "records", "array", type(records).__name__, "wrong_type"))
            else:
                _validate_records(log_name, records, errors)

    result_name = f"result_{game_id}.json"
    result = next((doc for name, doc in documents if name == result_name), None)
    if result:
        _required(result, result_name, {"schema_version", "report_type", "game_id", "game_uid", "links", "timezone", "groups", "num_sub_games", "sub_games", "final_result", "mutual_agreement"}, errors)
        if result.get("report_type") != "final_game_result":
            errors.append(_error(result_name, "report_type", "final_game_result", result.get("report_type"), "invalid_value"))
        rows = result.get("sub_games")
        if not isinstance(rows, list) or len(rows) != num_games:
            errors.append(_error(result_name, "sub_games", f"array of {num_games} rows", rows, "invalid_value"))
        else:
            _validate_result_rows(result_name, rows, group_ids, errors)
            totals = {key: sum(row["score"].get(key, 0) for row in rows) for key in group_ids}
            if len(set(totals.values())) == 1:
                # Tie Rule: a tied cumulative series must carry the fixed
                # tie-score credit for each side (Table 17 row 5).
                totals = {key: value + FIXED_TIE_SCORE for key, value in totals.items()}
            received = (result.get("final_result") or {}).get("total_score")
            if received != totals:
                errors.append(_error(result_name, "final_result.total_score", totals, received, "derived_value_mismatch"))
        agreement = result.get("mutual_agreement")
        if not isinstance(agreement, dict) or agreement.get("confirmed") is not True or not SHA256_RE.match(str(agreement.get("sha256", ""))):
            errors.append(_error(result_name, "mutual_agreement", "confirmed=true and SHA-256 digest", agreement, "invalid_value"))

    forbidden = {"credentials", "credentials_path", "token_path", "refresh_token", "client_secret", "api_key", "private_prompt", "rationale", "opponent_url"}
    for filename, doc in documents:
        for field, value in _walk(doc):
            if field.split(".")[-1].casefold() in forbidden:
                errors.append(_error(filename, field, "private field omitted", value, "private_information_exposed"))
    return errors, paths


def _validate_records(filename: str, records: list[Any], errors: list[SubmissionValidationError]) -> None:
    for index, record in enumerate(records):
        field = f"records[{index}]"
        if not isinstance(record, dict) or set(record) != {"payload", "nonce", "commit"}:
            errors.append(_error(filename, field, "object with payload, nonce, commit", record, "invalid_schema"))
            continue
        payload, nonce, commit = record["payload"], record["nonce"], record["commit"]
        expected = hashlib.sha256(canonical_bytes(payload) + b"|" + str(nonce).encode()).hexdigest()
        if commit != expected:
            errors.append(_error(filename, f"{field}.commit", expected, commit, "commit_mismatch"))
        if not isinstance(payload, dict):
            continue
        role = payload.get("role")
        if role is not None and role not in ALLOWED_ROLES:
            errors.append(_error(filename, f"{field}.payload.role", sorted(ALLOWED_ROLES), role, "invalid_value"))


def _validate_result_rows(filename: str, rows: list[dict[str, Any]], group_ids: list[str], errors: list[SubmissionValidationError]) -> None:
    required = {"sub_game_number", "roles", "started_at", "ended_at", "result", "winner_group", "tie", "steps", "github_commit", "tokens", "score", "log_files", "audit"}
    for index, row in enumerate(rows):
        field = f"sub_games[{index}]"
        if not isinstance(row, dict):
            errors.append(_error(filename, field, "object", type(row).__name__, "wrong_type"))
            continue
        _required(row, filename, required, errors)
        if row.get("result") not in ALLOWED_RESULTS:
            errors.append(_error(filename, f"{field}.result", sorted(ALLOWED_RESULTS), row.get("result"), "invalid_value"))
        if set((row.get("roles") or {}).values()) != ALLOWED_ROLES:
            errors.append(_error(filename, f"{field}.roles", "one police and one thief", row.get("roles"), "invalid_value"))
        if set(row.get("score") or {}) != set(group_ids):
            errors.append(_error(filename, f"{field}.score", f"numeric map for {group_ids}", row.get("score"), "invalid_value"))
        if set(row.get("tokens") or {}) != set(group_ids):
            errors.append(_error(filename, f"{field}.tokens", f"integer map for {group_ids}", row.get("tokens"), "invalid_value"))
        commits = row.get("github_commit") or {}
        if set(commits) != set(group_ids) or any(
            not GIT_RE.fullmatch(str(commits.get(group_id, "")))
            for group_id in group_ids
        ):
            errors.append(_error(filename, f"{field}.github_commit", f"40-hex map for {group_ids}", commits, "invalid_value"))
        for timestamp in ("started_at", "ended_at"):
            if not _iso(row.get(timestamp)):
                errors.append(_error(filename, f"{field}.{timestamp}", "ISO-8601 timestamp", row.get(timestamp), "invalid_value"))


def _walk(value: Any, prefix: str = "$"):
    if isinstance(value, dict):
        for key, item in value.items():
            field = f"{prefix}.{key}"
            yield field, item
            yield from _walk(item, field)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, f"{prefix}[{index}]")


def _first_terms(documents: list[tuple[str, dict[str, Any]]]) -> dict[str, Any] | None:
    for _, doc in documents:
        if isinstance(doc.get("terms"), dict):
            return doc["terms"]
    return None
