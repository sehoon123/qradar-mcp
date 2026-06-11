# Copyright 2026 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""Get a QRadar local destination address."""

from typing import Any, Dict
import json

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema


class GetLocalDestinationAddressTool(MCPTool):
    """Tool for retrieving one QRadar local destination address entity."""

    @property
    def name(self) -> str:
        return "get_local_destination_address"

    @property
    def description(self) -> str:
        return "Get a QRadar local destination address by local destination address ID."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .integer("local_destination_address_id")
                .description("Local destination address ID")
                .minimum(0)
                .required()
            .string("fields")
                .description("Optional comma-separated list of fields to return")
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        address_id = arguments.get("local_destination_address_id")
        if address_id is None:
            return self.create_error_response("Error: local_destination_address_id is required")

        params = {}
        if arguments.get("fields"):
            params["fields"] = arguments["fields"]

        response = await self.client.get(
            f"/siem/local_destination_addresses/{address_id}",
            params=params,
        )
        response.raise_for_status()
        return self.create_success_response(json.dumps(response.json(), indent=2))
