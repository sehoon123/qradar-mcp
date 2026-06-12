#!/usr/bin/env python3
"""
Smoke test for a locally running QRadar MCP server.

The local server reads config.json from the parent directory of the
qradar-mcp checkout. This script follows the same lookup first, then falls
back to a repository-local config.json for older Docker/development setups.
"""

import asyncio
import json
import os
from pathlib import Path

import httpx

try:
    import pytest
except ImportError:  # Allows `python tests/local_mcp_connection.py`.
    pytest = None

if pytest is not None:
    pytestmark = pytest.mark.asyncio


def _load_config():
    repo_root = Path(__file__).resolve().parents[1]
    candidates = [
        repo_root.parent / "config.json",
        repo_root / "config.json",
    ]

    for config_path in candidates:
        if config_path.exists():
            with open(config_path, encoding="utf-8") as config_file:
                return config_path, json.load(config_file)

    searched = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"config.json not found. Searched: {searched}")


def _build_base_url(config):
    if os.getenv("MCP_BASE_URL"):
        return os.getenv("MCP_BASE_URL").rstrip("/")

    server_config = config.get("server", {})
    host = os.getenv("MCP_HOST") or server_config.get("host") or "127.0.0.1"
    port = os.getenv("MCP_PORT") or server_config.get("port") or 5000

    if host in ("0.0.0.0", "::"):
        host = "127.0.0.1"

    return f"http://{host}:{port}"


def _auth_headers(config):
    qradar_config = config.get("qradar", {})
    auth_config = config.get("auth", {})
    authorized_service_token = qradar_config.get("authorized_service_token") or ""
    sec_token = qradar_config.get("sec_token") or ""
    csrf_token = qradar_config.get("csrf_token") or ""
    mcp_access_token = os.getenv("MCP_ACCESS_TOKEN") or auth_config.get("mcp_access_token") or ""

    headers = {}
    token_for_display = ""

    if authorized_service_token:
        headers["SEC"] = authorized_service_token
        token_for_display = authorized_service_token
    else:
        if sec_token:
            headers["SEC"] = sec_token
            token_for_display = sec_token
        if csrf_token:
            headers["QRadarCSRF"] = csrf_token

    if mcp_access_token:
        headers["Authorization"] = f"Bearer {mcp_access_token}"

    return headers, token_for_display


def _mask_token(token):
    if not token:
        return "(none)"
    if len(token) <= 12:
        return "*" * len(token)
    return f"{token[:8]}...{token[-4:]}"


async def test_local_mcp():
    """Test the locally running MCP server."""
    try:
        config_path, config = _load_config()
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Config error: {exc}")
        return

    headers, token_for_display = _auth_headers(config)
    if "SEC" not in headers:
        print("No SEC or authorized_service_token found in config.json")
        return

    base_url = _build_base_url(config)
    mcp_endpoint = f"{base_url}/mcp"

    print("QRadar MCP Server - Local Test")
    print("=" * 50)
    print(f"Config: {config_path}")
    print(f"Endpoint: {mcp_endpoint}")
    print(f"Auth token: {_mask_token(token_for_display)}\n")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("Step 1: Getting session ID...")
            response = await client.get(
                mcp_endpoint,
                headers={**headers, "Accept": "text/event-stream"}
            )

            print(f"Status: {response.status_code}")
            session_id = response.headers.get("mcp-session-id")

            if not session_id:
                print("No session ID received.")
                print(f"Headers: {dict(response.headers)}")
                print(f"Body: {response.text[:500]}")
                return

            print(f"Session ID: {session_id}\n")

            print("Step 2: Sending initialize command...")
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "local-test-client",
                        "version": "1.0.0"
                    }
                }
            }

            response = await client.post(
                mcp_endpoint,
                headers={
                    **headers,
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "mcp-session-id": session_id
                },
                json=init_request
            )

            print(f"Status: {response.status_code}")

            if response.status_code != 200:
                print("Initialize failed.")
                print(f"Response: {response.text}")
                return

            print("Initialize successful.\n")

            print("Step 3: Listing available tools...")
            list_tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }

            response = await client.post(
                mcp_endpoint,
                headers={
                    **headers,
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "mcp-session-id": session_id
                },
                json=list_tools_request
            )

            print(f"Status: {response.status_code}")

            if response.status_code != 200:
                print("List tools failed.")
                print(f"Response: {response.text}")
                return

            tools = []
            content_type = response.headers.get("content-type", "")
            if "text/event-stream" in content_type:
                for line in response.text.splitlines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                        except json.JSONDecodeError:
                            continue
                        tools = data.get("result", {}).get("tools", [])
                        if tools:
                            break
            else:
                tools = response.json().get("result", {}).get("tools", [])

            print(f"\nFound {len(tools)} tools")
            print("\nFirst 10 tools:")
            for index, tool in enumerate(tools[:10], 1):
                description = tool.get("description", "").split("\n")[0][:70]
                print(f"  {index}. {tool.get('name')}: {description}...")

            print("\n" + "=" * 50)
            print("MCP server is operational in local mode.")
            print("=" * 50)

    except httpx.ConnectError as exc:
        print(f"\nConnection error: cannot connect to {base_url}")
        print("Make sure the server is running with `python server.py`.")
        print(f"Details: {exc}")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"\nError: {type(exc).__name__}: {exc}")
        raise


if __name__ == "__main__":
    asyncio.run(test_local_mcp())
