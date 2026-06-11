# Copyright 2026 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""Cancel an active Ariel search job."""

from typing import Dict, Any
import json

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema


class CancelArielSearchTool(MCPTool):
    """Tool for canceling active Ariel searches."""

    @property
    def name(self) -> str:
        return "cancel_ariel_search"

    @property
    def description(self) -> str:
        return (
            "Cancel an active Ariel search by setting its status to CANCELED. "
            "This does not mutate QRadar event data, but it changes the state of "
            "a transient search job and is disabled in the default read-only profile."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .string("search_id")
                .description("The ID of the active Ariel search to cancel")
                .required()
            .build())

    @property
    def http_verb(self) -> str:
        return "POST"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        search_id = arguments.get("search_id")
        if not search_id:
            return self.create_error_response("Error: search_id is required")

        response = await self.client.post(
            f"ariel/searches/{search_id}",
            params={"status": "CANCELED"},
        )
        response.raise_for_status()

        try:
            payload = response.json()
        except json.JSONDecodeError:
            payload = {"status_code": response.status_code, "text": response.text}

        return self.create_success_response(json.dumps(payload, indent=2))
