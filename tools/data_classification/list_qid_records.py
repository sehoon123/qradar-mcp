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


"""
List QID Records Tool

Retrieves QID (QRadar Identifier) records, which map numeric event identifiers
to human-readable names, categories, and severities.
"""

from typing import Dict, Any
import json
from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema
from qradar_mcp.utils.parameters import (
    build_query_params,
    parse_range_from_limit_offset,
    build_headers
)


class ListQidRecordsTool(MCPTool):
    """Tool for listing QRadar QID records with filtering and pagination."""

    @property
    def name(self) -> str:
        return "list_qid_records"

    @property
    def description(self) -> str:
        return """List QID records from QRadar with optional filtering, sorting, and pagination.

A QID (QRadar Identifier) maps the numeric event identifier found in raw events
to a human-readable name, severity, and event category. Use this to translate the
'qid' value returned by Ariel event searches into a meaningful event name.

Examples:
  - Look up a specific QID: filter="qid=5000023"
  - Find events by name: filter="name LIKE '%logon%'"
  - Filter by log source type: filter="log_source_type_id=12"
  - Filter by low level category: filter="low_level_category_id=3001"
  - Sort by severity: sort="-severity"
  - Get first 50 records: limit=50, offset=0"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .string("filter")
                .description('Optional AQL-style filter expression. Examples: "qid=5000023", "name LIKE \'%logon%\'", "low_level_category_id=3001"')
            .string("fields")
                .description('Comma-separated list of fields to include. Examples: "qid,name,severity,low_level_category_id"')
            .string("sort")
                .description('Optional sort expression. Use +field for ascending, -field for descending. Examples: "-severity", "+name"')
            .integer("limit")
                .description("Maximum number of records to return (default: 50, max: 10000)")
                .minimum(1)
                .maximum(10000)
                .default(50)
            .integer("offset")
                .description("Number of records to skip for pagination (default: 0)")
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
        filter_expr = arguments.get("filter")
        fields_str = arguments.get("fields")
        sort_expr = arguments.get("sort")
        limit = arguments.get("limit", 50)
        offset = arguments.get("offset", 0)

        fields_list = [f.strip() for f in fields_str.split(",")] if fields_str else None
        params = build_query_params(
            filter_expr=filter_expr,
            sort_fields=[sort_expr] if sort_expr else None,
            fields=fields_list
        )

        start, end = parse_range_from_limit_offset(limit, offset)
        headers = build_headers(start=start, end=end)

        response = await self.client.get(
            '/data_classification/qid_records',
            params=params if params else None,
            headers=headers
        )
        response.raise_for_status()
        records = response.json()

        if arguments.get("format_output", False):
            return self.create_success_response(self._format_records(records))

        return self.create_success_response(json.dumps(records, indent=2))

    def _format_records(self, records: Any) -> str:
        if not records:
            return "No QID records found"

        lines = [f"Found {len(records)} QID record(s)\n", "=" * 80]
        for record in records:
            lines.append(
                f"QID {record.get('qid', 'N/A')}: {record.get('name', 'N/A')}"
            )
            description = record.get('description')
            if description:
                lines.append(f"  Description: {description}")
            lines.append(
                f"  Severity: {record.get('severity', 'N/A')} | "
                f"Low-level category: {record.get('low_level_category_id', 'N/A')} | "
                f"Log source type: {record.get('log_source_type_id', 'N/A')}"
            )
            lines.append("-" * 80)
        return "\n".join(lines)
