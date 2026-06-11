"""Tests for EndpointSpec coverage across registered tools."""

import json
from unittest.mock import AsyncMock, Mock

from qradar_mcp.tools.endpoint_registry import ENDPOINT_SPECS
from qradar_mcp.tools.fastmcp_adapter import _load_tool_class, register_all_tools
from qradar_mcp.utils.feature_toggle_manager import FeatureToggleManager


def _all_enabled_manager(tmp_path):
    config = {
        "read_only_mode": False,
        "verb_toggles": {"GET": True, "POST": True, "DELETE": True, "PUT": True, "PATCH": True},
        "group_toggles": {
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
        },
        "per_tool_toggles": {},
    }
    path = tmp_path / "feature_toggles.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return FeatureToggleManager(str(path))


def test_all_registered_tools_have_endpoint_specs(tmp_path):
    mock_mcp = Mock()
    mock_mcp.tool = Mock(return_value=lambda func: func)
    registered_tools, skipped_tools = register_all_tools(
        mock_mcp,
        _all_enabled_manager(tmp_path),
        AsyncMock(),
    )

    assert skipped_tools == []
    registered_class_names = {type(tool).__name__ for tool in registered_tools}
    assert registered_class_names == set(ENDPOINT_SPECS)


def test_all_endpoint_specs_resolve_to_tool_classes():
    """Every EndpointSpec must point to an importable MCPTool class."""
    for class_name, spec in ENDPOINT_SPECS.items():
        tool_class = _load_tool_class(spec)
        assert tool_class.__name__ == class_name


def test_p1_read_only_endpoint_specs_present():
    expected = {
        "ListReferenceSetEntriesTool": ("GET", "/reference_data_collections/set_entries"),
        "GetReferenceSetEntryTool": ("GET", "/reference_data_collections/set_entries/{entry_id}"),
        "GetReferenceSetDependentsTool": ("GET", "/reference_data_collections/sets/{set_id}/dependents"),
        "GetSetBulkUpdateTaskTool": ("GET", "/reference_data_collections/set_bulk_update_tasks/{task_status_id}"),
        "GetSetBulkUpdateTaskResultsTool": (
            "GET",
            "/reference_data_collections/set_bulk_update_tasks/{task_status_id}/results",
        ),
        "GetSetDeleteTaskTool": ("GET", "/reference_data_collections/set_delete_tasks/{task_status_id}"),
        "GetOffenseNoteTool": ("GET", "/siem/offenses/{offense_id}/notes/{note_id}"),
        "ListOffenseAssignableActorsTool": ("GET", "/siem/offenses/{offense_id}/assignable_actors"),
        "ListOffenseSavedSearchesTool": ("GET", "/siem/offense_saved_searches"),
        "GetOffenseSavedSearchTool": ("GET", "/siem/offense_saved_searches/{search_id}"),
        "ListOffensesOcsfTool": ("GET", "/siem/offenses_ocsf"),
        "GetSourceAddressTool": ("GET", "/siem/source_addresses/{source_address_id}"),
        "GetLocalDestinationAddressTool": (
            "GET",
            "/siem/local_destination_addresses/{local_destination_address_id}",
        ),
    }

    for class_name, endpoint in expected.items():
        spec = ENDPOINT_SPECS[class_name]
        assert spec.required_endpoints == (endpoint,)
        assert spec.read_only is True


def test_p2_read_only_endpoint_specs_present():
    expected = {
        "GetArielSearchMetadataTool": ("GET", "/ariel/searches/{search_id}/metadata"),
        "ListQradarApiVersionsTool": ("GET", "/help/versions"),
        "GetQradarApiVersionTool": ("GET", "/help/versions/{version_id}"),
        "GetQradarEndpointTool": ("GET", "/help/endpoints/{endpoint_id}"),
        "ListQradarResourcesTool": ("GET", "/help/resources"),
        "GetQradarResourceTool": ("GET", "/help/resources/{resource_id}"),
        "ListQradarMetricsTool": ("GET", "/health/metrics/qradar_metrics"),
        "GetQradarMetricTool": ("GET", "/health/metrics/qradar_metrics/{metric_id}"),
        "ListSystemMetricsTool": ("GET", "/health/metrics/system_metrics"),
        "GetSystemMetricTool": ("GET", "/health/metrics/system_metrics/{metric_id}"),
        "ListCaptureRecoveriesTool": ("GET", "/forensics/capture/recoveries"),
        "GetCaptureRecoveryTool": ("GET", "/forensics/capture/recoveries/{recovery_id}"),
        "ListCaptureRecoveryTasksTool": ("GET", "/forensics/capture/recovery_tasks"),
        "GetCaptureRecoveryTaskTool": ("GET", "/forensics/capture/recovery_tasks/{task_id}"),
        "GetCaseCreateTaskTool": ("GET", "/forensics/case_management/case_create_tasks/{task_id}"),
        "ListQvmFiltersTool": ("GET", "/qvm/filters"),
        "ListQvmNetworkTool": ("GET", "/qvm/network"),
        "ListQvmOpenservicesTool": ("GET", "/qvm/openservices"),
        "ListQvmSavedSearchGroupsTool": ("GET", "/qvm/saved_search_groups"),
        "GetQvmSavedSearchGroupTool": ("GET", "/qvm/saved_search_groups/{group_id}"),
        "ListQvmSavedSearchesTool": ("GET", "/qvm/saved_searches"),
        "GetQvmSavedSearchTool": ("GET", "/qvm/saved_searches/{saved_search_id}"),
        "CreateQvmVulnInstanceSearchTool": ("GET", "/qvm/saved_searches/{saved_search_id}/vuln_instances"),
        "GetQvmVulnInstanceSearchStatusTool": (
            "GET",
            "/qvm/saved_searches/vuln_instances/{task_id}/status",
        ),
        "ListQvmVulnInstanceResultAssetsTool": (
            "GET",
            "/qvm/saved_searches/vuln_instances/{task_id}/results/assets",
        ),
        "ListQvmVulnInstanceResultInstancesTool": (
            "GET",
            "/qvm/saved_searches/vuln_instances/{task_id}/results/vuln_instances",
        ),
        "ListQvmVulnInstanceResultVulnerabilitiesTool": (
            "GET",
            "/qvm/saved_searches/vuln_instances/{task_id}/results/vulnerabilities",
        ),
    }

    for class_name, endpoint in expected.items():
        spec = ENDPOINT_SPECS[class_name]
        assert spec.required_endpoints == (endpoint,)
        assert spec.read_only is True

    doctor = ENDPOINT_SPECS["QradarDoctorTool"]
    assert doctor.required_endpoints == (
        ("GET", "/help/versions"),
        ("GET", "/help/endpoints"),
    )
    assert doctor.read_only is True


def test_p2_composite_ariel_workflow_spec_present():
    spec = ENDPOINT_SPECS["InvestigateOffenseEventsTool"]
    assert spec.required_endpoints[0] == ("POST", "/ariel/searches")
    assert ("POST", "/ariel/validators/aql") in spec.required_endpoints
    assert ("GET", "/ariel/searches/{search_id}/metadata") in spec.required_endpoints
    assert spec.read_only is True
    assert spec.side_effect == "transient_search_job"


def test_ariel_cancel_search_spec_present():
    spec = ENDPOINT_SPECS["CancelArielSearchTool"]
    assert spec.required_endpoints == (("POST", "/ariel/searches/{search_id}"),)
    assert spec.read_only is True
    assert spec.side_effect == "transient_search_job_cancel"
