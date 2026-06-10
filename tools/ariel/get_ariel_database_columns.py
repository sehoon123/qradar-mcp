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

"""Get Ariel Database Columns Tool."""

from typing import Any, Dict
from urllib.parse import quote
import json

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema
from qradar_mcp.utils.parameters import (
    build_headers,
    build_query_params,
    parse_range_from_limit_offset,
)


class GetArielDatabaseColumnsTool(MCPTool):
    """Tool for retrieving columns available in an Ariel database."""

    @property
    def name(self) -> str:
        return "get_ariel_database_columns"

    @property
    def description(self) -> str:
        return """Get columns defined for a specific Ariel database.

Use this read-only endpoint before composing AQL SELECT clauses. It returns the
columns that can be explicitly named for a database such as "events" or "flows",
including metadata like indexability and value type."""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .string("database_name")
                .description('Ariel database name, usually "events" or "flows"')
                .required()
            .string("filter")
                .description('Optional filter expression, e.g. "name LIKE \'%source%\'"')
            .string("fields")
                .description('Optional fields, e.g. "columns(name,indexable,object_value_type)"')
            .integer("limit")
                .description("Maximum columns to return (default: 200, max: 10000)")
                .minimum(1)
                .maximum(10000)
                .default(200)
            .integer("offset")
                .description("Number of columns to skip (default: 0)")
                .minimum(0)
                .default(0)
            .boolean("format_output")
                .description("Format output as human-readable text (default: false)")
                .default(False)
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        database_name = arguments.get("database_name")
        if not database_name:
            return self.create_error_response("Error: database_name is required")

        fields = self._fields_list(arguments.get("fields"))
        params = build_query_params(
            filter_expr=arguments.get("filter"),
            fields=fields,
        )
        limit = arguments.get("limit", 200)
        offset = arguments.get("offset", 0)
        start, end = parse_range_from_limit_offset(limit, offset)
        headers = build_headers(start=start, end=end)

        encoded_name = quote(str(database_name), safe="")
        response = await self.client.get(
            f"/ariel/databases/{encoded_name}",
            params=params if params else None,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

        if arguments.get("format_output", False):
            return self.create_success_response(self._format_columns(database_name, data))

        return self.create_success_response(json.dumps(data, indent=2))

    def _fields_list(self, fields: str | None) -> list[str] | None:
        return [field.strip() for field in fields.split(",")] if fields else None

    def _format_columns(self, database_name: str, data: Any) -> str:
        columns = data.get("columns", []) if isinstance(data, dict) else data
        if not columns:
            return f"No columns found for Ariel database '{database_name}'"

        lines = [
            f"Found {len(columns)} column(s) for Ariel database '{database_name}'",
            "=" * 80,
        ]
        for column in columns:
            lines.append(str(column.get("name", "N/A")))
            details = []
            if "indexable" in column:
                details.append(f"indexable: {column.get('indexable')}")
            if column.get("object_value_type"):
                details.append(f"type: {column.get('object_value_type')}")
            if column.get("provider_name"):
                details.append(f"provider: {column.get('provider_name')}")
            if details:
                lines.append("  " + " | ".join(details))
        return "\n".join(lines)

