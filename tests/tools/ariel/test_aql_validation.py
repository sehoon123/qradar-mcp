"""Tests for AQL validation response parsing."""

import httpx

from qradar_mcp.tools.ariel.aql_validation import parse_aql_validation_response


def test_null_payload_is_valid():
    """QRadar returns null/empty payload when validation succeeds."""
    response = httpx.Response(200, json=None, request=httpx.Request("POST", "http://test"))

    parsed = parse_aql_validation_response(response)

    assert parsed["valid"] is True
    assert parsed["messages"] == []


def test_error_severity_in_200_payload_is_invalid():
    """HTTP 200 can still carry validator error messages."""
    response = httpx.Response(
        200,
        json={
            "error_messages": [
                {
                    "severity": "ERROR",
                    "message": "Unexpected token",
                }
            ]
        },
        request=httpx.Request("POST", "http://test"),
    )

    parsed = parse_aql_validation_response(response)

    assert parsed["valid"] is False
    assert parsed["messages"][0]["severity"] == "ERROR"


def test_warning_severity_in_200_payload_is_valid_with_warnings():
    """Warning validator messages should not block execution by themselves."""
    response = httpx.Response(
        200,
        json={
            "error_messages": [
                {
                    "severity": "WARN",
                    "message": "Query may be expensive",
                }
            ]
        },
        request=httpx.Request("POST", "http://test"),
    )

    parsed = parse_aql_validation_response(response)

    assert parsed["valid"] is True
    assert parsed["warnings"][0]["message"] == "Query may be expensive"


def test_422_payload_is_invalid():
    """422 responses are invalid regardless of payload shape."""
    response = httpx.Response(
        422,
        json={"message": "Syntax error", "details": {"line": 1}},
        request=httpx.Request("POST", "http://test"),
    )

    parsed = parse_aql_validation_response(response)

    assert parsed["valid"] is False
    assert parsed["messages"][0]["severity"] == "ERROR"
    assert parsed["details"]["message"] == "Syntax error"
