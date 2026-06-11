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

"""List Ariel Lookups Tool."""

from typing import Any, Dict
import json

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema


class ListArielLookupsTool(MCPTool):
    """Tool for listing tagged field lookups available to AQL."""

    @property
    def name(self) -> str:
        return "list_ariel_lookups"

    @property
    def description(self) -> str:
        return """List tagged field lookups available in Ariel.

Lookups map tagged field values to readable values and can be useful context
when interpreting Ariel results or deciding which lookup to inspect by name."""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .string("fields")
                .description('Optional fields, e.g. "name,type,default_value"')
            .boolean("format_output")
                .description("Format output as human-readable text (default: false)")
                .default(False)
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        params = {}
        if arguments.get("fields"):
            params["fields"] = arguments["fields"]

        response = await self.client.get(
            "/ariel/lookups",
            params=params if params else None,
        )
        response.raise_for_status()
        lookups = response.json()

        if arguments.get("format_output", False):
            return self.create_success_response(self._format_lookups(lookups))

        return self.create_success_response(json.dumps(lookups, indent=2))

    def _format_lookups(self, lookups: Any) -> str:
        if not lookups:
            return "No Ariel lookups found"

        lines = [f"Found {len(lookups)} Ariel lookup(s)", "=" * 80]
        for lookup in lookups:
            lines.append(
                f"{lookup.get('name', 'N/A')} "
                f"(type: {lookup.get('type', 'N/A')})"
            )
            if lookup.get("default_value") is not None:
                lines.append(f"  Default: {lookup.get('default_value')}")
        return "\n".join(lines)
