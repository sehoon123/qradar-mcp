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

"""List Ariel Functions Tool."""

from typing import Any, Dict
import json

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema


class ListArielFunctionsTool(MCPTool):
    """Tool for listing AQL functions for a specific Ariel database."""

    @property
    def name(self) -> str:
        return "list_ariel_functions"

    @property
    def description(self) -> str:
        return """List AQL functions available for an Ariel database.

The QRadar API requires a database name, typically "events" or "flows". Use
this to discover function names, argument types, return types, and capabilities
before composing AQL."""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .string("database")
                .description('Ariel database name, usually "events" or "flows"')
                .required()
            .string("fields")
                .description('Optional fields, e.g. "name,return_type,args_types,info"')
            .boolean("format_output")
                .description("Format output as human-readable text (default: false)")
                .default(False)
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        database = arguments.get("database")
        if not database:
            return self.create_error_response("Error: database is required")

        params = {"database": database}
        if arguments.get("fields"):
            params["fields"] = arguments["fields"]

        response = await self.client.get("/ariel/functions", params=params)
        response.raise_for_status()
        functions = response.json()

        if arguments.get("format_output", False):
            return self.create_success_response(self._format_functions(functions))

        return self.create_success_response(json.dumps(functions, indent=2))

    def _format_functions(self, functions: Any) -> str:
        if not functions:
            return "No Ariel functions found"

        lines = [f"Found {len(functions)} Ariel function(s)\n", "=" * 80]
        for func in functions:
            lines.append(
                f"{func.get('name', 'N/A')}("
                f"{', '.join(func.get('args_types') or [])}) -> "
                f"{func.get('return_type', 'N/A')}"
            )
            info = func.get("info")
            if info:
                lines.append(f"  {info}")
        return "\n".join(lines)
