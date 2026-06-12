"""Tests for MCP endpoint access-token middleware."""

import httpx
import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from qradar_mcp.utils.mcp_access_auth import MCPAccessTokenMiddleware


async def _ok(_request):
    return JSONResponse({"ok": True})


def _app(access_token="secret"):
    app = Starlette(routes=[
        Route("/mcp", _ok, methods=["GET"]),
        Route("/healthz", _ok, methods=["GET"]),
    ])
    app.add_middleware(MCPAccessTokenMiddleware, access_token=access_token)
    return app


@pytest.mark.asyncio
async def test_mcp_path_requires_access_token():
    """Test protected MCP paths reject missing tokens."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_app()),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/mcp")

    assert response.status_code == 401
    assert response.json()["code"] == "MCP_UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_mcp_path_accepts_bearer_access_token():
    """Test Authorization: Bearer works for MCP access auth."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_app()),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/mcp", headers={"Authorization": "Bearer secret"})

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_mcp_path_accepts_explicit_access_token_header():
    """Test X-MCP-Token works for MCP access auth."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_app()),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/mcp", headers={"X-MCP-Token": "secret"})

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_path_bypasses_mcp_access_token():
    """Test health endpoints remain usable without MCP token."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_app()),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
