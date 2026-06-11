# Copyright 2026 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shared log and audit redaction helpers."""

from __future__ import annotations

import hashlib
from typing import Any


REDACTED_VALUE = "***REDACTED***"
TRUNCATION_SUFFIX = "...[truncated]"

_CREDENTIAL_KEY_FRAGMENTS = (
    "password",
    "token",
    "secret",
    "api_key",
    "apikey",
    "credential",
    "authorization",
    "authorized_service_token",
    "qradarcsrf",
    "csrf",
    "sec_token",
)

_CREDENTIAL_KEY_EXACT = {
    "auth",
    "sec",
    "cookie",
    "set-cookie",
}

_SOC_CONTENT_KEYS = {
    "aql",
    "filter",
    "note",
    "notes",
    "note_text",
    "query",
    "query_expression",
    "search_query",
}


def sanitize_for_logging(data: Any, *, max_string_length: int = 1000) -> Any:
    """
    Return a JSON-safe copy of data for structured logs and audit records.

    Credential fields are fully redacted. SOC investigation text such as AQL,
    filters, and notes is replaced with stable metadata so operators can
    correlate events without storing raw investigative content.
    """
    return _sanitize_value(data, key=None, max_string_length=max_string_length)


def sanitize_for_audit(data: Any, *, max_string_length: int = 1000) -> Any:
    """Alias for audit call sites that should use the shared policy."""
    return sanitize_for_logging(data, max_string_length=max_string_length)


def _sanitize_value(data: Any, *, key: str | None, max_string_length: int) -> Any:
    if isinstance(data, dict):
        return {
            item_key: _sanitize_value(
                item_value,
                key=str(item_key),
                max_string_length=max_string_length
            )
            for item_key, item_value in data.items()
        }

    if isinstance(data, (list, tuple)):
        return [
            _sanitize_value(item, key=None, max_string_length=max_string_length)
            for item in data
        ]

    if key and _is_credential_key(key):
        return REDACTED_VALUE

    if isinstance(data, str):
        if key and _is_soc_content_key(key):
            return _redacted_content_summary(data)
        if len(data) > max_string_length:
            return data[:max_string_length] + TRUNCATION_SUFFIX

    return data


def _is_credential_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    if normalized in _CREDENTIAL_KEY_EXACT:
        return True
    return any(fragment in normalized for fragment in _CREDENTIAL_KEY_FRAGMENTS)


def _is_soc_content_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return normalized in _SOC_CONTENT_KEYS


def _redacted_content_summary(value: str) -> dict[str, Any]:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return {
        "redacted": True,
        "reason": "soc_content",
        "length": len(value),
        "sha256": digest[:16],
    }
