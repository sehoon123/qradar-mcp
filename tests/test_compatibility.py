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


"""Tests for runtime QRadar API compatibility gating (tools/compatibility.py)."""

import asyncio
import json
import tempfile
import time

import qradar_mcp.tools.compatibility as compat
from qradar_mcp.tools.compatibility import (
    BASELINE_API_VERSION,
    CATALOG_FAILURE_TTL,
    COMPATIBILITY_REGISTRY,
    gate_tool_call,
    get_catalog,
    normalize_path,
    refresh_catalog,
    reset_catalog,
)


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------
class _Resp:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data

    def raise_for_status(self):
        return None


class _Client:
    """Fake QRadarRestClient.get returning canned /help responses (single page)."""

    def __init__(self, endpoints, versions=None, fail=False):
        self._endpoints = endpoints
        self._versions = versions if versions is not None else [{"version": "24.0"}]
        self._fail = fail
        self.calls = []

    async def get(self, api_path, headers=None, **_kwargs):
        self.calls.append(api_path)
        if self._fail:
            raise RuntimeError("help unreachable")
        if api_path == "/help/versions":
            return _Resp(self._versions)
        if api_path == "/help/endpoints":
            # Single page: return all on the first range, empty afterwards.
            rng = (headers or {}).get("Range", "items=0-")
            if rng.startswith("items=0-"):
                return _Resp(self._endpoints)
            return _Resp([])
        raise AssertionError(f"unexpected path {api_path}")


def _make_tool(class_name, client=None, name="fake_tool"):
    """Build a duck-typed tool whose class name matches a registry key."""
    cls = type(class_name, (), {})
    tool = cls()
    tool.client = client
    tool.name = name
    return tool


def _prime_catalog(endpoints, available=True, max_version="24.0"):
    """Manually populate the singleton catalog as if freshly loaded."""
    reset_catalog()
    catalog = get_catalog()
    catalog._loaded = True            # pylint: disable=protected-access
    catalog._available = available    # pylint: disable=protected-access
    catalog._endpoints = set(endpoints)  # pylint: disable=protected-access
    catalog._max_api_version = max_version  # pylint: disable=protected-access
    catalog._loaded_at = time.monotonic()   # pylint: disable=protected-access
    return catalog


# ---------------------------------------------------------------------------
# normalize_path
# ---------------------------------------------------------------------------
def test_normalize_path_equivalences():
    assert normalize_path("/ariel/searches/{search_id}") == "ariel/searches/*"
    assert normalize_path("ariel/searches/{id}") == "ariel/searches/*"
    assert normalize_path("/api/ariel/searches/{x}") == "ariel/searches/*"
    assert normalize_path("/health_data/top_offenses") == "health_data/top_offenses"
    assert normalize_path("") == ""


# ---------------------------------------------------------------------------
# Catalog loading
# ---------------------------------------------------------------------------
def test_catalog_loads_and_matches_templated_paths():
    reset_catalog()
    client = _Client(
        endpoints=[
            {"http_method": "GET", "path": "/ariel/searches/{search_id}/results"},
            {"http_method": "POST", "path": "/ariel/searches"},
        ],
        versions=[{"version": "19.0"}, {"version": "24.0"}, {"version": "22.0"}],
    )
    catalog = get_catalog()
    asyncio.run(catalog.ensure_loaded(client))

    assert catalog.available is True
    assert catalog.max_api_version == "24.0"
    assert catalog.supports("GET", "/ariel/searches/{search_id}/results")
    assert catalog.supports("post", "ariel/searches")
    assert not catalog.supports("GET", "/health_data/top_offenses")


def test_catalog_loads_only_once_within_ttl():
    reset_catalog()
    client = _Client(endpoints=[{"http_method": "GET", "path": "/health_data/top_offenses"}])
    catalog = get_catalog()
    asyncio.run(catalog.ensure_loaded(client))
    asyncio.run(catalog.ensure_loaded(client))
    assert client.calls.count("/help/endpoints") == 1


