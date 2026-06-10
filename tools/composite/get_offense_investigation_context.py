# Copyright 2026 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Composite Offense Investigation Context Tool

Builds a read-only investigation bundle for a QRadar offense using only GET
requests. This tool intentionally avoids any mutating HTTP method.
"""

from typing import Any, Dict, Iterable, List, Optional, Tuple
import json

import httpx

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema
from qradar_mcp.utils.parameters import build_headers


class GetOffenseInvestigationContextTool(MCPTool):
    """Tool for collecting read-only investigation context for an offense."""

    @property
    def name(self) -> str:
        return "get_offense_investigation_context"

    @property
    def description(self) -> str:
        return """Collect read-only investigation context for a QRadar offense.

The tool retrieves the offense, optional notes, related source and local
destination address records, related analytics rule details, and optional asset
matches for discovered IP addresses. It only uses QRadar GET requests and is
intended for safe triage workflows where data must not be changed."""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .integer("offense_id")
                .description("The QRadar offense ID to investigate")
                .minimum(0)
                .required()
            .boolean("include_notes")
                .description("Include offense notes")
                .default(True)
            .boolean("include_address_context")
                .description("Include source and local destination address records")
                .default(True)
            .boolean("include_rule_details")
                .description("Include analytics rule details when rule IDs are present")
                .default(True)
            .boolean("include_assets")
                .description("Look up assets for IP addresses discovered in the context")
                .default(False)
            .integer("notes_limit")
                .description("Maximum number of offense notes to retrieve")
                .minimum(1)
                .maximum(100)
                .default(20)
            .integer("related_item_limit")
                .description("Maximum related addresses, rules, and asset IPs to expand")
                .minimum(1)
                .maximum(100)
                .default(25)
            .boolean("format_output")
                .description("Return a concise human-readable summary instead of JSON")
                .default(False)
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        offense_id = arguments.get("offense_id")
        if offense_id is None:
            return self.create_error_response("Error: offense_id is required")

        offense_id = int(offense_id)
        notes_limit = int(arguments.get("notes_limit", 20))
        related_item_limit = int(arguments.get("related_item_limit", 25))

        context: Dict[str, Any] = {
            "offense_id": offense_id,
            "read_only": True,
            "http_methods_used": ["GET"],
            "offense": await self._get_required_json(f"/siem/offenses/{offense_id}"),
            "notes": None,
            "source_addresses": None,
            "local_destination_addresses": None,
            "rules": None,
            "assets": None,
            "warnings": [],
        }

        offense = context["offense"]

        if arguments.get("include_notes", True):
            context["notes"] = await self._safe_get_notes(offense_id, notes_limit)

        source_ids = self._extract_id_list(offense, "source_address_ids", related_item_limit)
        destination_ids = self._extract_id_list(offense, "local_destination_address_ids", related_item_limit)

        if arguments.get("include_address_context", True):
            context["source_addresses"] = await self._safe_get_collection_by_ids(
                "/siem/source_addresses",
                source_ids,
                related_item_limit,
                "source_addresses",
                context["warnings"]
            )
            context["local_destination_addresses"] = await self._safe_get_collection_by_ids(
                "/siem/local_destination_addresses",
                destination_ids,
                related_item_limit,
                "local_destination_addresses",
                context["warnings"]
            )

        if arguments.get("include_rule_details", True):
            rule_ids = self._extract_rule_ids(offense, related_item_limit)
            context["rules"] = await self._safe_get_rules(rule_ids, context["warnings"])

        if arguments.get("include_assets", False):
            ips = self._collect_ips(context, related_item_limit)
            context["assets"] = await self._safe_get_assets_for_ips(ips, context["warnings"])

        if arguments.get("format_output", False):
            return self.create_success_response(self._format_context(context))

        return self.create_success_response(json.dumps(context, indent=2))

    async def _get_required_json(self, path: str) -> Any:
        response = await self.client.get(path)
        response.raise_for_status()
        return response.json()

    async def _safe_get_json(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Tuple[Optional[Any], Optional[str]]:
        try:
            response = await self.client.get(path, params=params, headers=headers)
            response.raise_for_status()
            return response.json(), None
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            return None, str(exc)

    async def _safe_get_notes(self, offense_id: int, limit: int) -> Dict[str, Any]:
        headers = build_headers(start=0, end=limit - 1)
        notes, error = await self._safe_get_json(f"/siem/offenses/{offense_id}/notes", headers=headers)
        if error:
            return {"error": error, "items": []}
        return {"count": len(notes or []), "items": notes or []}

    async def _safe_get_collection_by_ids(
        self,
        path: str,
        item_ids: List[int],
        limit: int,
        label: str,
        warnings: List[str]
    ) -> Dict[str, Any]:
        if not item_ids:
            return {"count": 0, "items": []}

        limited_ids = item_ids[:limit]
        params = {"filter": f"id in ({','.join(str(item_id) for item_id in limited_ids)})"}
        items, error = await self._safe_get_json(path, params=params)
        if error:
            warnings.append(f"Unable to retrieve {label}: {error}")
            return {"error": error, "requested_ids": limited_ids, "items": []}
        return {
            "count": len(items or []),
            "requested_ids": limited_ids,
            "items": items or [],
        }

    async def _safe_get_rules(self, rule_ids: List[int], warnings: List[str]) -> Dict[str, Any]:
        rules = []
        errors = []
        for rule_id in rule_ids:
            rule, error = await self._safe_get_json(f"/analytics/rules/{rule_id}")
            if error:
                errors.append({"rule_id": rule_id, "error": error})
            else:
                rules.append(rule)

        if errors:
            warnings.append(f"Unable to retrieve {len(errors)} rule(s)")

        return {
            "count": len(rules),
            "items": rules,
            "errors": errors,
        }

    async def _safe_get_assets_for_ips(self, ips: List[str], warnings: List[str]) -> Dict[str, Any]:
        assets_by_ip = {}
        errors = []

        for ip_address in ips:
            params = {
                "filter": f"interfaces(ip_addresses(value))='{ip_address}'",
                "fields": "id,hostnames,interfaces(ip_addresses),risk_score_sum,vulnerability_count,domain_id"
            }
            assets, error = await self._safe_get_json("/asset_model/assets", params=params)
            if error:
                errors.append({"ip": ip_address, "error": error})
            else:
                assets_by_ip[ip_address] = assets or []

        if errors:
            warnings.append(f"Unable to retrieve assets for {len(errors)} IP address(es)")

        return {
            "ip_count": len(ips),
            "items_by_ip": assets_by_ip,
            "errors": errors,
        }

    def _extract_id_list(self, source: Dict[str, Any], field_name: str, limit: int) -> List[int]:
        raw_items = source.get(field_name) or []
        result = []
        for raw_item in raw_items:
            try:
                result.append(int(raw_item))
            except (TypeError, ValueError):
                continue
        return result[:limit]

    def _extract_rule_ids(self, offense: Dict[str, Any], limit: int) -> List[int]:
        rule_ids = []
        for rule in offense.get("rules") or []:
            if isinstance(rule, dict):
                raw_id = rule.get("id")
            else:
                raw_id = rule
            try:
                rule_ids.append(int(raw_id))
            except (TypeError, ValueError):
                continue
        return self._unique_ints(rule_ids)[:limit]

    def _collect_ips(self, context: Dict[str, Any], limit: int) -> List[str]:
        ips = []
        for section_name in ("source_addresses", "local_destination_addresses"):
            section = context.get(section_name) or {}
            for item in section.get("items") or []:
                ips.extend(self._extract_ip_values(item))
        return self._unique_strings(ips)[:limit]

    def _extract_ip_values(self, value: Any) -> List[str]:
        if isinstance(value, str) and self._looks_like_ip(value):
            return [value]
        if isinstance(value, list):
            ips = []
            for item in value:
                ips.extend(self._extract_ip_values(item))
            return ips
        if isinstance(value, dict):
            ips = []
            for key, item in value.items():
                if key in ("source_ip", "local_destination_ip", "destination_ip", "value", "ip_address"):
                    ips.extend(self._extract_ip_values(item))
                elif isinstance(item, (dict, list)):
                    ips.extend(self._extract_ip_values(item))
            return ips
        return []

    def _format_context(self, context: Dict[str, Any]) -> str:
        offense = context.get("offense") or {}
        lines = [
            f"Offense {context['offense_id']} investigation context",
            "=" * 80,
            f"Description: {offense.get('description', 'N/A')}",
            f"Status: {offense.get('status', 'N/A')}",
            f"Severity: {offense.get('severity', 'N/A')}",
            f"Magnitude: {offense.get('magnitude', 'N/A')}",
            f"Credibility: {offense.get('credibility', 'N/A')}",
            f"Relevance: {offense.get('relevance', 'N/A')}",
            f"Event count: {offense.get('event_count', 'N/A')}",
            f"Flow count: {offense.get('flow_count', 'N/A')}",
            "",
            f"Notes: {self._section_count(context, 'notes')}",
            f"Source addresses: {self._section_count(context, 'source_addresses')}",
            f"Local destination addresses: {self._section_count(context, 'local_destination_addresses')}",
            f"Rules: {self._section_count(context, 'rules')}",
            f"Asset IP lookups: {(context.get('assets') or {}).get('ip_count', 0)}",
        ]

        warnings = context.get("warnings") or []
        if warnings:
            lines.extend(["", "Warnings:"])
            lines.extend(f"- {warning}" for warning in warnings)

        return "\n".join(lines)

    def _section_count(self, context: Dict[str, Any], section_name: str) -> int:
        section = context.get(section_name) or {}
        if isinstance(section, dict):
            return int(section.get("count", 0))
        return 0

    def _unique_ints(self, values: Iterable[int]) -> List[int]:
        seen = set()
        result = []
        for value in values:
            if value not in seen:
                seen.add(value)
                result.append(value)
        return result

    def _unique_strings(self, values: Iterable[str]) -> List[str]:
        seen = set()
        result = []
        for value in values:
            if value not in seen:
                seen.add(value)
                result.append(value)
        return result

    def _looks_like_ip(self, value: str) -> bool:
        parts = value.split(".")
        if len(parts) != 4:
            return False
        try:
            return all(0 <= int(part) <= 255 for part in parts)
        except ValueError:
            return False
