"""Tests for public MCP capability registration."""

import json
import subprocess
import sys
from unittest.mock import AsyncMock, Mock

from qradar_mcp.tools.capability_registry import CAPABILITY_SPECS
from qradar_mcp.tools.endpoint_registry import ENDPOINT_SPECS
from qradar_mcp.tools.fastmcp_adapter import _load_tool_class, register_all_tools
from qradar_mcp.utils.feature_toggle_manager import FeatureToggleManager


def _manager(tmp_path, *, disabled_tool=None, disabled_group=None, read_only_mode=False):
    groups = {
        "offense": True,
        "ariel": True,
        "reference_data": True,
        "asset": True,
        "log_source": True,
        "analytics": True,
        "system": True,
        "config": True,
        "data_classification": True,
        "health_data": True,
        "help": True,
        "services": True,
        "composite": True,
        "forensics": True,
        "qvm": True,
    }
    if disabled_group:
        groups[disabled_group] = False

    config = {
        "read_only_mode": read_only_mode,
        "verb_toggles": {"GET": True, "POST": True, "DELETE": True, "PUT": True, "PATCH": True},
        "group_toggles": groups,
        "read_only_post_allowlist": [
            "ValidateAQLTool",
            "InvestigateOffenseEventsTool",
        ],
        "per_tool_toggles": {disabled_tool: False} if disabled_tool else {},
    }
    path = tmp_path / "feature_toggles.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return FeatureToggleManager(str(path))


def _register(tmp_path, **manager_kwargs):
    mock_mcp = Mock()
    mock_mcp.tool = Mock(return_value=lambda func: func)
    return register_all_tools(mock_mcp, _manager(tmp_path, **manager_kwargs), AsyncMock())


def test_tools_package_does_not_eager_import_mutating_modules():
    """Importing qradar_mcp.tools must not load every endpoint wrapper."""
    code = """
import qradar_mcp.tools
import sys

for module_name in (
    "qradar_mcp.tools.offense.update_offense",
    "qradar_mcp.tools.reference_data.delete_reference_set",
):
    if module_name in sys.modules:
        raise SystemExit(f"unexpected eager import: {module_name}")
"""
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True, text=True)


def test_public_capabilities_are_a_small_surface():
    """EndpointSpec is the internal catalog; CapabilitySpec is the public surface."""
    assert len(ENDPOINT_SPECS) > 100
    assert 1 < len(CAPABILITY_SPECS) < 20


def test_capability_endpoints_are_declared():
    """Capabilities may be pure workflows, but they must declare dependencies."""
    for spec in CAPABILITY_SPECS.values():
        assert spec.required_endpoints


def test_all_capability_specs_resolve_to_tool_classes():
    """Every public CapabilitySpec must point to an importable MCPTool class."""
    for class_name, spec in CAPABILITY_SPECS.items():
        tool_class = _load_tool_class(spec)
        assert tool_class.__name__ == class_name


def test_register_all_tools_uses_capabilities_not_endpoint_specs(tmp_path):
    registered_tools, skipped_tools = _register(tmp_path)

    assert skipped_tools == []
    registered_class_names = {type(tool).__name__ for tool in registered_tools}
    assert registered_class_names == set(CAPABILITY_SPECS)
    assert registered_class_names != set(ENDPOINT_SPECS)

    # Low-level endpoint wrappers stay available as internal implementation
    # units but are not directly exposed as public MCP tools.
    assert "GetArielSearchResultsTool" in ENDPOINT_SPECS
    assert "GetArielSearchResultsTool" not in registered_class_names
    assert "GetOffenseNotesTool" in ENDPOINT_SPECS
    assert "GetOffenseNotesTool" not in registered_class_names


def test_default_public_tool_names_are_expected(tmp_path):
    registered_tools, _skipped_tools = _register(tmp_path, read_only_mode=True)

    assert len(registered_tools) <= 10
    assert {tool.name for tool in registered_tools} == {
        "qradar_doctor",
        "discover_qradar_endpoints",
        "list_offenses",
        "get_offense_investigation_context",
        "investigate_offense_events",
        "validate_aql",
    }


def test_feature_toggles_filter_public_capabilities_only(tmp_path):
    registered_tools, skipped_tools = _register(tmp_path, disabled_tool="QradarDoctorTool")

    assert len(registered_tools) + len(skipped_tools) == len(CAPABILITY_SPECS)
    assert "qradar_doctor" not in {tool.name for tool in registered_tools}
    assert "qradar_doctor" in {tool.name for tool in skipped_tools}


def test_group_toggle_filters_public_capabilities(tmp_path):
    registered_tools, skipped_tools = _register(tmp_path, disabled_group="help")

    assert all(tool.tool_group != "help" for tool in registered_tools)
    assert {type(tool).__name__ for tool in skipped_tools if tool.tool_group == "help"} == {
        "DiscoverQradarEndpointsTool",
        "QradarDoctorTool",
    }


def test_read_only_mode_does_not_import_mutating_endpoint_modules(tmp_path, monkeypatch):
    """Read-only public registration must not import QRadar-mutating endpoint modules."""
    mutating_module_paths = {
        spec.module_path
        for spec in ENDPOINT_SPECS.values()
        if not spec.read_only
    }
    imported_modules = []

    from qradar_mcp.tools import fastmcp_adapter  # pylint: disable=import-outside-toplevel

    real_import_module = fastmcp_adapter.import_module

    def guarded_import_module(name):
        imported_modules.append(name)
        if name in mutating_module_paths:
            raise AssertionError(f"Mutating module should not be imported in read-only mode: {name}")
        return real_import_module(name)

    monkeypatch.setattr(fastmcp_adapter, "import_module", guarded_import_module)

    registered_tools, skipped_tools = _register(tmp_path, read_only_mode=True)

    assert mutating_module_paths.isdisjoint(imported_modules)
    registered_non_get = {type(tool).__name__ for tool in registered_tools if tool.http_verb != "GET"}
    assert registered_non_get == {
        "ValidateAQLTool",
        "InvestigateOffenseEventsTool",
    }
    assert len(registered_tools) + len(skipped_tools) == len(CAPABILITY_SPECS)
