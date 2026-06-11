"""Tests for the offense Ariel event investigation workflow."""

import pytest

from qradar_mcp.tools.composite.investigate_offense_events import InvestigateOffenseEventsTool


@pytest.fixture
def tool():
    """Create an InvestigateOffenseEventsTool instance."""
    return InvestigateOffenseEventsTool()


def test_build_aql_uses_safe_defaults(tool):
    """Test default AQL uses bounded limits and safe fields."""
    query = tool._build_aql({"offense_id": 123})

    assert "WHERE INOFFENSE(123)" in query
    assert "LIMIT 100 LAST 360 MINUTES" in query
    assert "QIDDESCRIPTION(qid) AS event_name" in query
    assert "LOGSOURCENAME(logsourceid) AS log_source" in query


def test_build_aql_accepts_allowed_fields(tool):
    """Test explicit fields must come from the allowlist."""
    query = tool._build_aql({
        "offense_id": 123,
        "fields": "starttime, sourceip, destinationip, magnitude",
        "max_events": 25,
        "time_window_minutes": 30,
    })

    assert query.startswith("SELECT starttime, sourceip, destinationip, magnitude FROM events")
    assert "LIMIT 25 LAST 30 MINUTES" in query


def test_build_aql_rejects_unsupported_fields(tool):
    """Test arbitrary SELECT expressions are rejected."""
    with pytest.raises(ValueError, match="Unsupported Ariel event fields"):
        tool._build_aql({
            "offense_id": 123,
            "fields": "starttime, DATEFORMAT(starttime, 'YYYY') AS day",
        })


def test_build_aql_rejects_expensive_limits(tool):
    """Test hard bounds prevent high-cost automatic queries."""
    with pytest.raises(ValueError, match="max_events must be between 1 and 1000"):
        tool._build_aql({"offense_id": 123, "max_events": 10000})

    with pytest.raises(ValueError, match="time_window_minutes must be between 1 and 1440"):
        tool._build_aql({"offense_id": 123, "time_window_minutes": 10080})
