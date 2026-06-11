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

"""Central QRadar endpoint metadata for MCP tools."""

from typing import Dict, Mapping, Optional

from qradar_mcp.tools.endpoint_spec import EndpointSpec, EndpointRef, HttpMethod


def _spec(
    class_name: str,
    tool_name: str,
    group: str,
    method: HttpMethod,
    path: str,
    *,
    min_api_version: str = "24.0",
    read_only: bool = True,
    side_effect: Optional[str] = None,
    deprecated: bool = False,
    permission_hint: Optional[str] = None,
    additional_required_endpoints: tuple[EndpointRef, ...] = (),
    optional_endpoints: tuple[EndpointRef, ...] = (),
) -> EndpointSpec:
    return EndpointSpec(
        tool_name=tool_name,
        class_name=class_name,
        group=group,
        method=method,
        path=path,
        min_api_version=min_api_version,
        read_only=read_only,
        side_effect=side_effect,
        deprecated=deprecated,
        permission_hint=permission_hint,
        additional_required_endpoints=additional_required_endpoints,
        optional_endpoints=optional_endpoints,
    )


ENDPOINT_SPECS: Dict[str, EndpointSpec] = {
    # Offense tools
    "GetOffenseTool": _spec("GetOffenseTool", "get_offense", "offense", "GET", "/siem/offenses/{offense_id}"),
    "ListOffensesTool": _spec("ListOffensesTool", "list_offenses", "offense", "GET", "/siem/offenses"),
    "UpdateOffenseTool": _spec("UpdateOffenseTool", "update_offense", "offense", "POST", "/siem/offenses/{offense_id}", read_only=False),
    "AddOffenseNoteTool": _spec("AddOffenseNoteTool", "add_offense_note", "offense", "POST", "/siem/offenses/{offense_id}/notes", read_only=False),
    "GetOffenseNotesTool": _spec("GetOffenseNotesTool", "get_offense_notes", "offense", "GET", "/siem/offenses/{offense_id}/notes"),
    "GetOffenseNoteTool": _spec("GetOffenseNoteTool", "get_offense_note", "offense", "GET", "/siem/offenses/{offense_id}/notes/{note_id}", min_api_version="27.0"),
    "ListOffenseAssignableActorsTool": _spec("ListOffenseAssignableActorsTool", "list_offense_assignable_actors", "offense", "GET", "/siem/offenses/{offense_id}/assignable_actors", min_api_version="27.0"),
    "ListOffenseClosingReasonsTool": _spec("ListOffenseClosingReasonsTool", "list_offense_closing_reasons", "offense", "GET", "/siem/offense_closing_reasons"),
    "ListOffenseTypesTool": _spec("ListOffenseTypesTool", "list_offense_types", "offense", "GET", "/siem/offense_types"),
    "ListSourceAddressesTool": _spec("ListSourceAddressesTool", "list_source_addresses", "offense", "GET", "/siem/source_addresses"),
    "GetSourceAddressTool": _spec("GetSourceAddressTool", "get_source_address", "offense", "GET", "/siem/source_addresses/{source_address_id}", min_api_version="27.0"),
    "ListLocalDestinationAddressesTool": _spec("ListLocalDestinationAddressesTool", "list_local_destination_addresses", "offense", "GET", "/siem/local_destination_addresses"),
    "GetLocalDestinationAddressTool": _spec("GetLocalDestinationAddressTool", "get_local_destination_address", "offense", "GET", "/siem/local_destination_addresses/{local_destination_address_id}", min_api_version="27.0"),
    "ListOffenseSavedSearchesTool": _spec("ListOffenseSavedSearchesTool", "list_offense_saved_searches", "offense", "GET", "/siem/offense_saved_searches", min_api_version="27.0"),
    "GetOffenseSavedSearchTool": _spec("GetOffenseSavedSearchTool", "get_offense_saved_search", "offense", "GET", "/siem/offense_saved_searches/{search_id}", min_api_version="27.0"),
    "ListOffensesOcsfTool": _spec("ListOffensesOcsfTool", "list_offenses_ocsf", "offense", "GET", "/siem/offenses_ocsf", min_api_version="27.0"),

    # Ariel tools
    "CreateArielSearchTool": _spec("CreateArielSearchTool", "create_ariel_search", "ariel", "POST", "/ariel/searches", side_effect="transient_search_job"),
    "GetArielSearchStatusTool": _spec("GetArielSearchStatusTool", "get_ariel_search_status", "ariel", "GET", "/ariel/searches/{search_id}"),
    "GetArielSearchResultsTool": _spec("GetArielSearchResultsTool", "get_ariel_search_results", "ariel", "GET", "/ariel/searches/{search_id}/results"),
    "DeleteArielSearchTool": _spec("DeleteArielSearchTool", "delete_ariel_search", "ariel", "DELETE", "/ariel/searches/{search_id}", read_only=False, side_effect="transient_search_job_delete"),
    "CancelArielSearchTool": _spec("CancelArielSearchTool", "cancel_ariel_search", "ariel", "POST", "/ariel/searches/{search_id}", side_effect="transient_search_job_cancel"),
    "ListSavedSearchesTool": _spec("ListSavedSearchesTool", "list_saved_searches", "ariel", "GET", "/ariel/saved_searches"),
    "GetSavedSearchTool": _spec("GetSavedSearchTool", "get_saved_search", "ariel", "GET", "/ariel/saved_searches/{id}"),
    "DeleteSavedSearchTool": _spec("DeleteSavedSearchTool", "delete_saved_search", "ariel", "DELETE", "/ariel/saved_searches/{id}", read_only=False),
    "ValidateAQLTool": _spec("ValidateAQLTool", "validate_aql", "ariel", "POST", "/ariel/validators/aql"),
    "ListArielDatabasesTool": _spec("ListArielDatabasesTool", "list_ariel_databases", "ariel", "GET", "/ariel/databases"),
    "ListArielFunctionsTool": _spec("ListArielFunctionsTool", "list_ariel_functions", "ariel", "GET", "/ariel/functions"),
    "GetArielParserKeywordsTool": _spec("GetArielParserKeywordsTool", "get_ariel_parser_keywords", "ariel", "GET", "/ariel/parser_keywords"),
    "GetArielDatabaseColumnsTool": _spec("GetArielDatabaseColumnsTool", "get_ariel_database_columns", "ariel", "GET", "/ariel/databases/{database_name}"),
    "ListArielLookupsTool": _spec("ListArielLookupsTool", "list_ariel_lookups", "ariel", "GET", "/ariel/lookups"),
    "GetArielLookupTool": _spec("GetArielLookupTool", "get_ariel_lookup", "ariel", "GET", "/ariel/lookups/{name}"),
    "GetArielSearchMetadataTool": _spec("GetArielSearchMetadataTool", "get_ariel_search_metadata", "ariel", "GET", "/ariel/searches/{search_id}/metadata", min_api_version="27.0"),

    # Reference data collection set tools
    "ListReferenceSets": _spec("ListReferenceSets", "list_reference_sets", "reference_data", "GET", "/reference_data_collections/sets"),
    "GetReferenceSetTool": _spec("GetReferenceSetTool", "get_reference_set", "reference_data", "GET", "/reference_data_collections/sets/{set_id}"),
    "CreateReferenceSetTool": _spec("CreateReferenceSetTool", "create_reference_set", "reference_data", "POST", "/reference_data_collections/sets", read_only=False),
    "UpdateReferenceSetTool": _spec("UpdateReferenceSetTool", "update_reference_set", "reference_data", "POST", "/reference_data_collections/sets/{set_id}", read_only=False),
    "DeleteReferenceSetTool": _spec("DeleteReferenceSetTool", "delete_reference_set", "reference_data", "DELETE", "/reference_data_collections/sets/{set_id}", read_only=False),
    "AddToReferenceSetTool": _spec("AddToReferenceSetTool", "add_to_reference_set", "reference_data", "POST", "/reference_data_collections/set_entries", read_only=False, additional_required_endpoints=(("GET", "/reference_data_collections/sets"),)),
    "RemoveFromReferenceSetTool": _spec("RemoveFromReferenceSetTool", "remove_from_reference_set", "reference_data", "DELETE", "/reference_data_collections/set_entries/{entry_id}", read_only=False),
    "ListReferenceSetEntriesTool": _spec("ListReferenceSetEntriesTool", "list_reference_set_entries", "reference_data", "GET", "/reference_data_collections/set_entries", min_api_version="27.0"),
    "GetReferenceSetEntryTool": _spec("GetReferenceSetEntryTool", "get_reference_set_entry", "reference_data", "GET", "/reference_data_collections/set_entries/{entry_id}", min_api_version="27.0"),
    "GetReferenceSetDependentsTool": _spec("GetReferenceSetDependentsTool", "get_reference_set_dependents", "reference_data", "GET", "/reference_data_collections/sets/{set_id}/dependents", min_api_version="27.0"),
    "GetSetBulkUpdateTaskTool": _spec("GetSetBulkUpdateTaskTool", "get_set_bulk_update_task", "reference_data", "GET", "/reference_data_collections/set_bulk_update_tasks/{task_status_id}", min_api_version="27.0"),
    "GetSetBulkUpdateTaskResultsTool": _spec("GetSetBulkUpdateTaskResultsTool", "get_set_bulk_update_task_results", "reference_data", "GET", "/reference_data_collections/set_bulk_update_tasks/{task_status_id}/results", min_api_version="27.0"),
    "GetSetDeleteTaskTool": _spec("GetSetDeleteTaskTool", "get_set_delete_task", "reference_data", "GET", "/reference_data_collections/set_delete_tasks/{task_status_id}", min_api_version="27.0"),

    # Legacy reference data maps/tables
    "ListReferenceMaps": _spec("ListReferenceMaps", "list_reference_maps", "reference_data", "GET", "/reference_data/maps", deprecated=True),
    "GetReferenceMap": _spec("GetReferenceMap", "get_reference_map", "reference_data", "GET", "/reference_data/maps/{name}", deprecated=True),
    "CreateReferenceMap": _spec("CreateReferenceMap", "create_reference_map", "reference_data", "POST", "/reference_data/maps", read_only=False, deprecated=True),
    "AddToReferenceMap": _spec("AddToReferenceMap", "add_to_reference_map", "reference_data", "POST", "/reference_data/maps/{name}", read_only=False, deprecated=True),
    "DeleteReferenceMap": _spec("DeleteReferenceMap", "delete_reference_map", "reference_data", "DELETE", "/reference_data/maps/{name}", read_only=False, deprecated=True),
    "RemoveFromReferenceMap": _spec("RemoveFromReferenceMap", "remove_from_reference_map", "reference_data", "DELETE", "/reference_data/maps/{name}/{key}", read_only=False, deprecated=True),
    "ListReferenceTables": _spec("ListReferenceTables", "list_reference_tables", "reference_data", "GET", "/reference_data/tables", deprecated=True),
    "GetReferenceTable": _spec("GetReferenceTable", "get_reference_table", "reference_data", "GET", "/reference_data/tables/{name}", deprecated=True),
    "CreateReferenceTable": _spec("CreateReferenceTable", "create_reference_table", "reference_data", "POST", "/reference_data/tables", read_only=False, deprecated=True),
    "AddToReferenceTable": _spec("AddToReferenceTable", "add_to_reference_table", "reference_data", "POST", "/reference_data/tables/{name}", read_only=False, deprecated=True),
    "DeleteReferenceTable": _spec("DeleteReferenceTable", "delete_reference_table", "reference_data", "DELETE", "/reference_data/tables/{name}", read_only=False, deprecated=True),
    "RemoveFromReferenceTable": _spec("RemoveFromReferenceTable", "remove_from_reference_table", "reference_data", "DELETE", "/reference_data/tables/{name}/{outer_key}/{inner_key}", read_only=False, deprecated=True),

    # Asset, log source, analytics, system, config
    "ListAssetsTool": _spec("ListAssetsTool", "list_assets", "asset", "GET", "/asset_model/assets"),
    "ListAssetPropertiesTool": _spec("ListAssetPropertiesTool", "list_asset_properties", "asset", "GET", "/asset_model/properties"),
    "ListLogSourcesTool": _spec("ListLogSourcesTool", "list_log_sources", "log_source", "GET", "/config/event_sources/log_source_management/log_sources"),
    "GetLogSourceTool": _spec("GetLogSourceTool", "get_log_source", "log_source", "GET", "/config/event_sources/log_source_management/log_sources/{log_source_id}"),
    "ListLogSourceTypesTool": _spec("ListLogSourceTypesTool", "list_log_source_types", "log_source", "GET", "/config/event_sources/log_source_management/log_source_types"),
    "ListRulesTool": _spec("ListRulesTool", "list_rules", "analytics", "GET", "/analytics/rules"),
    "GetRuleTool": _spec("GetRuleTool", "get_rule", "analytics", "GET", "/analytics/rules/{rule_id}"),
    "ListBuildingBlocksTool": _spec("ListBuildingBlocksTool", "list_building_blocks", "analytics", "GET", "/analytics/building_blocks"),
    "GetBuildingBlockTool": _spec("GetBuildingBlockTool", "get_building_block", "analytics", "GET", "/analytics/building_blocks/{building_block_id}"),
    "ListCustomActionsTool": _spec("ListCustomActionsTool", "list_custom_actions", "analytics", "GET", "/analytics/custom_actions/actions"),
    "GetCustomActionTool": _spec("GetCustomActionTool", "get_custom_action", "analytics", "GET", "/analytics/custom_actions/actions/{action_id}"),
    "GetSystemInfoTool": _spec("GetSystemInfoTool", "get_system_info", "system", "GET", "/system/about"),
    "ListServersTool": _spec("ListServersTool", "list_servers", "system", "GET", "/system/servers"),
    "ListUsersTool": _spec("ListUsersTool", "list_users", "config", "GET", "/config/access/users"),
    "ListUserRolesTool": _spec("ListUserRolesTool", "list_user_roles", "config", "GET", "/config/access/user_roles"),
    "ListNetworkHierarchyTool": _spec("ListNetworkHierarchyTool", "list_network_hierarchy", "config", "GET", "/config/network_hierarchy/networks"),
    "ListDomainsTool": _spec("ListDomainsTool", "list_domains", "config", "GET", "/config/domain_management/domains"),
    "ListRegexPropertiesTool": _spec("ListRegexPropertiesTool", "list_regex_properties", "config", "GET", "/config/event_sources/custom_properties/regex_properties"),
    "ListCalculatedPropertiesTool": _spec("ListCalculatedPropertiesTool", "list_calculated_properties", "config", "GET", "/config/event_sources/custom_properties/calculated_properties"),

    # Data classification, health data, help, services, forensics, QVM
    "ListQidRecordsTool": _spec("ListQidRecordsTool", "list_qid_records", "data_classification", "GET", "/data_classification/qid_records"),
    "GetQidRecordTool": _spec("GetQidRecordTool", "get_qid_record", "data_classification", "GET", "/data_classification/qid_records", optional_endpoints=(("GET", "/data_classification/qid_records/{qid}"),)),
    "ListDsmEventMappingsTool": _spec("ListDsmEventMappingsTool", "list_dsm_event_mappings", "data_classification", "GET", "/data_classification/dsm_event_mappings"),
    "ListLowLevelCategoriesTool": _spec("ListLowLevelCategoriesTool", "list_low_level_categories", "data_classification", "GET", "/data_classification/low_level_categories"),
    "ListHighLevelCategoriesTool": _spec("ListHighLevelCategoriesTool", "list_high_level_categories", "data_classification", "GET", "/data_classification/high_level_categories"),
    "GetSecurityDataCountTool": _spec("GetSecurityDataCountTool", "get_security_data_count", "health_data", "GET", "/health_data/security_data_count"),
    "ListTopOffensesTool": _spec("ListTopOffensesTool", "list_top_offenses", "health_data", "GET", "/health_data/top_offenses"),
    "ListTopRulesTool": _spec("ListTopRulesTool", "list_top_rules", "health_data", "GET", "/health_data/top_rules"),
    "ListQradarMetricsTool": _spec("ListQradarMetricsTool", "list_qradar_metrics", "health_data", "GET", "/health/metrics/qradar_metrics", min_api_version="27.0"),
    "GetQradarMetricTool": _spec("GetQradarMetricTool", "get_qradar_metric", "health_data", "GET", "/health/metrics/qradar_metrics/{metric_id}", min_api_version="27.0"),
    "ListSystemMetricsTool": _spec("ListSystemMetricsTool", "list_system_metrics", "health_data", "GET", "/health/metrics/system_metrics", min_api_version="27.0"),
    "GetSystemMetricTool": _spec("GetSystemMetricTool", "get_system_metric", "health_data", "GET", "/health/metrics/system_metrics/{metric_id}", min_api_version="27.0"),
    "DiscoverQradarEndpointsTool": _spec("DiscoverQradarEndpointsTool", "discover_qradar_endpoints", "help", "GET", "/help/endpoints"),
    "ListQradarApiVersionsTool": _spec("ListQradarApiVersionsTool", "list_qradar_api_versions", "help", "GET", "/help/versions", min_api_version="27.0"),
    "GetQradarApiVersionTool": _spec("GetQradarApiVersionTool", "get_qradar_api_version", "help", "GET", "/help/versions/{version_id}", min_api_version="27.0"),
    "GetQradarEndpointTool": _spec("GetQradarEndpointTool", "get_qradar_endpoint", "help", "GET", "/help/endpoints/{endpoint_id}", min_api_version="27.0"),
    "ListQradarResourcesTool": _spec("ListQradarResourcesTool", "list_qradar_resources", "help", "GET", "/help/resources", min_api_version="27.0"),
    "GetQradarResourceTool": _spec("GetQradarResourceTool", "get_qradar_resource", "help", "GET", "/help/resources/{resource_id}", min_api_version="27.0"),
    "GeolocateIpTool": _spec("GeolocateIpTool", "geolocate_ip", "services", "GET", "/services/geolocations", side_effect="external_network_lookup"),
    "DnsLookupTool": _spec("DnsLookupTool", "dns_lookup", "services", "POST", "/services/dns_lookups", side_effect="external_dns_lookup_task"),
    "GetDnsResultTool": _spec("GetDnsResultTool", "get_dns_result", "services", "GET", "/services/dns_lookups/{task_id}"),
    "WhoisLookupTool": _spec("WhoisLookupTool", "whois_lookup", "services", "POST", "/services/whois_lookups", side_effect="external_whois_lookup_task"),
    "GetWhoisResultTool": _spec("GetWhoisResultTool", "get_whois_result", "services", "GET", "/services/whois_lookups/{task_id}"),
    "ListCasesTool": _spec("ListCasesTool", "list_cases", "forensics", "GET", "/forensics/case_management/cases"),
    "GetCaseTool": _spec("GetCaseTool", "get_case", "forensics", "GET", "/forensics/case_management/cases/{case_id}"),
    "ListCaptureRecoveriesTool": _spec("ListCaptureRecoveriesTool", "list_capture_recoveries", "forensics", "GET", "/forensics/capture/recoveries", min_api_version="27.0"),
    "GetCaptureRecoveryTool": _spec("GetCaptureRecoveryTool", "get_capture_recovery", "forensics", "GET", "/forensics/capture/recoveries/{recovery_id}", min_api_version="27.0"),
    "ListCaptureRecoveryTasksTool": _spec("ListCaptureRecoveryTasksTool", "list_capture_recovery_tasks", "forensics", "GET", "/forensics/capture/recovery_tasks", min_api_version="27.0"),
    "GetCaptureRecoveryTaskTool": _spec("GetCaptureRecoveryTaskTool", "get_capture_recovery_task", "forensics", "GET", "/forensics/capture/recovery_tasks/{task_id}", min_api_version="27.0"),
    "GetCaseCreateTaskTool": _spec("GetCaseCreateTaskTool", "get_case_create_task", "forensics", "GET", "/forensics/case_management/case_create_tasks/{task_id}", min_api_version="27.0"),
    "ListVulnerabilitiesTool": _spec("ListVulnerabilitiesTool", "list_vulnerabilities", "qvm", "GET", "/qvm/vulns"),
    "ListQvmAssetsTool": _spec("ListQvmAssetsTool", "list_qvm_assets", "qvm", "GET", "/qvm/assets"),
    "ListQvmFiltersTool": _spec("ListQvmFiltersTool", "list_qvm_filters", "qvm", "GET", "/qvm/filters", min_api_version="27.0"),
    "ListQvmNetworkTool": _spec("ListQvmNetworkTool", "list_qvm_network", "qvm", "GET", "/qvm/network", min_api_version="27.0"),
    "ListQvmOpenservicesTool": _spec("ListQvmOpenservicesTool", "list_qvm_openservices", "qvm", "GET", "/qvm/openservices", min_api_version="27.0"),
    "ListQvmSavedSearchGroupsTool": _spec("ListQvmSavedSearchGroupsTool", "list_qvm_saved_search_groups", "qvm", "GET", "/qvm/saved_search_groups", min_api_version="27.0"),
    "GetQvmSavedSearchGroupTool": _spec("GetQvmSavedSearchGroupTool", "get_qvm_saved_search_group", "qvm", "GET", "/qvm/saved_search_groups/{group_id}", min_api_version="27.0"),
    "ListQvmSavedSearchesTool": _spec("ListQvmSavedSearchesTool", "list_qvm_saved_searches", "qvm", "GET", "/qvm/saved_searches", min_api_version="27.0"),
    "GetQvmSavedSearchTool": _spec("GetQvmSavedSearchTool", "get_qvm_saved_search", "qvm", "GET", "/qvm/saved_searches/{saved_search_id}", min_api_version="27.0"),
    "CreateQvmVulnInstanceSearchTool": _spec("CreateQvmVulnInstanceSearchTool", "create_qvm_vuln_instance_search", "qvm", "GET", "/qvm/saved_searches/{saved_search_id}/vuln_instances", min_api_version="27.0", side_effect="transient_qvm_vuln_instance_search"),
    "GetQvmVulnInstanceSearchStatusTool": _spec("GetQvmVulnInstanceSearchStatusTool", "get_qvm_vuln_instance_search_status", "qvm", "GET", "/qvm/saved_searches/vuln_instances/{task_id}/status", min_api_version="27.0"),
    "ListQvmVulnInstanceResultAssetsTool": _spec("ListQvmVulnInstanceResultAssetsTool", "list_qvm_vuln_instance_result_assets", "qvm", "GET", "/qvm/saved_searches/vuln_instances/{task_id}/results/assets", min_api_version="27.0"),
    "ListQvmVulnInstanceResultInstancesTool": _spec("ListQvmVulnInstanceResultInstancesTool", "list_qvm_vuln_instance_result_instances", "qvm", "GET", "/qvm/saved_searches/vuln_instances/{task_id}/results/vuln_instances", min_api_version="27.0"),
    "ListQvmVulnInstanceResultVulnerabilitiesTool": _spec("ListQvmVulnInstanceResultVulnerabilitiesTool", "list_qvm_vuln_instance_result_vulnerabilities", "qvm", "GET", "/qvm/saved_searches/vuln_instances/{task_id}/results/vulnerabilities", min_api_version="27.0"),
    "GetOffenseInvestigationContextTool": _spec(
        "GetOffenseInvestigationContextTool",
        "get_offense_investigation_context",
        "composite",
        "GET",
        "/siem/offenses/{offense_id}",
        optional_endpoints=(
            ("GET", "/siem/offenses/{offense_id}/notes"),
            ("GET", "/siem/source_addresses"),
            ("GET", "/siem/local_destination_addresses"),
            ("GET", "/analytics/rules/{rule_id}"),
            ("GET", "/asset_model/assets"),
        ),
    ),
    "InvestigateOffenseEventsTool": _spec(
        "InvestigateOffenseEventsTool",
        "investigate_offense_events",
        "composite",
        "POST",
        "/ariel/searches",
        min_api_version="27.0",
        side_effect="transient_search_job",
        additional_required_endpoints=(
            ("GET", "/siem/offenses/{offense_id}"),
            ("POST", "/ariel/validators/aql"),
            ("GET", "/ariel/searches/{search_id}"),
            ("GET", "/ariel/searches/{search_id}/metadata"),
            ("GET", "/ariel/searches/{search_id}/results"),
        ),
    ),
}


def get_endpoint_spec(class_name: str) -> Optional[EndpointSpec]:
    """Return endpoint metadata for a tool class name."""
    return ENDPOINT_SPECS.get(class_name)


def compatibility_registry_from_specs(base: Optional[Mapping[str, Dict]] = None) -> Dict[str, Dict]:
    """Build compatibility registry entries, preserving non-spec legacy keys."""
    registry = dict(base or {})
    for class_name, spec in ENDPOINT_SPECS.items():
        registry[class_name] = spec.to_compatibility_entry()
    return registry
