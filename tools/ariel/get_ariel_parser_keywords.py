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

"""Get Ariel Parser Keywords Tool."""

from typing import Any, Dict
import json

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema


class GetArielParserKeywordsTool(MCPTool):
    """Tool for retrieving AQL parser keywords."""

    @property
    def name(self) -> str:
        return "get_ariel_parser_keywords"

    @property
    def description(self) -> str:
        return """Get AQL parser keywords from QRadar.

Returns parser keywords and WHERE-clause keywords. This helps avoid generating
AQL that conflicts with reserved words or unsupported syntax."""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .string("fields")
                .description('Optional fields, e.g. "keywords,where_clause_keywords"')
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        params = {}
        if arguments.get("fields"):
            params["fields"] = arguments["fields"]

        response = await self.client.get(
            "/ariel/parser_keywords",
            params=params if params else None
        )
        response.raise_for_status()
        return self.create_success_response(json.dumps(response.json(), indent=2))
