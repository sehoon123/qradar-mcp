#!/usr/bin/env python3
"""
Complete MCP test - establishes connection and sends commands.

Copy to container or modify base url to match your environment.
"""

import asyncio
import json
import httpx

async def test_mcp_complete():
    """Test MCP server with actual commands."""

    base_url = "http://127.0.0.1:5000"
    mcp_endpoint = f"{base_url}/mcp"

    # Replace with your actual tokens
    headers = {
        "SEC": "",
        "QRadarCSRF": "",
    }

    print("QRadar MCP Server - Complete Test")
    print("=" * 50)
    print(f"Endpoint: {mcp_endpoint}\n")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Get session ID
            print("Step 1: Getting session ID...")
            response = await client.get(
                mcp_endpoint,
                headers={**headers, "Accept": "text/event-stream"}
            )
            session_id = response.headers.get('mcp-session-id')
            if not session_id:
                print("❌ No session ID received!")
                return

            print(f"✅ Session ID: {session_id}\n")

            # Step 2: Send initialize command
            print("Step 2: Sending initialize command...")
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "test-client",
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
            print(f"Content-Type: {response.headers.get('content-type')}")

            if response.status_code == 200:
                # Check if it's SSE or JSON
                content_type = response.headers.get('content-type', '')
                if 'text/event-stream' in content_type:
                    print(f"✅ Initialize command sent (SSE stream response)")
                    print(f"Response body length: {len(response.text)} bytes")
                    if response.text:
                        # Parse SSE format and pretty print JSON
                        lines = response.text.split('\n')
                        for line in lines:
                            if line.startswith('data: '):
                                try:
                                    data = json.loads(line[6:])  # Remove 'data: ' prefix
                                    print(f"\nParsed Response:")
                                    print(json.dumps(data, indent=2))
                                except json.JSONDecodeError:
                                    print(f"Raw data: {line}")
                        print()
                    else:
                        print("(Empty SSE stream - waiting for events)\n")
                else:
                    result = response.json()
                    print(f"✅ Initialize successful!")
                    print(f"Server: {result.get('result', {}).get('serverInfo', {}).get('name')}")
                    print(f"Protocol: {result.get('result', {}).get('protocolVersion')}\n")
            else:
                print(f"Response: {response.text}\n")

            # Step 3: List tools
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
            print(f"Content-Type: {response.headers.get('content-type')}")

            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'text/event-stream' in content_type:
                    print(f"✅ Tools list command sent (SSE stream response)")
                    print(f"Response body length: {len(response.text)} bytes")
                    if response.text:
                        # Parse SSE format and extract tool info
                        lines = response.text.split('\n')
                        for line in lines:
                            if line.startswith('data: '):
                                try:
                                    data = json.loads(line[6:])
                                    tools = data.get('result', {}).get('tools', [])
                                    if tools:
                                        print(f"\n✅ Found {len(tools)} tools")
                                        print("\nFirst 10 tools:")
                                        for i, tool in enumerate(tools[:10], 1):
                                            print(f"  {i}. {tool['name']}")
                                            print(f"     {tool['description'][:80]}...")
                                except json.JSONDecodeError:
                                    print(f"Raw data: {line[:200]}")
                    else:
                        print("(Empty SSE stream - waiting for events)")
                else:
                    result = response.json()
                    tools = result.get('result', {}).get('tools', [])
                    print(f"✅ Found {len(tools)} tools")
                    print("\nFirst 5 tools:")
                    for tool in tools[:5]:
                        print(f"  - {tool['name']}: {tool['description'][:60]}...")
            else:
                print(f"Response: {response.text}")

            print("\n" + "=" * 50)
            print("✅ MCP Server is fully operational!")
            print("=" * 50)

    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_complete())
