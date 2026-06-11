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

"""Get Security Data Count Tool."""

from typing import Any, Dict
import json

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema


class GetSecurityDataCountTool(MCPTool):
    """Tool for retrieving high-level QRadar security artifact counts."""

    @property
    def name(self) -> str:
        return "get_security_data_count"

    @property
    def description(self) -> str:
        return """Get high-level QRadar security data counts.

Returns the number of assets, offenses, rules, log sources, and vulnerabilities
known to QRadar. This is useful as a lightweight deployment summary before
starting an investigation or health review."""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .string("fields")
                .description('Optional comma-separated fields, e.g. "assets,offenses,rules"')
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        params = {}
        if arguments.get("fields"):
            params["fields"] = arguments["fields"]

        response = await self.client.get(
            "/health_data/security_data_count",
            params=params if params else None
        )
        response.raise_for_status()
        return self.create_success_response(json.dumps(response.json(), indent=2))
