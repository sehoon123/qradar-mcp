"""Tests for the offense Ariel event investigation workflow."""

import pytest
from unittest.mock import AsyncMock

import httpx

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


def test_input_schema_requires_positive_offense_id(tool):
    """Test offense IDs are positive integers."""
    assert tool.input_schema["properties"]["offense_id"]["minimum"] == 1


def test_build_aql_rejects_zero_offense_id(tool):
    """Test offense_id=0 is rejected before AQL construction."""
    with pytest.raises(ValueError, match="offense_id must be between 1"):
        tool._build_aql({"offense_id": 0})


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


@pytest.mark.asyncio
async def test_validate_aql_treats_error_severity_as_invalid(tool):
    """Test composite workflow honors validator error severity in HTTP 200 responses."""
    response = httpx.Response(
        200,
        json={
            "error_messages": [
                {"severity": "ERROR", "message": "Unexpected token"}
            ]
        },
        request=httpx.Request("POST", "http://test"),
    )
    tool.client = AsyncMock()
    tool.client.post = AsyncMock(return_value=response)

    validation = await tool._validate_aql("SELECT * FORM events")

    assert validation["valid"] is False
    assert validation["messages"][0]["severity"] == "ERROR"


@pytest.mark.asyncio
async def test_incomplete_search_returns_public_capability_guidance(tool):
    """Test timeout guidance does not reference hidden default tools as required."""
    tool.client = AsyncMock()
    tool.client.get = AsyncMock(side_effect=[
        httpx.Response(
            200,
            json={"id": 123, "status": "OPEN"},
            request=httpx.Request("GET", "http://test/offense"),
        ),
        httpx.Response(
            200,
            json={"status": "EXECUTING"},
            request=httpx.Request("GET", "http://test/search"),
        ),
    ])
    tool.client.post = AsyncMock(side_effect=[
        httpx.Response(
            200,
            json=None,
            request=httpx.Request("POST", "http://test/validate"),
        ),
        httpx.Response(
            201,
            json={"search_id": "abc-123", "status": "EXECUTING"},
            request=httpx.Request("POST", "http://test/searches"),
        ),
    ])

    result = await tool.execute({
        "offense_id": 123,
        "max_poll_attempts": 1,
        "poll_interval_seconds": 0,
    })

    payload = result["content"][0]["json"]
    assert payload["search_id"] == "abc-123"
    assert payload["recommended_next_call"]["tool"] == "investigate_offense_events"
    assert "get_ariel_search_status/results" not in payload["warnings"][0]
