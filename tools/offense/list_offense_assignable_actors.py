# Copyright 2026 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""List assignable actors for a QRadar offense."""

from typing import Any, Dict
import json

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema
from qradar_mcp.utils.validators import validate_offense_id


class ListOffenseAssignableActorsTool(MCPTool):
    """Tool for listing users or groups an offense can be assigned to."""

    @property
    def name(self) -> str:
        return "list_offense_assignable_actors"

    @property
    def description(self) -> str:
        return "List actors that the connected QRadar deployment allows for assigning an offense."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .integer("offense_id")
                .description("Offense ID")
                .minimum(0)
                .required()
            .string("fields")
                .description("Optional comma-separated list of fields to return")
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        offense_id = arguments.get("offense_id")
        if not validate_offense_id(offense_id):
            return self.create_error_response("Error: offense_id must be a non-negative integer")

        params = {}
        if arguments.get("fields"):
            params["fields"] = arguments["fields"]

        response = await self.client.get(
            f"/siem/offenses/{offense_id}/assignable_actors",
            params=params,
        )
        response.raise_for_status()
        return self.create_success_response(json.dumps(response.json(), indent=2))
