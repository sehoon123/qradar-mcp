"""Tests for discover_qradar_endpoints."""

from unittest.mock import AsyncMock

import httpx
import pytest

from qradar_mcp.tools.help.discover_qradar_endpoints import DiscoverQradarEndpointsTool


@pytest.mark.asyncio
async def test_discover_qradar_endpoints_returns_structured_json_by_default():
    """Default response should be structured JSON, not a JSON text blob."""
    tool = DiscoverQradarEndpointsTool()
    response = httpx.Response(
        200,
        json=[
            {
                "id": 1,
                "path": "/siem/offenses",
                "http_method": "GET",
                "summary": "List offenses",
            }
        ],
        request=httpx.Request("GET", "https://qradar.local/api/help/endpoints"),
    )
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=response)
    tool.client = mock_client

    result = await tool._execute_impl({"limit": 10, "offset": 5})

    assert result["content"][0]["type"] == "json"
    payload = result["content"][0]["json"]
    assert payload["count"] == 1
    assert payload["limit"] == 10
    assert payload["offset"] == 5
    assert payload["endpoints"][0]["path"] == "/siem/offenses"
