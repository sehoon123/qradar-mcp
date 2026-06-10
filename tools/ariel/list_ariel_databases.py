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

"""List Ariel Databases Tool."""

from typing import Any, Dict
import json

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema
from qradar_mcp.utils.parameters import build_headers


class ListArielDatabasesTool(MCPTool):
    """Tool for listing available Ariel databases."""

    @property
    def name(self) -> str:
        return "list_ariel_databases"

    @property
    def description(self) -> str:
        return """List available Ariel databases, such as events and flows.

Use this before building AQL queries to confirm which Ariel databases are
available on the target QRadar deployment."""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .string("filter")
                .description("Optional filter expression")
            .integer("limit")
                .description("Maximum databases to return (default: 50, max: 100)")
                .minimum(1)
                .maximum(100)
                .default(50)
            .integer("offset")
                .description("Number of databases to skip (default: 0)")
                .minimum(0)
                .default(0)
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        params = {}
        if arguments.get("filter"):
            params["filter"] = arguments["filter"]

        limit = arguments.get("limit", 50)
        offset = arguments.get("offset", 0)
        headers = build_headers(start=offset, end=offset + limit - 1)

        response = await self.client.get(
            "/ariel/databases",
            params=params if params else None,
            headers=headers
        )
        response.raise_for_status()
        return self.create_success_response(json.dumps(response.json(), indent=2))

