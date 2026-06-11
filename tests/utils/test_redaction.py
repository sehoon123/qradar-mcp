"""Tests for shared log redaction policy."""

from qradar_mcp.utils.redaction import sanitize_for_logging


def test_sanitize_for_logging_redacts_nested_credentials():
    """Credential-like keys are redacted recursively, including lists."""
    data = {
        "Authorization": "Bearer secret",
        "nested": {
            "authorized_service_token": "token",
            "items": [
                {"QRadarCSRF": "csrf"},
                {"normal": "value"},
            ],
        },
    }

    sanitized = sanitize_for_logging(data)

    assert sanitized["Authorization"] == "***REDACTED***"
    assert sanitized["nested"]["authorized_service_token"] == "***REDACTED***"
    assert sanitized["nested"]["items"][0]["QRadarCSRF"] == "***REDACTED***"
    assert sanitized["nested"]["items"][1]["normal"] == "value"


def test_sanitize_for_logging_summarizes_soc_content():
    """AQL, filters, and note text are summarized without raw content."""
    data = {
        "query_expression": "SELECT * FROM events WHERE username = 'alice'",
        "filter": "sourceip = '10.0.0.1'",
        "note_text": "Investigating host workstation-01",
    }

    sanitized = sanitize_for_logging(data)

    for key, raw_value in data.items():
        assert sanitized[key]["redacted"] is True
        assert sanitized[key]["reason"] == "soc_content"
        assert sanitized[key]["length"] == len(raw_value)
        assert len(sanitized[key]["sha256"]) == 16
        assert raw_value not in str(sanitized[key])


def test_sanitize_for_logging_truncates_non_sensitive_long_strings():
    """Long benign strings are truncated instead of fully redacted."""
    sanitized = sanitize_for_logging({"description": "x" * 1005})

    assert len(sanitized["description"]) == 1014
    assert sanitized["description"].endswith("...[truncated]")
