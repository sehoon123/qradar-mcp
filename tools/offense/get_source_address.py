# Copyright 2026 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""Get a QRadar source address."""

from typing import Any, Dict
import json

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema


class GetSourceAddressTool(MCPTool):
    """Tool for retrieving one QRadar source address entity."""

    @property
    def name(self) -> str:
        return "get_source_address"

    @property
    def description(self) -> str:
        return "Get a QRadar source address by source address ID."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .integer("source_address_id")
                .description("Source address ID")
                .minimum(0)
                .required()
            .string("fields")
                .description("Optional comma-separated list of fields to return")
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        source_address_id = arguments.get("source_address_id")
        if source_address_id is None:
            return self.create_error_response("Error: source_address_id is required")

        params = {}
        if arguments.get("fields"):
            params["fields"] = arguments["fields"]

        response = await self.client.get(
            f"/siem/source_addresses/{source_address_id}",
            params=params,
        )
        response.raise_for_status()
        return self.create_success_response(json.dumps(response.json(), indent=2))
