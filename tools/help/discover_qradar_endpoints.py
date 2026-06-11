# Copyright 2026 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Discover QRadar Endpoints Tool."""

from typing import Any, Dict
import json

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema
from qradar_mcp.utils.parameters import build_headers


class DiscoverQradarEndpointsTool(MCPTool):
    """Tool for querying QRadar's own endpoint documentation catalog."""

    @property
    def name(self) -> str:
        return "discover_qradar_endpoints"

    @property
    def description(self) -> str:
        return """Discover supported QRadar API endpoints from /help/endpoints.

This read-only tool queries the live QRadar console for endpoint metadata, so it
reflects the exact QRadar version and installed capabilities. Use it before
adding new MCP tools or when checking whether a GET endpoint exists."""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .string("search")
                .description("Search term matched against endpoint path or summary")
            .string("method")
                .description("Optional HTTP method filter")
                .enum(["GET", "POST", "PUT", "PATCH", "DELETE"])
            .string("filter")
                .description("Raw QRadar help filter; overrides search/method when supplied")
            .string("fields")
                .description('Optional fields, e.g. "id,path,http_method,summary,deprecated"')
            .integer("limit")
                .description("Maximum endpoints to return (default: 25, max: 100)")
                .minimum(1)
                .maximum(100)
                .default(25)
            .integer("offset")
                .description("Number of endpoints to skip (default: 0)")
                .minimum(0)
                .default(0)
            .boolean("get_only")
                .description("Restrict results to GET endpoints (default: true)")
                .default(True)
            .boolean("format_output")
                .description("Format output as human-readable text (default: false)")
                .default(False)
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        params = {}
        filter_expr = arguments.get("filter") or self._build_filter(arguments)
        if filter_expr:
            params["filter"] = filter_expr
        if arguments.get("fields"):
            params["fields"] = arguments["fields"]

        limit = arguments.get("limit", 25)
        offset = arguments.get("offset", 0)
        headers = build_headers(start=offset, end=offset + limit - 1)

        response = await self.client.get(
            "/help/endpoints",
            params=params if params else None,
            headers=headers
        )
        response.raise_for_status()
        endpoints = response.json()

        if arguments.get("format_output", False):
            return self.create_success_response(self._format_endpoints(endpoints))

        return self.create_success_response(json.dumps(endpoints, indent=2))

    def _build_filter(self, arguments: Dict[str, Any]) -> str | None:
        filters = []
        method = arguments.get("method")
        if arguments.get("get_only", True) and not method:
            method = "GET"
        if method:
            filters.append(f"http_method='{method}'")

        search = arguments.get("search")
        if search:
            safe_search = str(search).replace("'", "''")
            filters.append(f"(path ILIKE '%{safe_search}%' OR summary ILIKE '%{safe_search}%')")

        return " AND ".join(filters) if filters else None

    def _format_endpoints(self, endpoints: Any) -> str:
        if not endpoints:
            return "No QRadar endpoints found"

        lines = [f"Found {len(endpoints)} endpoint(s)\n", "=" * 80]
        for endpoint in endpoints:
            deprecated = " DEPRECATED" if endpoint.get("deprecated") else ""
            lines.append(
                f"{endpoint.get('http_method', 'N/A')} "
                f"{endpoint.get('path', 'N/A')}{deprecated}"
            )
            summary = endpoint.get("summary")
            if summary:
                lines.append(f"  {summary}")
        return "\n".join(lines)
