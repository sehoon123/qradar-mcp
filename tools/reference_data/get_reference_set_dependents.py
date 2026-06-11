# Copyright 2026 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""Get QRadar reference set dependents."""

from typing import Any, Dict
import json

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema


class GetReferenceSetDependentsTool(MCPTool):
    """Tool for listing QRadar objects that depend on a reference set."""

    @property
    def name(self) -> str:
        return "get_reference_set_dependents"

    @property
    def description(self) -> str:
        return "Get dependents for a QRadar reference set by set ID."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .integer("set_id")
                .description("Reference set ID")
                .minimum(0)
                .required()
            .string("fields")
                .description("Optional comma-separated list of fields to return")
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        set_id = arguments.get("set_id")
        if set_id is None:
            return self.create_error_response("Error: set_id is required")

        params = {}
        if arguments.get("fields"):
            params["fields"] = arguments["fields"]

        response = await self.client.get(
            f"/reference_data_collections/sets/{set_id}/dependents",
            params=params,
        )
        response.raise_for_status()
        return self.create_success_response(json.dumps(response.json(), indent=2))
