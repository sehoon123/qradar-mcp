# Copyright 2026 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""Composite Ariel workflow for retrieving offense event evidence."""

from typing import Any, Dict
import asyncio

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema


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
                .minimum(0)
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

        offense = await self._get_json(f"/siem/offenses/{int(offense_id)}")
        try:
            query_expression = self._build_aql(arguments)
        except ValueError as exc:
            return self.create_error_response(f"Error: {exc}")

        validation = await self._validate_aql(query_expression)
        if not validation["valid"]:
            return self.create_json_response({
                "offense_id": offense_id,
                "valid": False,
                "query_expression": query_expression,
                "validation": validation,
            })

        search = await self._create_search(query_expression)
        search_id = self._extract_search_id(search)
        if not search_id:
            return self.create_error_response(f"Error: Ariel search response did not include a search ID: {search}")

        status = search
        for attempt in range(int(arguments.get("max_poll_attempts", 3))):
            if attempt > 0:
                await asyncio.sleep(int(arguments.get("poll_interval_seconds", 1)))
            status = await self._get_json(f"/ariel/searches/{search_id}")
            if str(status.get("status", "")).upper() in {"COMPLETED", "ERROR", "CANCELED"}:
                break

        metadata = None
        results = None
        warnings = []
        if str(status.get("status", "")).upper() == "COMPLETED":
            metadata = await self._get_json(f"/ariel/searches/{search_id}/metadata")
            max_events = self._bounded_int(
                arguments.get("max_events", DEFAULT_MAX_EVENTS),
                "max_events",
                1,
                MAX_EVENTS,
            )
            results = await self._get_results(search_id, max_events)
        else:
            warnings.append("Search did not complete within polling limits; use get_ariel_search_status/results later.")

        return self.create_json_response({
            "offense_id": offense_id,
            "offense": offense,
            "query_expression": query_expression,
            "validation": validation,
            "search_id": search_id,
            "search": search,
            "final_status": status,
            "metadata": metadata,
            "results": results,
            "warnings": warnings,
        })

    def _build_aql(self, arguments: Dict[str, Any]) -> str:
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
            f"WHERE INOFFENSE({int(arguments['offense_id'])}) "
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
        if response.status_code == 200:
            data = response.json()
            return {"valid": True, "details": data, "warnings": data.get("warnings", [])}
        if response.status_code == 422:
            return {"valid": False, "details": response.json()}
        response.raise_for_status()
        return {"valid": False, "details": response.text}

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
