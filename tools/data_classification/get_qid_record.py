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
Get QID Record Tool

Retrieves a single QID record by its numeric QID value.
"""

from typing import Dict, Any
import json
from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema
from qradar_mcp.utils.parameters import build_headers


class GetQidRecordTool(MCPTool):
    """Tool for retrieving a single QRadar QID record by QID."""

    @property
    def name(self) -> str:
        return "get_qid_record"

    @property
    def description(self) -> str:
        return """Get a single QID record by its numeric QID value.

A QID (QRadar Identifier) maps a numeric event identifier to a human-readable
name, severity, and event category. Use this to resolve a specific 'qid' value
returned by an Ariel event search.

Returns the event name, description, severity, and the associated low/high level
event category identifiers."""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .integer("qid")
                .description("The numeric QID (QRadar Identifier) of the record to retrieve")
                .minimum(0)
                .required()
            .string("fields")
                .description('Optional comma-separated list of fields to return (e.g., "qid,name,severity")')
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        qid = arguments.get("qid")
        fields = arguments.get("fields")

        if qid is None:
            return self.create_error_response("Error: qid is required")

        params = {}
        if fields:
            params['fields'] = fields

        qid = int(qid)
        response = await self.client.get(
            f'/data_classification/qid_records/{int(qid)}',
            params=params if params else None
        )
        if response.status_code == 404:
            return await self._lookup_by_qid_filter(qid, fields)

        response.raise_for_status()
        record = response.json()
        return self.create_success_response(json.dumps(record, indent=2))

    async def _lookup_by_qid_filter(self, qid: int, fields: str | None) -> Dict[str, Any]:
        """Fallback for deployments where the record id differs from the QID value."""
        params = {"filter": f"qid={qid}"}
        if fields:
            params["fields"] = fields

        response = await self.client.get(
            "/data_classification/qid_records",
            params=params,
            headers=build_headers(start=0, end=0)
        )
        response.raise_for_status()
        records = response.json()
        if not records:
            return self.create_error_response(f"Error: QID record not found for qid={qid}")

        return self.create_success_response(json.dumps(records[0], indent=2))
