# Copyright 2026 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""Helpers for interpreting QRadar AQL validator responses."""

from typing import Any, Dict, List

import httpx


MESSAGE_KEYS = ("error_messages", "messages", "warnings", "errors")


def parse_aql_validation_response(response: httpx.Response) -> Dict[str, Any]:
    """Parse QRadar's AQL validator response into a stable validation result."""
    payload = _safe_json_payload(response)
    messages = normalize_validation_messages(payload)

    if response.status_code == 422:
        status_message = {
            "severity": "ERROR",
            "message": "QRadar AQL validation failed",
        }
        messages = [status_message, *messages] if messages else [status_message]
        return {"valid": False, "messages": messages, "details": payload}

    if response.status_code >= 400:
        status_message = {
            "severity": "ERROR",
            "message": f"QRadar AQL validator returned HTTP {response.status_code}",
        }
        if messages:
            messages = [status_message, *messages]
        else:
            messages = [status_message]
        return {"valid": False, "messages": messages, "details": payload}

    has_error = any(
        str(message.get("severity", "")).upper() == "ERROR"
        for message in messages
    )
    return {
        "valid": not has_error,
        "messages": messages,
        "warnings": [
            message for message in messages
            if str(message.get("severity", "")).upper() in {"WARN", "WARNING"}
        ],
        "details": payload,
    }


def normalize_validation_messages(payload: Any) -> List[Dict[str, Any]]:
    """Normalize known QRadar validator message shapes into dictionaries."""
    if payload is None or payload == "":
        return []

    if isinstance(payload, list):
        return _normalize_message_list(payload)

    if isinstance(payload, dict):
        if _looks_like_message(payload):
            return [_normalize_message(payload, default_severity="ERROR")]

        messages: List[Dict[str, Any]] = []
        for key in MESSAGE_KEYS:
            if key not in payload:
                continue
            default_severity = _default_severity_for_key(key)
            messages.extend(_normalize_message_list(payload[key], default_severity=default_severity))

        if messages:
            return messages

        if "message" in payload:
            message = {
                "severity": "ERROR",
                "message": str(payload["message"]),
            }
            if "details" in payload:
                message["details"] = payload["details"]
            return [message]

    return [{
        "severity": "WARN",
        "message": str(payload),
    }]


def format_validation_messages(messages: List[Dict[str, Any]]) -> str:
    """Format normalized validator messages for tool text responses."""
    lines = []
    for message in messages:
        severity = str(message.get("severity", "INFO")).upper()
        text = str(message.get("message", message))
        line = f"- {severity}: {text}"
        if "details" in message:
            line += f" Details: {message['details']}"
        lines.append(line)
    return "\n".join(lines)


def _safe_json_payload(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text or None


def _normalize_message_list(value: Any, default_severity: str = "INFO") -> List[Dict[str, Any]]:
    if isinstance(value, list):
        return [_normalize_message(item, default_severity=default_severity) for item in value]
    if value is None:
        return []
    return [_normalize_message(value, default_severity=default_severity)]


def _normalize_message(message: Any, default_severity: str = "INFO") -> Dict[str, Any]:
    if isinstance(message, dict):
        normalized = dict(message)
        normalized.setdefault("severity", default_severity)
        if "message" not in normalized:
            normalized["message"] = str(message)
        return normalized
    return {
        "severity": default_severity,
        "message": str(message),
    }


def _looks_like_message(payload: Dict[str, Any]) -> bool:
    return "severity" in payload or "message" in payload


def _default_severity_for_key(key: str) -> str:
    if key in {"error_messages", "errors"}:
        return "ERROR"
    if key == "warnings":
        return "WARN"
    return "INFO"
