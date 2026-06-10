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

"""Get Ariel Lookup Tool."""

from typing import Any, Dict
from urllib.parse import quote
import json

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema


class GetArielLookupTool(MCPTool):
    """Tool for retrieving a tagged field lookup by name."""

    @property
    def name(self) -> str:
        return "get_ariel_lookup"

    @property
    def description(self) -> str:
        return """Get a tagged field lookup by name.

Use this read-only endpoint to inspect a specific Ariel lookup map and default
value when interpreting tagged field values in query results."""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .string("name")
                .description("Lookup name to retrieve")
                .required()
            .string("fields")
                .description('Optional fields, e.g. "name,type,default_value,map"')
            .boolean("format_output")
                .description("Format output as human-readable text (default: false)")
                .default(False)
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        name = arguments.get("name")
        if not name:
            return self.create_error_response("Error: name is required")

        params = {}
        if arguments.get("fields"):
            params["fields"] = arguments["fields"]

        encoded_name = quote(str(name), safe="")
        response = await self.client.get(
            f"/ariel/lookups/{encoded_name}",
            params=params if params else None,
        )
        response.raise_for_status()
        lookup = response.json()

        if arguments.get("format_output", False):
            return self.create_success_response(self._format_lookup(lookup))

        return self.create_success_response(json.dumps(lookup, indent=2))

    def _format_lookup(self, lookup: Any) -> str:
        if not lookup:
            return "Ariel lookup not found"

        lines = [
            f"Lookup: {lookup.get('name', 'N/A')}",
            f"Type: {lookup.get('type', 'N/A')}",
        ]
        if lookup.get("default_value") is not None:
            lines.append(f"Default: {lookup.get('default_value')}")
        mapping = lookup.get("map")
        if isinstance(mapping, dict):
            lines.append(f"Entries: {len(mapping)}")
        return "\n".join(lines)

