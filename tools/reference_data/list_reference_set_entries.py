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

"""List QRadar reference set entries."""

from typing import Any, Dict
import json

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema
from qradar_mcp.utils.parameters import build_headers, build_query_params, parse_range_from_limit_offset


class ListReferenceSetEntriesTool(MCPTool):
    """Tool for listing entries in QRadar reference data collections."""

    @property
    def name(self) -> str:
        return "list_reference_set_entries"

    @property
    def description(self) -> str:
        return """List reference set entries from QRadar reference data collections.

Use filters to narrow by collection_id, value, source, or timing fields when the
connected QRadar API exposes those fields."""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .string("filter")
                .description("Optional AQL-style filter expression")
            .string("sort")
                .description("Optional sort expression, e.g. '+value' or '-last_seen'")
            .integer("limit")
                .description("Maximum number of entries to return")
                .minimum(1)
                .maximum(10000)
            .integer("offset")
                .description("Number of entries to skip")
                .minimum(0)
            .string("fields")
                .description("Optional comma-separated list of fields to return")
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        sort_expr = arguments.get("sort")
        fields = arguments.get("fields")
        params = build_query_params(
            filter_expr=arguments.get("filter"),
            sort_fields=[sort_expr] if sort_expr else None,
            fields=[field.strip() for field in fields.split(",")] if fields else None,
        )
        start, end = parse_range_from_limit_offset(
            limit=arguments.get("limit", 50),
            offset=arguments.get("offset", 0),
        )
        response = await self.client.get(
            "/reference_data_collections/set_entries",
            params=params,
            headers=build_headers(start=start, end=end),
        )
        response.raise_for_status()
        return self.create_success_response(json.dumps(response.json(), indent=2))
