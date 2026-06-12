# Copyright 2026 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""Get a single QRadar offense note."""

from typing import Any, Dict
import json

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema
from qradar_mcp.utils.validators import validate_offense_id


class GetOffenseNoteTool(MCPTool):
    """Tool for retrieving one investigation note from an offense."""

    @property
    def name(self) -> str:
        return "get_offense_note"

    @property
    def description(self) -> str:
        return "Get a single investigation note for a QRadar offense by note ID."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .integer("offense_id")
                .description("Offense ID")
                .minimum(1)
                .required()
            .integer("note_id")
                .description("Offense note ID")
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
        note_id = arguments.get("note_id")
        if not validate_offense_id(offense_id):
            return self.create_error_response("Error: offense_id must be a positive integer")
        if note_id is None:
            return self.create_error_response("Error: note_id is required")

        params = {}
        if arguments.get("fields"):
            params["fields"] = arguments["fields"]

        response = await self.client.get(
            f"/siem/offenses/{offense_id}/notes/{note_id}",
            params=params,
        )
        response.raise_for_status()
        return self.create_success_response(json.dumps(response.json(), indent=2))