def test_catalog_pages_through_help_endpoints():
    reset_catalog()
    original = compat._HELP_ENDPOINTS_PAGE_SIZE  # pylint: disable=protected-access
    compat._HELP_ENDPOINTS_PAGE_SIZE = 2         # pylint: disable=protected-access
    try:
        pages = {
            "items=0-1": [
                {"http_method": "GET", "path": "/ariel/databases"},
                {"http_method": "GET", "path": "/ariel/functions"},
            ],
            "items=2-3": [{"http_method": "GET", "path": "/health_data/top_offenses"}],
        }

        class PagingClient:
            def __init__(self):
                self.ranges = []

            async def get(self, api_path, headers=None, **_kwargs):
                if api_path == "/help/versions":
                    return _Resp([{"version": "24.0"}])
                if api_path == "/help/endpoints":
                    rng = (headers or {}).get("Range")
                    self.ranges.append(rng)
                    return _Resp(pages.get(rng, []))
                raise AssertionError(api_path)

        client = PagingClient()
        catalog = get_catalog()
        asyncio.run(catalog.ensure_loaded(client))

        assert catalog.available
        assert catalog.supports("GET", "/ariel/databases")
        assert catalog.supports("GET", "/ariel/functions")
        assert catalog.supports("GET", "/health_data/top_offenses")
        assert client.ranges == ["items=0-1", "items=2-3"]
    finally:
        compat._HELP_ENDPOINTS_PAGE_SIZE = original  # pylint: disable=protected-access


def test_catalog_fail_open_when_help_unreachable():
    reset_catalog()
    client = _Client(endpoints=[], fail=True)
    catalog = get_catalog()
    asyncio.run(catalog.ensure_loaded(client))
    assert catalog.loaded is True
    assert catalog.available is False


def test_catalog_failure_retried_after_ttl():
    reset_catalog()
    catalog = get_catalog()
    asyncio.run(catalog.ensure_loaded(_Client(endpoints=[], fail=True)))
    assert catalog.available is False

    good = _Client(endpoints=[{"http_method": "GET", "path": "/health_data/top_offenses"}])
    # Within the failure TTL: no retry.
    asyncio.run(catalog.ensure_loaded(good))
    assert good.calls == []

    # Backdate past the failure TTL: should retry and succeed.
    catalog._loaded_at -= (CATALOG_FAILURE_TTL + 1)  # pylint: disable=protected-access
    asyncio.run(catalog.ensure_loaded(good))
    assert catalog.available is True
    assert good.calls.count("/help/endpoints") == 1


def test_refresh_catalog_forces_reload():
    reset_catalog()
    client = _Client(endpoints=[{"http_method": "GET", "path": "/health_data/top_offenses"}])
    asyncio.run(refresh_catalog(client))
    assert get_catalog().available
    asyncio.run(refresh_catalog(client))
    assert client.calls.count("/help/endpoints") == 2


# ---------------------------------------------------------------------------
# gate_tool_call
# ---------------------------------------------------------------------------
def test_gate_ungated_tool_allowed():
    reset_catalog()
    tool = _make_tool("SomeToolNotInRegistry")
    assert asyncio.run(gate_tool_call(tool)) is None


def test_gate_blocks_when_endpoint_missing():
    _prime_catalog(endpoints=set())
    tool = _make_tool("ListTopOffensesTool", name="list_top_offenses")
    message = asyncio.run(gate_tool_call(tool))
    assert message is not None
    assert "not supported" in message
    assert "/health_data/top_offenses" in message


def test_gate_allows_when_endpoint_present():
    _prime_catalog(endpoints={("GET", "health_data/top_offenses")})
    tool = _make_tool("ListTopOffensesTool")
    assert asyncio.run(gate_tool_call(tool)) is None


def test_gate_fail_open_when_catalog_unavailable():
    _prime_catalog(endpoints=set(), available=False)
    tool = _make_tool("ListTopOffensesTool")
    assert asyncio.run(gate_tool_call(tool)) is None


def test_gate_lazy_loads_via_tool_client():
    reset_catalog()
    client = _Client(endpoints=[{"http_method": "GET", "path": "/health_data/top_offenses"}])
    tool = _make_tool("ListTopOffensesTool", client=client)
    assert asyncio.run(gate_tool_call(tool)) is None
    assert client.calls.count("/help/endpoints") == 1


def test_gate_lazy_load_blocks_missing():
    reset_catalog()
    client = _Client(endpoints=[{"http_method": "GET", "path": "/ariel/databases"}])
    tool = _make_tool("ListTopOffensesTool", name="list_top_offenses", client=client)
    message = asyncio.run(gate_tool_call(tool))
    assert message is not None and "/health_data/top_offenses" in message


