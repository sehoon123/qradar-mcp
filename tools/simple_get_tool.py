# Copyright 2026 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""Small bases for straightforward read-only QRadar GET endpoint wrappers."""

from typing import Any, Dict

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema
from qradar_mcp.utils.parameters import build_headers, build_query_params, parse_range_from_limit_offset


class SimpleListTool(MCPTool):
    """Base for list-style GET endpoints with filter/sort/fields/range support."""

    tool_name = ""
    tool_description = ""
    endpoint = ""
    default_limit = 50
    max_limit = 10000

    @property
    def name(self) -> str:
        return self.tool_name

    @property
    def description(self) -> str:
        return self.tool_description

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .string("filter")
                .description("Optional QRadar filter expression")
            .string("sort")
                .description("Optional sort expression, e.g. '+name' or '-id'")
            .integer("limit")
                .description(f"Maximum rows to return (default: {self.default_limit})")
                .minimum(1)
                .maximum(self.max_limit)
                .default(self.default_limit)
            .integer("offset")
                .description("Number of rows to skip (default: 0)")
                .minimum(0)
                .default(0)
            .string("fields")
                .description("Optional comma-separated list of fields to return")
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        fields = arguments.get("fields")
        sort = arguments.get("sort")
        params = build_query_params(
            filter_expr=arguments.get("filter"),
            sort_fields=[sort] if sort else None,
            fields=[field.strip() for field in fields.split(",")] if fields else None,
        )
        start, end = parse_range_from_limit_offset(
            limit=arguments.get("limit", self.default_limit),
            offset=arguments.get("offset", 0),
        )
        response = await self.client.get(
            self.endpoint,
            params=params if params else None,
            headers=build_headers(start=start, end=end),
        )
        response.raise_for_status()
        return self.create_json_response(response.json())


class SimpleGetByIdTool(MCPTool):
    """Base for GET endpoints that retrieve one item by path parameter."""

    tool_name = ""
    tool_description = ""
    endpoint_template = ""
    id_argument = "id"
    id_description = "Resource ID"
    id_type = "integer"

    @property
    def name(self) -> str:
        return self.tool_name

    @property
    def description(self) -> str:
        return self.tool_description

    @property
    def input_schema(self) -> Dict[str, Any]:
        builder = schema()
        if self.id_type == "string":
            builder = (builder
                .string(self.id_argument)
                    .description(self.id_description)
                    .min_length(1)
                    .required())
        else:
            builder = (builder
                .integer(self.id_argument)
                    .description(self.id_description)
                    .minimum(0)
                    .required())
        return (builder
            .string("fields")
                .description("Optional comma-separated list of fields to return")
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        value = arguments.get(self.id_argument)
        if value is None or value == "":
            return self.create_error_response(f"Error: {self.id_argument} is required")

        params = {}
        if arguments.get("fields"):
            params["fields"] = arguments["fields"]

        response = await self.client.get(
            self.endpoint_template.format(**{self.id_argument: value}),
            params=params if params else None,
        )
        response.raise_for_status()
        return self.create_json_response(response.json())
