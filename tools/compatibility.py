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
Runtime QRadar API compatibility gating.

This fork targets an API 24.0+ baseline but is run against QRadar consoles of
varying versions and license/module configurations. Rather than trust the
documentation, the *connected console* is treated as the source of truth: on the
first tool call we lazily fetch ``GET /help/versions`` and ``GET /help/endpoints``
(paging through all results) and cache the set of supported ``(method, path)``
pairs. A tool that declares ``required_endpoints`` is blocked at call time (with a
clear message) when the console does not expose those endpoints.

Design notes:
  * The gate runs at call time, not at server startup. In FastMCP HTTP mode the
    QRadar auth token is injected per-request, so there is no authenticated
    client at import/registration time. ``gate_tool_call`` reuses the calling
    tool's ``client`` (which carries the active request's auth).
  * Fail mode is configurable. The default is fail-closed: if the catalog cannot
    be fetched (network error, /help denied), gated tools are blocked. Lab
    deployments can explicitly set fail-open so calls proceed when the catalog
    source of truth is unavailable.
  * The catalog is cached with a TTL (a process talks to a single console). A
    failed load is cached only briefly so a transient outage does not disable
    gating for the whole process life; a successful load is cached longer and is
    refreshed after expiry (picks up a console upgrade without a restart).
    ``reset_catalog()``/``refresh_catalog()`` force a reload.
  * ``required_endpoints`` are gated. ``optional_endpoints`` are metadata only
    (the tool degrades gracefully when they are absent) and are never gated.
  * Imports are kept to the standard library; logging is best-effort and lazily
    imported so this module (and its tests) load without the full server stack.
