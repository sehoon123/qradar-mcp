# Copyright 2026 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""List QRadar offense saved searches."""

from typing import Any, Dict
import json

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema
from qradar_mcp.utils.parameters import build_headers, build_query_params, parse_range_from_limit_offset


class ListOffenseSavedSearchesTool(MCPTool):
    """Tool for listing QRadar SIEM offense saved searches."""

    @property
    def name(self) -> str:
        return "list_offense_saved_searches"

    @property
    def description(self) -> str:
        return "List offense saved searches available on the connected QRadar deployment."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .string("filter")
                .description("Optional AQL-style filter expression")
            .string("sort")
                .description("Optional sort expression")
            .integer("limit")
                .description("Maximum number of saved searches to return")
                .minimum(1)
                .maximum(10000)
            .integer("offset")
                .description("Number of saved searches to skip")
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
            "/siem/offense_saved_searches",
            params=params,
            headers=build_headers(start=start, end=end),
        )
        response.raise_for_status()
        return self.create_success_response(json.dumps(response.json(), indent=2))
