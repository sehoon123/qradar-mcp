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

"""List Top Rules Tool."""

from typing import Any, Dict
import json

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema
from qradar_mcp.utils.parameters import (
    build_headers,
    build_query_params,
    parse_range_from_limit_offset,
)


class ListTopRulesTool(MCPTool):
    """Tool for retrieving QRadar top rules by response count."""

    @property
    def name(self) -> str:
        return "list_top_rules"

    @property
    def description(self) -> str:
        return """List top rules in QRadar sorted by response count.

Use this read-only health endpoint to identify the rules generating the most
responses, which helps find noisy detection logic and high-value rule context."""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .string("filter")
                .description('Optional filter expression, e.g. "count > 10"')
            .string("fields")
                .description('Optional comma-separated fields, e.g. "rule_id,rule_name,count"')
            .integer("limit")
                .description("Maximum number of top rules to return (default: 10, max: 1000)")
                .minimum(1)
                .maximum(1000)
                .default(10)
            .integer("offset")
                .description("Number of rows to skip (default: 0)")
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
        fields = self._fields_list(arguments.get("fields"))
        params = build_query_params(
            filter_expr=arguments.get("filter"),
            fields=fields
        )
        limit = arguments.get("limit", 10)
        offset = arguments.get("offset", 0)
        start, end = parse_range_from_limit_offset(limit, offset)
        headers = build_headers(start=start, end=end)

        response = await self.client.get(
            "/health_data/top_rules",
            params=params if params else None,
            headers=headers
        )
        response.raise_for_status()
        rules = response.json()

        if arguments.get("format_output", False):
            return self.create_success_response(self._format_rules(rules))

        return self.create_success_response(json.dumps(rules, indent=2))

    def _fields_list(self, fields: str | None) -> list[str] | None:
        return [field.strip() for field in fields.split(",")] if fields else None

    def _format_rules(self, rules: Any) -> str:
        if not rules:
            return "No top rules found"

        lines = [f"Found {len(rules)} top rule(s)\n", "=" * 80]
        for rule in rules:
            lines.append(
                f"Rule {rule.get('rule_id', 'N/A')}: "
                f"{rule.get('rule_name', 'N/A')}"
            )
            lines.append(f"  Response count: {rule.get('count', 'N/A')}")
        return "\n".join(lines)
