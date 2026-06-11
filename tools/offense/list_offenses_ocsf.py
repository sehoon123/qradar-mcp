# Copyright 2026 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""List QRadar offenses in OCSF shape."""

from typing import Any, Dict
import json

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema
from qradar_mcp.utils.parameters import build_headers, build_query_params, parse_range_from_limit_offset


class ListOffensesOcsfTool(MCPTool):
    """Tool for listing QRadar offenses through the OCSF endpoint."""

    @property
    def name(self) -> str:
        return "list_offenses_ocsf"

    @property
    def description(self) -> str:
        return "List QRadar offenses from the OCSF endpoint."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .string("filter")
                .description("Optional AQL-style filter expression")
            .string("sort")
                .description("Optional sort expression")
            .integer("limit")
                .description("Maximum number of offenses to return")
                .minimum(1)
                .maximum(10000)
            .integer("offset")
                .description("Number of offenses to skip")
                .minimum(0)
            .string("fields")
                .description("Optional comma-separated list of fields to return")
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        sort_expr = arguments.get("sort")
        fields = arguments.get("fields")
        params = build_query_params(
            filter_expr=arguments.get("filter"),
            sort_fields=[sort_expr] if sort_expr else None,
            fields=[field.strip() for field in fields.split(",")] if fields else None,
        )
        start, end = parse_range_from_limit_offset(
            limit=arguments.get("limit", 50),
            offset=arguments.get("offset", 0),
        )
        response = await self.client.get(
            "/siem/offenses_ocsf",
            params=params,
            headers=build_headers(start=start, end=end),
        )
        response.raise_for_status()
        return self.create_success_response(json.dumps(response.json(), indent=2))
