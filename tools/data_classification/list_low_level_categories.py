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
List Low Level Categories Tool

Retrieves QRadar low level event categories, which provide fine-grained
classification of events and roll up into high level categories.
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


class ListLowLevelCategoriesTool(MCPTool):
    """Tool for listing QRadar low level event categories."""

    @property
    def name(self) -> str:
        return "list_low_level_categories"

    @property
    def description(self) -> str:
        return """List low level event categories from QRadar with optional filtering, sorting, and pagination.

Low level categories provide fine-grained event classification (e.g. "User Login Success")
and each belongs to a high level category. Use this to resolve the
'low_level_category_id' found on QID records and Ariel results into a readable name.

Examples:
  - Look up a specific category: filter="id=3001"
  - Find categories by name: filter="name LIKE '%Login%'"
  - Filter by parent high level category: filter="high_level_category_id=3000"
  - Get first 100 categories: limit=100, offset=0"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .string("filter")
                .description('Optional AQL-style filter expression. Examples: "id=3001", "name LIKE \'%Login%\'", "high_level_category_id=3000"')
            .string("fields")
                .description('Comma-separated list of fields to include. Examples: "id,name,high_level_category_id,severity"')
            .string("sort")
                .description('Optional sort expression. Use +field for ascending, -field for descending. Examples: "+name"')
            .integer("limit")
                .description("Maximum number of categories to return (default: 100, max: 10000)")
                .minimum(1)
                .maximum(10000)
                .default(100)
            .integer("offset")
                .description("Number of categories to skip for pagination (default: 0)")
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
        limit = arguments.get("limit", 100)
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
            '/data_classification/low_level_categories',
            params=params if params else None,
            headers=headers
        )
        response.raise_for_status()
        categories = response.json()

        if arguments.get("format_output", False):
            return self.create_success_response(self._format_categories(categories))

        return self.create_success_response(json.dumps(categories, indent=2))

    def _format_categories(self, categories: Any) -> str:
        if not categories:
            return "No low level categories found"

        lines = [f"Found {len(categories)} low level category(ies)\n", "=" * 80]
        for category in categories:
            lines.append(
                f"[{category.get('id', 'N/A')}] {category.get('name', 'N/A')} "
                f"(high level category: {category.get('high_level_category_id', 'N/A')}, "
                f"severity: {category.get('severity', 'N/A')})"
            )
            description = category.get('description')
            if description:
                lines.append(f"  Description: {description}")
        return "\n".join(lines)