"""

import asyncio
import time
from typing import Dict, List, Optional, Set, Tuple

from qradar_mcp.tools.capability_registry import compatibility_registry_from_capabilities
from qradar_mcp.tools.endpoint_registry import compatibility_registry_from_specs
from qradar_mcp.utils.structured_logger import log_structured

# ---------------------------------------------------------------------------
# Compatibility registry: tool class name -> requirements.
#
#   required_endpoints : list of (HTTP_METHOD, PATH_TEMPLATE) the tool must have.
#   optional_endpoints : (opt) endpoints the tool uses but degrades without; not gated.
#   min_api_version    : earliest QRadar API version the endpoints exist in.
#   read_only          : True if the tool does not mutate QRadar data.
#   side_effect        : optional note on non-mutating side effects (honesty).
#
# This legacy dict is merged with the EndpointSpec registry below. Paths are
# taken verbatim from each tool's client call; normalize_path() absorbs
# leading-slash, "/api/" prefix and placeholder-name differences when matching
# the catalog.
# ---------------------------------------------------------------------------
COMPATIBILITY_REGISTRY: Dict[str, Dict] = {  # pylint: disable=invalid-name
    # Ariel metadata (AQL authoring helpers)
    "ListArielDatabasesTool": {
        "required_endpoints": [("GET", "/ariel/databases")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    "ListArielFunctionsTool": {
        "required_endpoints": [("GET", "/ariel/functions")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    "GetArielParserKeywordsTool": {
        "required_endpoints": [("GET", "/ariel/parser_keywords")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    "GetArielDatabaseColumnsTool": {
        "required_endpoints": [("GET", "/ariel/databases/{database_name}")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    "ListArielLookupsTool": {
        "required_endpoints": [("GET", "/ariel/lookups")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    "GetArielLookupTool": {
        "required_endpoints": [("GET", "/ariel/lookups/{name}")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    # Ariel read-only querying (POST that creates a transient search job)
    "CreateArielSearchTool": {
        "required_endpoints": [("POST", "/ariel/searches")],
        "min_api_version": "24.0",
        "read_only": True,
        "side_effect": "transient_search_job",
    },
    "GetArielSearchStatusTool": {
        "required_endpoints": [("GET", "/ariel/searches/{search_id}")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    "GetArielSearchResultsTool": {
        "required_endpoints": [("GET", "/ariel/searches/{search_id}/results")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    "ValidateAQLTool": {
        "required_endpoints": [("POST", "/ariel/validators/aql")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    # Ariel saved searches (read-only browsing)
    "ListSavedSearchesTool": {
        "required_endpoints": [("GET", "/ariel/saved_searches")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    "GetSavedSearchTool": {
        "required_endpoints": [("GET", "/ariel/saved_searches/{id}")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    # Health data
    "GetSecurityDataCountTool": {
        "required_endpoints": [("GET", "/health_data/security_data_count")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    "ListTopOffensesTool": {
        "required_endpoints": [("GET", "/health_data/top_offenses")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    "ListTopRulesTool": {
        "required_endpoints": [("GET", "/health_data/top_rules")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    # Data classification (event taxonomy)
    "ListQidRecordsTool": {
        "required_endpoints": [("GET", "/data_classification/qid_records")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    "GetQidRecordTool": {
        # Falls back to the list endpoint on 404, so only the list endpoint is required.
        "required_endpoints": [("GET", "/data_classification/qid_records")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    "ListDsmEventMappingsTool": {
        "required_endpoints": [("GET", "/data_classification/dsm_event_mappings")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    "ListLowLevelCategoriesTool": {
        "required_endpoints": [("GET", "/data_classification/low_level_categories")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    "ListHighLevelCategoriesTool": {
        "required_endpoints": [("GET", "/data_classification/high_level_categories")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    # Config (network hierarchy, domains, custom properties)
    "ListNetworkHierarchyTool": {
        "required_endpoints": [("GET", "/config/network_hierarchy/networks")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    "ListDomainsTool": {
        "required_endpoints": [("GET", "/config/domain_management/domains")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    "ListRegexPropertiesTool": {
        "required_endpoints": [("GET", "/config/event_sources/custom_properties/regex_properties")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    "ListCalculatedPropertiesTool": {
        "required_endpoints": [("GET", "/config/event_sources/custom_properties/calculated_properties")],
        "min_api_version": "24.0",
        "read_only": True,
    },
    # Composite read-only investigation bundle. Only the core offense GET is
    # required; the rest are optional (the tool degrades gracefully without them).
    "GetOffenseInvestigationContextTool": {
        "required_endpoints": [("GET", "/siem/offenses/{offense_id}")],
        "optional_endpoints": [
            ("GET", "/siem/offenses/{offense_id}/notes"),
            ("GET", "/siem/source_addresses"),
            ("GET", "/siem/local_destination_addresses"),
            ("GET", "/analytics/rules/{rule_id}"),
            ("GET", "/asset_model/assets"),
        ],
        "min_api_version": "24.0",
        "read_only": True,
    },
}
COMPATIBILITY_REGISTRY = compatibility_registry_from_specs(COMPATIBILITY_REGISTRY)  # pylint: disable=invalid-name
COMPATIBILITY_REGISTRY = compatibility_registry_from_capabilities(COMPATIBILITY_REGISTRY)  # pylint: disable=invalid-name

# The baseline API version this fork commits to supporting by default.
BASELINE_API_VERSION = "24.0"

# Catalog cache lifetimes (seconds). A successful load is cached longer; a failed
# load is retried sooner so a transient outage does not disable gating forever.
CATALOG_SUCCESS_TTL = 3600.0
CATALOG_FAILURE_TTL = 60.0
_FAIL_MODE = "closed"

# Page size used when paging through /help/endpoints.
_HELP_ENDPOINTS_PAGE_SIZE = 500
# Safety bound on total endpoints fetched (avoids an unbounded paging loop).
_HELP_ENDPOINTS_MAX = 100000


def _log(message: str, level: str = "INFO", **kwargs) -> None:
    """Best-effort structured logging that never fails if the logger is absent."""
    try:  # pragma: no cover - logging is environmental
        log_structured(message, level=level, **kwargs)
    except Exception:  # pylint: disable=broad-exception-caught
        pass


def normalize_path(path: str) -> str:
    """
    Normalize an API path for comparison.

    Strips a leading slash and an optional ``api/`` prefix, and replaces any
    ``{placeholder}`` segment with ``*`` so that placeholder-name and
    leading-slash differences do not affect matching.

        "/ariel/searches/{search_id}" -> "ariel/searches/*"
        "ariel/searches/{id}"         -> "ariel/searches/*"
        "/api/ariel/searches/{x}"     -> "ariel/searches/*"
    """
    if not path:
        return ""
    stripped = path.strip().lstrip("/")
    if stripped.startswith("api/"):
        stripped = stripped[len("api/"):]
    segments = []
    for segment in stripped.split("/"):
        if not segment:
            continue
        if segment.startswith("{") and segment.endswith("}"):
            segments.append("*")
        else:
            segments.append(segment)
    return "/".join(segments)


class QRadarEndpointCatalog:
    """
    Lazily-loaded, TTL-cached view of the connected console's supported endpoints.

    A single instance is shared per process (see ``get_catalog``). ``ensure_loaded``
    fetches ``/help/versions`` and (paged) ``/help/endpoints``; on any failure the
    catalog is marked unavailable (gating then fails open) and retried after a
    short TTL.
    """

    def __init__(self) -> None:
        self._endpoints: Set[Tuple[str, str]] = set()
        self._max_api_version: Optional[str] = None
        self._loaded: bool = False
        self._available: bool = False
        self._loaded_at: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def available(self) -> bool:
        """True if the endpoint catalog was successfully loaded."""
        return self._available

    @property
    def loaded(self) -> bool:
        """True once a load has been attempted (success or failure)."""
        return self._loaded

    @property
    def max_api_version(self) -> Optional[str]:
        """Highest API version reported by /help/versions, or None if unknown."""
        return self._max_api_version

    @property
    def endpoint_count(self) -> int:
        """Number of endpoints loaded from /help/endpoints."""
        return len(self._endpoints)

    def _is_expired(self) -> bool:
        """True if the cached result is older than its TTL and should be reloaded."""
        ttl = CATALOG_SUCCESS_TTL if self._available else CATALOG_FAILURE_TTL
        return (time.monotonic() - self._loaded_at) >= ttl

    async def ensure_loaded(self, client, force: bool = False) -> None:
        """Fetch and cache the endpoint catalog, honoring the TTL, using the client."""
        if not force and self._loaded and not self._is_expired():
            return
        async with self._lock:
            if not force and self._loaded and not self._is_expired():
                return
            try:
                await self._load(client)
                self._available = True
                _log(
                    "QRadar endpoint catalog loaded",
                    level="INFO",
                    endpoint_count=len(self._endpoints),
                    max_api_version=self._max_api_version,
                )
            except Exception as exc:  # pylint: disable=broad-exception-caught
                # Fail-open: gating is skipped until the (short) failure TTL elapses.
                self._available = False
                self._endpoints = set()
                _log(
                    "QRadar endpoint catalog unavailable; compatibility gating disabled",
                    level="WARNING",
                    error=str(exc),
                )
            finally:
                self._loaded = True
                self._loaded_at = time.monotonic()

    async def _load(self, client) -> None:
        """Populate endpoint set (paged) and max API version from /help."""
        self._max_api_version = await self._fetch_max_version(client)

        collected: Set[Tuple[str, str]] = set()
        start = 0
        while start < _HELP_ENDPOINTS_MAX:
            end = start + _HELP_ENDPOINTS_PAGE_SIZE - 1
            headers = {"Range": f"items={start}-{end}"}
            response = await client.get("/help/endpoints", headers=headers)
            response.raise_for_status()
            batch = response.json() or []
            for endpoint in batch:
                if not isinstance(endpoint, dict):
                    continue
                method = endpoint.get("http_method")
                path = endpoint.get("path")
                if not method or not path:
                    continue
                collected.add((str(method).upper(), normalize_path(str(path))))
            if len(batch) < _HELP_ENDPOINTS_PAGE_SIZE:
                break
            start += _HELP_ENDPOINTS_PAGE_SIZE
        self._endpoints = collected

    async def _fetch_max_version(self, client) -> Optional[str]:
        """Return the highest version string from /help/versions (best effort)."""
        try:
            response = await client.get("/help/versions")
            response.raise_for_status()
            versions = response.json()
        except Exception:  # pylint: disable=broad-exception-caught
            return None

        best_str: Optional[str] = None
        best_val: float = float("-inf")
        for item in versions or []:
            value = item.get("version") if isinstance(item, dict) else item
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            if numeric > best_val:
                best_val = numeric
                best_str = str(value)
        return best_str

    def supports(self, method: str, path: str) -> bool:
        """True if (method, path) exists in the loaded catalog."""
        return (str(method).upper(), normalize_path(path)) in self._endpoints


# Module-level singleton (one console per process).
_CATALOG: Optional[QRadarEndpointCatalog] = None


def get_catalog() -> QRadarEndpointCatalog:
    """Return the shared endpoint catalog, creating it on first use."""
    global _CATALOG  # pylint: disable=global-statement
    if _CATALOG is None:
        _CATALOG = QRadarEndpointCatalog()
    return _CATALOG


def reset_catalog() -> None:
    """Drop the cached catalog (used by tests)."""
    global _CATALOG  # pylint: disable=global-statement
    _CATALOG = None


def set_fail_mode(fail_mode: str) -> None:
    """Set compatibility catalog failure behavior."""
    global _FAIL_MODE  # pylint: disable=global-statement
    normalized = str(fail_mode or "open").strip().lower()
    if normalized not in {"open", "closed"}:
        raise ValueError("compatibility fail mode must be 'open' or 'closed'")
    _FAIL_MODE = normalized


def get_fail_mode() -> str:
    """Return current compatibility catalog failure behavior."""
    return _FAIL_MODE


async def refresh_catalog(client) -> QRadarEndpointCatalog:
    """Force a reload of the endpoint catalog using the given client."""
    catalog = get_catalog()
    await catalog.ensure_loaded(client, force=True)
    return catalog


def get_requirements(tool) -> Optional[Dict]:
    """Return the registry entry for a tool instance, or None if ungated."""
    return COMPATIBILITY_REGISTRY.get(type(tool).__name__)


async def gate_tool_call(tool) -> Optional[str]:
    """
    Check a tool's required endpoints against the connected console.

    Returns a user-facing error message if the tool is unsupported on this
    deployment, or None if the call may proceed (including the fail-open and
    ungated cases). ``optional_endpoints`` are never gated.
    """
    entry = get_requirements(tool)
    required: List[Tuple[str, str]] = (entry or {}).get("required_endpoints", [])
    if not required:
        return None  # ungated tool

    catalog = get_catalog()
    await catalog.ensure_loaded(tool.client)
    if not catalog.available:
        if get_fail_mode() == "closed":
            return _format_catalog_unavailable_message(tool, entry)
        return None  # fail-open: could not determine support

    missing = [(method, path) for method, path in required if not catalog.supports(method, path)]
    if not missing:
        return None

    return _format_unsupported_message(tool, entry, catalog, missing)


def _format_catalog_unavailable_message(tool, entry: Dict) -> str:
    """Build an operator-friendly fail-closed message."""
    min_version = entry.get("min_api_version", BASELINE_API_VERSION)
    return (
        f"Tool '{tool.name}' cannot run because the QRadar API compatibility "
        f"catalog is unavailable and compatibility fail mode is closed. "
        f"Required minimum API version: {min_version}. Ensure /help/versions "
        f"and /help/endpoints are reachable by this token, or set "
        f"compatibility.fail_mode to 'open' for lab use."
    )


def _format_unsupported_message(tool, entry: Dict, catalog: "QRadarEndpointCatalog",
                                missing: List[Tuple[str, str]]) -> str:
    """Build an operator-friendly 'not supported' message including key metadata."""
    missing_str = ", ".join(f"{method} {path}" for method, path in missing)
    deployment_version = catalog.max_api_version or "unknown"
    min_version = entry.get("min_api_version", BASELINE_API_VERSION)

    attributes = [f"min API {min_version}"]
    if entry.get("read_only"):
        attributes.append("read-only")
    if entry.get("side_effect"):
        attributes.append(f"side effect: {entry['side_effect']}")
    attribute_str = "; ".join(attributes)

    return (
        f"Tool '{tool.name}' ({attribute_str}) is not supported on the connected "
        f"QRadar deployment (API version {deployment_version}). "
        f"Missing required endpoint(s): {missing_str}."
    )
