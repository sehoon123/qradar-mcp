# Copyright 2026 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""Composite Ariel workflow for retrieving offense event evidence."""

from typing import Any, Dict
import asyncio

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema
from qradar_mcp.tools.ariel.aql_validation import parse_aql_validation_response


DEFAULT_EVENT_FIELDS = (
    "starttime",
    "sourceip",
    "destinationip",
    "username",
    "qid",
    "QIDDESCRIPTION(qid) AS event_name",
    "LOGSOURCENAME(logsourceid) AS log_source",
    "magnitude",
)

ALLOWED_EVENT_FIELDS = frozenset({
    "starttime",
    "sourceip",
    "destinationip",
    "username",
    "qid",
    "magnitude",
    "credibility",
    "relevance",
    "severity",
    "logsourceid",
    "QIDDESCRIPTION(qid) AS event_name",
    "LOGSOURCENAME(logsourceid) AS log_source",
})

DEFAULT_TIME_WINDOW_MINUTES = 360
MAX_TIME_WINDOW_MINUTES = 1440
DEFAULT_MAX_EVENTS = 100
MAX_EVENTS = 1000


class InvestigateOffenseEventsTool(MCPTool):
    """Tool that runs a read-only Ariel workflow for offense-related events."""

    @property
    def name(self) -> str:
        return "investigate_offense_events"

    @property
    def description(self) -> str:
        return """Retrieve offense-related Ariel event evidence.

The workflow gets the offense, builds an offense-scoped AQL query, validates it,
creates a transient Ariel search, polls status, then returns metadata and result
rows. It does not mutate QRadar data, but it does create a transient search job."""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .integer("offense_id")
                .description("QRadar offense ID")
                .minimum(1)
                .required()
            .integer("time_window_minutes")
                .description("Ariel time window in minutes (default: 360, max: 1440)")
                .minimum(1)
                .maximum(MAX_TIME_WINDOW_MINUTES)
                .default(DEFAULT_TIME_WINDOW_MINUTES)
            .integer("max_events")
                .description("Maximum event rows to return (default: 100, max: 1000)")
                .minimum(1)
                .maximum(MAX_EVENTS)
                .default(DEFAULT_MAX_EVENTS)
            .string("fields")
                .description("Optional comma-separated event fields from the safe allowlist")
            .integer("max_poll_attempts")
                .description("Maximum status polling attempts after search creation (default: 3)")
                .minimum(1)
                .maximum(20)
                .default(3)
            .integer("poll_interval_seconds")
                .description("Seconds between polling attempts (default: 1, max: 10)")
                .minimum(0)
                .maximum(10)
                .default(1)
            .build())

    @property
    def http_verb(self) -> str:
        return "POST"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        offense_id = arguments.get("offense_id")
        if offense_id is None:
            return self.create_error_response("Error: offense_id is required")
        try:
            offense_id = self._bounded_int(offense_id, "offense_id", 1, 2_147_483_647)
        except ValueError as exc:
            return self.create_error_response(f"Error: {exc}")

        workflow_args = {**arguments, "offense_id": offense_id}

        offense = await self._get_json(f"/siem/offenses/{offense_id}")
        try:
            query_expression = self._build_aql(workflow_args)
        except ValueError as exc:
            return self.create_error_response(f"Error: {exc}")

        validation = await self._validate_aql(query_expression)
        if not validation["valid"]:
            return self.create_json_response({
                "offense_id": offense_id,
                "valid": False,
                "validation": validation,
            })

        search = await self._create_search(query_expression)
        search_id = self._extract_search_id(search)
        if not search_id:
            return self.create_error_response(f"Error: Ariel search response did not include a search ID: {search}")

        status = await self._poll_search_status(search_id, arguments)
        output = await self._collect_search_output(search_id, status, arguments)

        return self.create_json_response({
            "offense_id": offense_id,
            "offense": offense,
            "query_expression": query_expression,
            "validation": validation,
            "search_id": search_id,
            "search": search,
            "final_status": status,
            "metadata": output["metadata"],
            "results": output["results"],
            "recommended_next_call": self._recommended_next_call(
                workflow_args,
                search_id,
                status,
                output["metadata"],
            ),
            "warnings": output["warnings"],
        })

    async def _poll_search_status(self, search_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Poll an Ariel search until a terminal state or the configured bound."""
        status: Dict[str, Any] = {}
        for attempt in range(int(arguments.get("max_poll_attempts", 3))):
            if attempt > 0:
                await asyncio.sleep(int(arguments.get("poll_interval_seconds", 1)))
            status = await self._get_json(f"/ariel/searches/{search_id}")
            if str(status.get("status", "")).upper() in {"COMPLETED", "ERROR", "CANCELED"}:
                break
        return status

    async def _collect_search_output(
        self,
        search_id: str,
        status: Dict[str, Any],
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Fetch metadata/results for completed searches and warnings otherwise."""
        if str(status.get("status", "")).upper() != "COMPLETED":
            return {
                "metadata": None,
                "results": None,
                "warnings": [
                    "Search did not complete within polling limits. Re-run "
                    "investigate_offense_events with higher polling bounds, or use "
                    "an operator profile that exposes Ariel job status/result tools."
                ],
            }

        max_events = self._bounded_int(
            arguments.get("max_events", DEFAULT_MAX_EVENTS),
            "max_events",
            1,
            MAX_EVENTS,
        )
        return {
            "metadata": await self._get_json(f"/ariel/searches/{search_id}/metadata"),
            "results": await self._get_results(search_id, max_events),
            "warnings": [],
        }

    def _build_aql(self, arguments: Dict[str, Any]) -> str:
        offense_id = self._bounded_int(arguments.get("offense_id"), "offense_id", 1, 2_147_483_647)
        select_fields = self._normalize_select_fields(arguments.get("fields"))
        max_events = self._bounded_int(
            arguments.get("max_events", DEFAULT_MAX_EVENTS),
            "max_events",
            1,
            MAX_EVENTS,
        )
        time_window = self._bounded_int(
            arguments.get("time_window_minutes", DEFAULT_TIME_WINDOW_MINUTES),
            "time_window_minutes",
            1,
            MAX_TIME_WINDOW_MINUTES,
        )
        return (
            f"SELECT {select_fields} FROM events "
            f"WHERE INOFFENSE({offense_id}) "
            f"ORDER BY starttime DESC LIMIT {max_events} LAST {time_window} MINUTES"
        )

    @staticmethod
    def _normalize_select_fields(raw_fields: Any) -> str:
        """Return a SELECT field list constrained to safe event fields."""
        if not raw_fields:
            return ", ".join(DEFAULT_EVENT_FIELDS)

        requested = [field.strip() for field in str(raw_fields).split(",") if field.strip()]
        if not requested:
            return ", ".join(DEFAULT_EVENT_FIELDS)

        invalid = [field for field in requested if field not in ALLOWED_EVENT_FIELDS]
        if invalid:
            raise ValueError(f"Unsupported Ariel event fields: {invalid}")

        return ", ".join(requested)

    @staticmethod
    def _bounded_int(value: Any, name: str, minimum: int, maximum: int) -> int:
        """Parse an integer argument and enforce hard bounds."""
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be an integer") from exc
        if parsed < minimum or parsed > maximum:
            raise ValueError(f"{name} must be between {minimum} and {maximum}")
        return parsed

    async def _validate_aql(self, query_expression: str) -> Dict[str, Any]:
        response = await self.client.post(
            "/ariel/validators/aql",
            params={"query_expression": query_expression},
        )
        if response.status_code >= 500:
            response.raise_for_status()
        return parse_aql_validation_response(response)

    async def _create_search(self, query_expression: str) -> Dict[str, Any]:
        response = await self.client.post(
            "/ariel/searches",
            params={"query_expression": query_expression},
        )
        response.raise_for_status()
        return response.json()

    async def _get_results(self, search_id: str, max_events: int) -> Any:
        response = await self.client.get(
            f"/ariel/searches/{search_id}/results",
            headers={"Range": f"items=0-{max_events - 1}"},
        )
        response.raise_for_status()
        return response.json()

    async def _get_json(self, path: str) -> Any:
        response = await self.client.get(path)
        response.raise_for_status()
        return response.json()

    def _extract_search_id(self, search: Dict[str, Any]) -> str | None:
        for key in ("search_id", "id"):
            if search.get(key):
                return str(search[key])
        return None

    @staticmethod
    def _recommended_next_call(arguments: Dict[str, Any], search_id: str, status: Dict[str, Any],
                               metadata: Any) -> Dict[str, Any] | None:
        """Return public-capability-compatible guidance for incomplete searches."""
        if str(status.get("status", "")).upper() == "COMPLETED":
            return None

        return {
            "tool": "investigate_offense_events",
            "reason": "rerun_workflow_with_longer_polling_bounds",
            "search_id": search_id,
            "current_status": status.get("status", "UNKNOWN"),
            "arguments": {
                "offense_id": arguments["offense_id"],
                "time_window_minutes": arguments.get(
                    "time_window_minutes",
                    DEFAULT_TIME_WINDOW_MINUTES,
                ),
                "max_events": arguments.get("max_events", DEFAULT_MAX_EVENTS),
                "fields": arguments.get("fields"),
                "max_poll_attempts": min(
                    max(int(arguments.get("max_poll_attempts", 3)) * 2, 6),
                    20,
                ),
                "poll_interval_seconds": arguments.get("poll_interval_seconds", 1),
            },
            "operator_profile_note": (
                "Ariel job status/result tools can inspect this search_id when "
                "an operator profile exposes them."
            ),
            "metadata_available": metadata is not None,
        }
