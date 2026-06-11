# Copyright 2026 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""Get a QRadar reference set entry by ID."""

from typing import Any, Dict
import json

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema


class GetReferenceSetEntryTool(MCPTool):
    """Tool for retrieving a single QRadar reference set entry."""

    @property
    def name(self) -> str:
        return "get_reference_set_entry"

    @property
    def description(self) -> str:
        return "Get a reference set entry by entry ID from QRadar reference data collections."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .integer("entry_id")
                .description("Reference set entry ID")
                .minimum(0)
                .required()
            .string("fields")
                .description("Optional comma-separated list of fields to return")
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        entry_id = arguments.get("entry_id")
        if entry_id is None:
            return self.create_error_response("Error: entry_id is required")

        params = {}
        if arguments.get("fields"):
            params["fields"] = arguments["fields"]

        response = await self.client.get(
            f"/reference_data_collections/set_entries/{entry_id}",
            params=params,
        )
        response.raise_for_status()
        return self.create_success_response(json.dumps(response.json(), indent=2))
