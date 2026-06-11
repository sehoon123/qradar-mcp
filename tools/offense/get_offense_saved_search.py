# Copyright 2026 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""Get a QRadar offense saved search."""

from typing import Any, Dict
import json

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema


class GetOffenseSavedSearchTool(MCPTool):
    """Tool for retrieving one QRadar SIEM offense saved search."""

    @property
    def name(self) -> str:
        return "get_offense_saved_search"

    @property
    def description(self) -> str:
        return "Get an offense saved search by ID from QRadar SIEM."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .integer("search_id")
                .description("Offense saved search ID")
                .minimum(0)
                .required()
            .string("fields")
                .description("Optional comma-separated list of fields to return")
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        search_id = arguments.get("search_id")
        if search_id is None:
            return self.create_error_response("Error: search_id is required")

        params = {}
        if arguments.get("fields"):
            params["fields"] = arguments["fields"]

        response = await self.client.get(
            f"/siem/offense_saved_searches/{search_id}",
            params=params,
        )
        response.raise_for_status()
        return self.create_success_response(json.dumps(response.json(), indent=2))
