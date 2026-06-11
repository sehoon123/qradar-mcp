"""QRadar deployment diagnostics for MCP operators."""

from ipaddress import ip_address
from typing import Any, Dict
from urllib.parse import urlparse

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.compatibility import get_fail_mode, refresh_catalog
from qradar_mcp.tools.endpoint_registry import ENDPOINT_SPECS
from qradar_mcp.tools.schema import schema
from qradar_mcp.utils.feature_toggle_manager import get_feature_toggle_manager


class QradarDoctorTool(MCPTool):
    """Tool for checking QRadar connection, API, auth, and exposure posture."""

    @property
    def name(self) -> str:
        return "qradar_doctor"

    @property
    def description(self) -> str:
        return """Run non-mutating QRadar MCP diagnostics.

Checks local QRadar transport settings, configured Version header, /help catalog
availability, identity probe behavior, and feature-toggle exposure posture.
Use this before enabling broader profiles or after QRadar upgrades."""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .boolean("format_output")
                .description("Format output as human-readable text (default: false)")
                .default(False)
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _check_compatibility(self) -> str | None:
        """Doctor diagnoses compatibility failures, so it must not be gated."""
        return None

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        report = {
            "qradar_host": self._transport_report(),
            "api": await self._api_report(),
            "auth": await self._auth_report(),
            "compatibility": await self._compatibility_report(),
            "feature_toggles": self._feature_toggle_report(),
            "tool_registry": {
                "endpoint_spec_count": len(ENDPOINT_SPECS),
                "groups": self._tool_group_counts(),
            },
            "recommendations": [],
        }
        report["recommendations"] = self._recommendations(report)

        if arguments.get("format_output", False):
            return self.create_success_response(self._format_report(report))
        return self.create_json_response(report)

    def _transport_report(self) -> Dict[str, Any]:
        raw_host = getattr(self.client, "_url", None)  # pylint: disable=protected-access
        parsed = urlparse(str(raw_host) if raw_host and "://" in str(raw_host) else f"https://{raw_host or ''}")
        hostname = parsed.hostname or ""
        private_network = self._is_private_or_internal_host(hostname)
        allow_plain_http = bool(
            getattr(self.client, "_allow_plain_http_private_network", False)  # pylint: disable=protected-access
        )

        risk = "ok"
        if parsed.scheme == "http":
            risk = "token_sent_without_tls"

        return {
            "configured": bool(raw_host),
            "raw": raw_host,
            "scheme": parsed.scheme,
            "host": parsed.netloc,
            "private_or_internal": private_network,
            "allow_plain_http_private_network": allow_plain_http,
            "risk": risk,
        }

    async def _api_report(self) -> Dict[str, Any]:
        configured = getattr(self.client, "_api_version", None)  # pylint: disable=protected-access
        payload = {
            "configured_version": configured,
            "versions_available": False,
            "console_max_version": None,
            "error": None,
        }
        try:
            response = await self.client.get("/help/versions")
            response.raise_for_status()
            versions = response.json() or []
            payload["versions_available"] = True
            payload["console_max_version"] = self._max_version(versions)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            payload["error"] = str(exc)
        return payload

    async def _auth_report(self) -> Dict[str, Any]:
        payload = {
            "identity_probe": "failed",
            "identity_type": None,
            "id": None,
            "label": None,
            "error": None,
        }
        try:
            user_id, username = await self.client.identify_user()
            if username and user_id:
                payload.update({
                    "identity_probe": "ok",
                    "identity_type": "user",
                    "id": user_id,
                    "label": username,
                })
                return payload

            service_id, service_label = await self.client.identify_authorized_service()
            if service_label and service_id:
                payload.update({
                    "identity_probe": "ok",
                    "identity_type": "authorized_service",
                    "id": service_id,
                    "label": service_label,
                })
        except Exception as exc:  # pylint: disable=broad-exception-caught
            payload["error"] = str(exc)
        return payload

    async def _compatibility_report(self) -> Dict[str, Any]:
        catalog = await refresh_catalog(self.client)
        return {
            "fail_mode": get_fail_mode(),
            "catalog_loaded": catalog.loaded,
            "catalog_available": catalog.available,
            "endpoint_count": catalog.endpoint_count,
            "console_max_api_version": catalog.max_api_version,
        }

    def _feature_toggle_report(self) -> Dict[str, Any]:
        manager = get_feature_toggle_manager()
        if manager is None:
            return {"available": False}
        disabled_groups = [
            group for group, enabled in sorted(manager.group_toggles.items())
            if not enabled
        ]
        return {
            "available": True,
            "read_only_mode": manager.read_only_mode,
            "compatibility_gate_enabled": manager.compatibility_gate_enabled,
            "verb_toggles": manager.verb_toggles,
            "disabled_groups": disabled_groups,
            "read_only_post_allowlist": manager.read_only_post_allowlist,
        }

    @staticmethod
    def _tool_group_counts() -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for spec in ENDPOINT_SPECS.values():
            counts[spec.group] = counts.get(spec.group, 0) + 1
        return dict(sorted(counts.items()))

    @staticmethod
    def _is_private_or_internal_host(hostname: str) -> bool:
        normalized = hostname.lower()
        if normalized == "localhost":
            return True
        if normalized.endswith((".local", ".internal", ".lan")):
            return True
        try:
            return ip_address(normalized).is_private
        except ValueError:
            return False

    @staticmethod
    def _max_version(versions: Any) -> str | None:
        best_value = float("-inf")
        best_version = None
        for item in versions:
            value = item.get("version") if isinstance(item, dict) else item
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            if numeric > best_value:
                best_value = numeric
                best_version = str(value)
        return best_version

    @staticmethod
    def _recommendations(report: Dict[str, Any]) -> list[str]:
        recommendations = []
        transport = report["qradar_host"]
        if transport["scheme"] == "http":
            recommendations.append(
                "Prefer HTTPS if the QRadar certificate can be trusted; SEC tokens are sent without TLS over HTTP."
            )
        if transport["scheme"] == "http" and not transport["private_or_internal"]:
            recommendations.append("Plain HTTP should only be used for private or internal QRadar hosts.")
        api = report["api"]
        if not api["configured_version"]:
            recommendations.append("Set qradar.api_version to pin the QRadar Version header.")
        compatibility = report["compatibility"]
        if not compatibility["catalog_available"]:
            recommendations.append("Ensure /help/versions and /help/endpoints are reachable by the configured token.")
        if compatibility["fail_mode"] == "open":
            recommendations.append("Use compatibility.fail_mode='closed' for stricter production deployments.")
        auth = report["auth"]
        if auth["identity_probe"] != "ok":
            recommendations.append("Identity probe failed; verify token permissions or use auth.identity_probe deliberately.")
        return recommendations

    @staticmethod
    def _format_report(report: Dict[str, Any]) -> str:
        transport = report["qradar_host"]
        api = report["api"]
        auth = report["auth"]
        compatibility = report["compatibility"]
        lines = [
            "QRadar MCP Doctor",
            "=" * 80,
            f"QRadar host: {transport['raw'] or 'not configured'}",
            f"Transport: {transport['scheme']} ({transport['risk']})",
            f"Configured API version: {api['configured_version'] or 'not set'}",
            f"Console max API version: {api['console_max_version'] or 'unknown'}",
            f"Identity probe: {auth['identity_probe']} ({auth['identity_type'] or 'unknown'})",
            f"Compatibility catalog: {'available' if compatibility['catalog_available'] else 'unavailable'}",
            f"Compatibility fail mode: {compatibility['fail_mode']}",
            f"Endpoint catalog count: {compatibility['endpoint_count']}",
        ]
        if report["recommendations"]:
            lines.extend(["", "Recommendations:"])
            lines.extend(f"- {item}" for item in report["recommendations"])
        return "\n".join(lines)