# ---------------------------------------------------------------------------
# Composite tool: required core vs optional endpoints
# ---------------------------------------------------------------------------
def test_composite_allowed_with_only_core_offense_endpoint():
    # Optional endpoints (notes/addresses/rules/assets) are absent but not gated.
    _prime_catalog(endpoints={("GET", "siem/offenses/*")})
    tool = _make_tool("GetOffenseInvestigationContextTool", name="get_offense_investigation_context")
    assert asyncio.run(gate_tool_call(tool)) is None


def test_composite_blocked_when_core_offense_missing():
    _prime_catalog(endpoints=set())
    tool = _make_tool("GetOffenseInvestigationContextTool", name="get_offense_investigation_context")
    message = asyncio.run(gate_tool_call(tool))
    assert message is not None
    assert "/siem/offenses/{offense_id}" in message


# ---------------------------------------------------------------------------
# Unsupported message content
# ---------------------------------------------------------------------------
def test_unsupported_message_includes_metadata():
    _prime_catalog(endpoints=set(), max_version="22.0")
    tool = _make_tool("CreateArielSearchTool", name="create_ariel_search")
    message = asyncio.run(gate_tool_call(tool))
    assert "min API 24.0" in message
    assert "read-only" in message
    assert "side effect: transient_search_job" in message
    assert "API version 22.0" in message


# ---------------------------------------------------------------------------
# Registry invariants
# ---------------------------------------------------------------------------
def test_registry_entries_respect_baseline():
    for class_name, entry in COMPATIBILITY_REGISTRY.items():
        version = entry.get("min_api_version", BASELINE_API_VERSION)
        assert float(version) <= float(BASELINE_API_VERSION), (
            f"{class_name} requires API {version} > baseline {BASELINE_API_VERSION}"
        )
        assert entry.get("required_endpoints"), f"{class_name} has no required_endpoints"


def test_all_registry_entries_are_read_only():
    for class_name, entry in COMPATIBILITY_REGISTRY.items():
        assert entry.get("read_only") is True, f"{class_name} is not marked read_only"


def test_ariel_search_marked_read_only_with_side_effect():
    entry = COMPATIBILITY_REGISTRY["CreateArielSearchTool"]
    assert entry.get("read_only") is True
    assert entry.get("side_effect") == "transient_search_job"


def test_saved_search_tools_registered():
    assert ("GET", "/ariel/saved_searches") in COMPATIBILITY_REGISTRY["ListSavedSearchesTool"]["required_endpoints"]
    assert COMPATIBILITY_REGISTRY["GetSavedSearchTool"]["required_endpoints"][0] == ("GET", "/ariel/saved_searches/{id}")


def test_ariel_metadata_expansion_tools_registered():
    assert COMPATIBILITY_REGISTRY["GetArielDatabaseColumnsTool"]["required_endpoints"][0] == (
        "GET", "/ariel/databases/{database_name}"
    )
    assert COMPATIBILITY_REGISTRY["ListArielLookupsTool"]["required_endpoints"][0] == ("GET", "/ariel/lookups")
    assert COMPATIBILITY_REGISTRY["GetArielLookupTool"]["required_endpoints"][0] == ("GET", "/ariel/lookups/{name}")


def test_composite_has_optional_endpoints_not_in_required():
    entry = COMPATIBILITY_REGISTRY["GetOffenseInvestigationContextTool"]
    assert entry["required_endpoints"] == [("GET", "/siem/offenses/{offense_id}")]
    optional_paths = {path for _, path in entry["optional_endpoints"]}
    assert "/siem/offenses/{offense_id}/notes" in optional_paths
    assert "/asset_model/assets" in optional_paths


# ---------------------------------------------------------------------------
# Feature toggle plumbing for the gate on/off switch
# ---------------------------------------------------------------------------
def test_feature_toggle_loads_compatibility_gate_flag():
    from qradar_mcp.utils.feature_toggle_manager import FeatureToggleManager

    tmp_dir = tempfile.mkdtemp()
    disabled = f"{tmp_dir}/disabled.json"
    with open(disabled, "w", encoding="utf-8") as handle:
        json.dump({"verb_toggles": {"GET": True}, "group_toggles": {},
                   "compatibility_gate_enabled": False}, handle)
    assert FeatureToggleManager(disabled).compatibility_gate_enabled is False

    default = f"{tmp_dir}/default.json"
    with open(default, "w", encoding="utf-8") as handle:
        json.dump({"verb_toggles": {"GET": True}, "group_toggles": {}}, handle)
    assert FeatureToggleManager(default).compatibility_gate_enabled is True
