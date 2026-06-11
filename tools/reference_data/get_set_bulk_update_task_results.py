# Copyright 2026 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""Get QRadar reference set bulk update task results."""

from typing import Any, Dict
import json

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema
from qradar_mcp.utils.parameters import build_headers, parse_range_from_limit_offset


class GetSetBulkUpdateTaskResultsTool(MCPTool):
    """Tool for retrieving reference set bulk update task results."""

    @property
    def name(self) -> str:
        return "get_set_bulk_update_task_results"

    @property
    def description(self) -> str:
        return "Get result entries for a QRadar reference set bulk update task."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .string("task_status_id")
                .description("Bulk update task status ID")
                .min_length(1)
                .required()
            .integer("limit")
                .description("Maximum number of results to return")
                .minimum(1)
                .maximum(10000)
            .integer("offset")
                .description("Number of results to skip")
                .minimum(0)
            .string("fields")
                .description("Optional comma-separated list of fields to return")
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        task_status_id = arguments.get("task_status_id")
        if not task_status_id:
            return self.create_error_response("Error: task_status_id is required")

        params = {}
        if arguments.get("fields"):
            params["fields"] = arguments["fields"]
        start, end = parse_range_from_limit_offset(
            limit=arguments.get("limit", 50),
            offset=arguments.get("offset", 0),
        )
        response = await self.client.get(
            f"/reference_data_collections/set_bulk_update_tasks/{task_status_id}/results",
            params=params,
            headers=build_headers(start=start, end=end),
        )
        response.raise_for_status()
        return self.create_success_response(json.dumps(response.json(), indent=2))
