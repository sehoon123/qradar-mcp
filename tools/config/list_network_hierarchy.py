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
List Network Hierarchy Tool

Retrieves the deployed network hierarchy: the named networks (CIDR ranges) that
QRadar uses to determine whether an address is local or remote and which network
group it belongs to.
"""

from typing import Dict, Any
import json
from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema


class ListNetworkHierarchyTool(MCPTool):
    """Tool for retrieving the QRadar deployed network hierarchy."""

    @property
    def name(self) -> str:
        return "list_network_hierarchy"

    @property
    def description(self) -> str:
        return """List the deployed network hierarchy from QRadar.

The network hierarchy defines named networks as CIDR ranges. QRadar uses it to
decide whether an IP address is local or remote and which logical network group
it belongs to. This is key context when investigating an offense or event: it
tells you what part of the environment a source or destination IP represents.

Returns each network's id, name, CIDR/group, and (where available) country code.
Use the optional 'fields' parameter to limit the returned attributes."""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .string("fields")
                .description('Optional comma-separated list of fields to return (e.g., "id,name,cidr,group")')
            .boolean("format_output")
                .description("Format output as human-readable text (default: false)")
                .default(False)
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        fields = arguments.get("fields")

        params = {}
        if fields:
            params['fields'] = fields

        response = await self.client.get(
            '/config/network_hierarchy/networks',
            params=params if params else None
        )
        response.raise_for_status()
        networks = response.json()

        if arguments.get("format_output", False):
            return self.create_success_response(self._format_networks(networks))

        return self.create_success_response(json.dumps(networks, indent=2))

    def _format_networks(self, networks: Any) -> str:
        if not networks:
            return "No networks found in the network hierarchy"

        lines = [f"Found {len(networks)} network(s)\n", "=" * 80]
        for network in networks:
            lines.append(
                f"[{network.get('id', 'N/A')}] {network.get('name', 'N/A')} "
                f"-> {network.get('cidr', 'N/A')}"
            )
            group = network.get('group')
            country = network.get('country_code')
            details = []
            if group:
                details.append(f"group: {group}")
            if country:
                details.append(f"country: {country}")
            if details:
                lines.append("  " + " | ".join(details))
        return "\n".join(lines)
