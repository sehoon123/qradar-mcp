"""Tests for Cancel Ariel Search Tool."""

import json
from unittest.mock import AsyncMock

import httpx
import pytest

from qradar_mcp.tools.ariel.cancel_ariel_search import CancelArielSearchTool


@pytest.fixture
def tool():
    """Create a CancelArielSearchTool instance for testing."""
    return CancelArielSearchTool()


def test_cancel_ariel_search_properties(tool):
    """Test cancel tool metadata."""
    assert tool.name == "cancel_ariel_search"
    assert tool.http_verb == "POST"
    assert tool.tool_group == "ariel"
    assert "search_id" in tool.input_schema["properties"]


@pytest.mark.asyncio
async def test_cancel_ariel_search(tool):
    """Test canceling an Ariel search sets status=CANCELED."""
    request = httpx.Request("POST", "https://qradar.local/api/ariel/searches/s123")
    response = httpx.Response(
        200,
        json={"search_id": "s123", "status": "CANCELED"},
        request=request,
    )

    tool.client = AsyncMock()
    tool.client.post = AsyncMock(return_value=response)

    result = await tool.execute({"search_id": "s123"})

    assert result.get("isError") is not True
    payload = json.loads(result["content"][0]["text"])
    assert payload["status"] == "CANCELED"
    tool.client.post.assert_called_once_with(
        "ariel/searches/s123",
        params={"status": "CANCELED"},
    )


@pytest.mark.asyncio
async def test_cancel_ariel_search_requires_search_id(tool):
    """Test search_id is required."""
    result = await tool.execute({})

    assert result["isError"] is True
    assert "search_id is required" in result["content"][0]["text"].lower()
