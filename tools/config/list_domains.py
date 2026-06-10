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
List Domains Tool

Retrieves the domains defined in the QRadar deployment. Domains provide
multi-tenancy / data segregation; events, offenses and assets are scoped to
a domain.
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


class ListDomainsTool(MCPTool):
    """Tool for listing QRadar domains with filtering and pagination."""

    @property
    def name(self) -> str:
        return "list_domains"

    @property
    def description(self) -> str:
        return """List domains from QRadar with optional filtering, sorting, and pagination.

Domains provide multi-tenancy and data segregation in QRadar. Events, flows,
offenses and assets are associated with a domain via a domain_id. Use this to
resolve a 'domain_id' to a readable domain name and to understand the tenant
structure of the deployment.

Examples:
  - List all domains: (no parameters)
  - Look up a specific domain: filter="id=2"
  - Find a domain by name: filter="name LIKE '%Tenant%'"
  - Exclude deleted domains: filter="deleted=false\""""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .string("filter")
                .description('Optional AQL-style filter expression. Examples: "id=2", "name LIKE \'%Tenant%\'", "deleted=false"')
            .string("fields")
                .description('Comma-separated list of fields to include. Examples: "id,name,description,deleted"')
            .string("sort")
                .description('Optional sort expression. Use +field for ascending, -field for descending. Examples: "+name"')
            .integer("limit")
                .description("Maximum number of domains to return (default: 50, max: 10000)")
                .minimum(1)
                .maximum(10000)
                .default(50)
            .integer("offset")
                .description("Number of domains to skip for pagination (default: 0)")
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
            '/config/domain_management/domains',
            params=params if params else None,
            headers=headers
        )
        response.raise_for_status()
        domains = response.json()

        if arguments.get("format_output", False):
            return self.create_success_response(self._format_domains(domains))

        return self.create_success_response(json.dumps(domains, indent=2))

    def _format_domains(self, domains: Any) -> str:
        if not domains:
            return "No domains found"

        lines = [f"Found {len(domains)} domain(s)\n", "=" * 80]
        for domain in domains:
            deleted = " (deleted)" if domain.get('deleted') else ""
            lines.append(
                f"[{domain.get('id', 'N/A')}] {domain.get('name', 'N/A')}{deleted}"
            )
            description = domain.get('description')
            if description:
                lines.append(f"  Description: {description}")
        return "\n".join(lines)
