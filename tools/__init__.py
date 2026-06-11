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
MCP Tools Module

This module exports all MCP tool classes. Tools are now registered via the FastMCP
adapter in tools/fastmcp_adapter.py.

To add a new tool:
1. Create a new class that inherits from MCPTool
2. Implement the required methods (name, description, input_schema, execute)
3. Import it in this file
4. The FastMCP adapter will automatically discover and register it
"""

# Import base classes
from .base import MCPTool
from .schema import schema

# Import and register all tools
from .offense.get_offense import GetOffenseTool
from .offense.list_offenses import ListOffensesTool
from .offense.update_offense import UpdateOffenseTool
from .offense.add_offense_note import AddOffenseNoteTool
from .offense.get_offense_notes import GetOffenseNotesTool
from .offense.get_offense_note import GetOffenseNoteTool
from .offense.list_offense_assignable_actors import ListOffenseAssignableActorsTool
from .offense.list_offense_closing_reasons import ListOffenseClosingReasonsTool
from .offense.list_offense_types import ListOffenseTypesTool
from .offense.list_source_addresses import ListSourceAddressesTool
from .offense.get_source_address import GetSourceAddressTool
from .offense.list_local_destination_addresses import ListLocalDestinationAddressesTool
from .offense.get_local_destination_address import GetLocalDestinationAddressTool
from .offense.list_offense_saved_searches import ListOffenseSavedSearchesTool
from .offense.get_offense_saved_search import GetOffenseSavedSearchTool
from .offense.list_offenses_ocsf import ListOffensesOcsfTool

from .ariel.create_ariel_search import CreateArielSearchTool
from .ariel.get_ariel_search_status import GetArielSearchStatusTool
from .ariel.get_ariel_search_results import GetArielSearchResultsTool
from .ariel.delete_ariel_search import DeleteArielSearchTool
from .ariel.list_saved_searches import ListSavedSearchesTool
from .ariel.get_saved_search import GetSavedSearchTool
from .ariel.delete_saved_search import DeleteSavedSearchTool
from .ariel.list_ariel_databases import ListArielDatabasesTool
from .ariel.list_ariel_functions import ListArielFunctionsTool
from .ariel.get_ariel_parser_keywords import GetArielParserKeywordsTool
from .ariel.get_ariel_database_columns import GetArielDatabaseColumnsTool
from .ariel.list_ariel_lookups import ListArielLookupsTool
from .ariel.get_ariel_lookup import GetArielLookupTool
from .ariel.get_ariel_search_metadata import GetArielSearchMetadataTool
from .ariel.cancel_ariel_search import CancelArielSearchTool

from .reference_data.list_reference_sets import ListReferenceSets
from .reference_data.get_reference_set import GetReferenceSetTool
from .reference_data.create_reference_set import CreateReferenceSetTool
from .reference_data.update_reference_set import UpdateReferenceSetTool
from .reference_data.delete_reference_set import DeleteReferenceSetTool
from .reference_data.add_to_reference_set import AddToReferenceSetTool
from .reference_data.remove_from_reference_set import RemoveFromReferenceSetTool
from .reference_data.list_reference_set_entries import ListReferenceSetEntriesTool
from .reference_data.get_reference_set_entry import GetReferenceSetEntryTool
from .reference_data.get_reference_set_dependents import GetReferenceSetDependentsTool
from .reference_data.get_set_bulk_update_task import GetSetBulkUpdateTaskTool
from .reference_data.get_set_bulk_update_task_results import GetSetBulkUpdateTaskResultsTool
from .reference_data.get_set_delete_task import GetSetDeleteTaskTool

from .reference_data.list_reference_maps import ListReferenceMaps
from .reference_data.get_reference_map import GetReferenceMap
from .reference_data.create_reference_map import CreateReferenceMap
from .reference_data.add_to_reference_map import AddToReferenceMap
from .reference_data.delete_reference_map import DeleteReferenceMap
from .reference_data.remove_from_reference_map import RemoveFromReferenceMap

from .reference_data.list_reference_tables import ListReferenceTables
from .reference_data.get_reference_table import GetReferenceTable
from .reference_data.create_reference_table import CreateReferenceTable
from .reference_data.add_to_reference_table import AddToReferenceTable
from .reference_data.delete_reference_table import DeleteReferenceTable
from .reference_data.remove_from_reference_table import RemoveFromReferenceTable

from .asset.list_assets import ListAssetsTool

from .log_source.list_log_sources import ListLogSourcesTool
from .log_source.get_log_source import GetLogSourceTool

from .analytics.list_rules import ListRulesTool
from .analytics.get_rule import GetRuleTool
from .analytics.list_building_blocks import ListBuildingBlocksTool
from .analytics.get_building_block import GetBuildingBlockTool
from .analytics.list_custom_actions import ListCustomActionsTool
from .analytics.get_custom_action import GetCustomActionTool

from .ariel.validate_aql import ValidateAQLTool

from .system.get_system_info import GetSystemInfoTool
from .system.list_servers import ListServersTool

from .config.list_users import ListUsersTool
from .config.list_user_roles import ListUserRolesTool
from .config.list_network_hierarchy import ListNetworkHierarchyTool
from .config.list_domains import ListDomainsTool
from .config.list_regex_properties import ListRegexPropertiesTool
from .config.list_calculated_properties import ListCalculatedPropertiesTool

from .data_classification.list_qid_records import ListQidRecordsTool
from .data_classification.get_qid_record import GetQidRecordTool
from .data_classification.list_dsm_event_mappings import ListDsmEventMappingsTool
from .data_classification.list_low_level_categories import ListLowLevelCategoriesTool
from .data_classification.list_high_level_categories import ListHighLevelCategoriesTool
from .health_data.get_security_data_count import GetSecurityDataCountTool
from .health_data.list_top_offenses import ListTopOffensesTool
from .health_data.list_top_rules import ListTopRulesTool
from .health_data.list_qradar_metrics import ListQradarMetricsTool
from .health_data.get_qradar_metric import GetQradarMetricTool
from .health_data.list_system_metrics import ListSystemMetricsTool
from .health_data.get_system_metric import GetSystemMetricTool
from .help.discover_qradar_endpoints import DiscoverQradarEndpointsTool
from .help.list_qradar_api_versions import ListQradarApiVersionsTool
from .help.get_qradar_api_version import GetQradarApiVersionTool
from .help.get_qradar_endpoint import GetQradarEndpointTool
from .help.list_qradar_resources import ListQradarResourcesTool
from .help.get_qradar_resource import GetQradarResourceTool

from .services.geolocate_ip import GeolocateIpTool
from .services.dns_lookup import DnsLookupTool
from .services.get_dns_result import GetDnsResultTool
from .services.whois_lookup import WhoisLookupTool
from .services.get_whois_result import GetWhoisResultTool

from .asset.list_asset_properties import ListAssetPropertiesTool
from .log_source.list_log_source_types import ListLogSourceTypesTool
from .forensics.list_cases import ListCasesTool
from .forensics.get_case import GetCaseTool
from .forensics.list_capture_recoveries import ListCaptureRecoveriesTool
from .forensics.get_capture_recovery import GetCaptureRecoveryTool
from .forensics.list_capture_recovery_tasks import ListCaptureRecoveryTasksTool
from .forensics.get_capture_recovery_task import GetCaptureRecoveryTaskTool
from .forensics.get_case_create_task import GetCaseCreateTaskTool
from .qvm.list_vulnerabilities import ListVulnerabilitiesTool
from .qvm.list_qvm_assets import ListQvmAssetsTool
from .qvm.list_qvm_filters import ListQvmFiltersTool
from .qvm.list_qvm_network import ListQvmNetworkTool
from .qvm.list_qvm_openservices import ListQvmOpenservicesTool
from .qvm.list_qvm_saved_search_groups import ListQvmSavedSearchGroupsTool
from .qvm.get_qvm_saved_search_group import GetQvmSavedSearchGroupTool
from .qvm.list_qvm_saved_searches import ListQvmSavedSearchesTool
from .qvm.get_qvm_saved_search import GetQvmSavedSearchTool
from .qvm.create_qvm_vuln_instance_search import CreateQvmVulnInstanceSearchTool
from .qvm.get_qvm_vuln_instance_search_status import GetQvmVulnInstanceSearchStatusTool
from .qvm.list_qvm_vuln_instance_result_assets import ListQvmVulnInstanceResultAssetsTool
from .qvm.list_qvm_vuln_instance_result_instances import ListQvmVulnInstanceResultInstancesTool
from .qvm.list_qvm_vuln_instance_result_vulnerabilities import ListQvmVulnInstanceResultVulnerabilitiesTool
from .composite.get_offense_investigation_context import GetOffenseInvestigationContextTool
from .composite.investigate_offense_events import InvestigateOffenseEventsTool



# Export public API
__all__ = [
    'MCPTool',
    'schema',
    # Tool classes
    'GetOffenseTool',
    'ListOffensesTool',
    'UpdateOffenseTool',
    'AddOffenseNoteTool',
    'GetOffenseNotesTool',
    'GetOffenseNoteTool',
    'ListOffenseAssignableActorsTool',
    'ListOffenseClosingReasonsTool',
    'ListOffenseTypesTool',
    'ListSourceAddressesTool',
    'GetSourceAddressTool',
    'ListLocalDestinationAddressesTool',
    'GetLocalDestinationAddressTool',
    'ListOffenseSavedSearchesTool',
    'GetOffenseSavedSearchTool',
    'ListOffensesOcsfTool',
    'CreateArielSearchTool',
    'GetArielSearchStatusTool',
    'GetArielSearchResultsTool',
    'DeleteArielSearchTool',
    'ValidateAQLTool',
    'ListSavedSearchesTool',
    'GetSavedSearchTool',
    'DeleteSavedSearchTool',
    'ListArielDatabasesTool',
    'ListArielFunctionsTool',
    'GetArielParserKeywordsTool',
    'GetArielDatabaseColumnsTool',
    'ListArielLookupsTool',
    'GetArielLookupTool',
    'GetArielSearchMetadataTool',
    'CancelArielSearchTool',
    'ListReferenceSets',
    'GetReferenceSetTool',
    'CreateReferenceSetTool',
    'UpdateReferenceSetTool',
    'DeleteReferenceSetTool',
    'AddToReferenceSetTool',
    'RemoveFromReferenceSetTool',
    'ListReferenceSetEntriesTool',
    'GetReferenceSetEntryTool',
    'GetReferenceSetDependentsTool',
    'GetSetBulkUpdateTaskTool',
    'GetSetBulkUpdateTaskResultsTool',
    'GetSetDeleteTaskTool',
    'ListReferenceMaps',
    'GetReferenceMap',
    'CreateReferenceMap',
    'AddToReferenceMap',
    'DeleteReferenceMap',
    'RemoveFromReferenceMap',
    'ListReferenceTables',
    'GetReferenceTable',
    'CreateReferenceTable',
    'AddToReferenceTable',
    'DeleteReferenceTable',
    'RemoveFromReferenceTable',
    'ListAssetsTool',
    'ListLogSourcesTool',
    'GetLogSourceTool',
    'ListRulesTool',
    'GetRuleTool',
    'ListBuildingBlocksTool',
    'GetBuildingBlockTool',
    'ListCustomActionsTool',
    'GetCustomActionTool',
    'GetSystemInfoTool',
    'ListServersTool',
    'ListUsersTool',
    'ListUserRolesTool',
    'ListNetworkHierarchyTool',
    'ListDomainsTool',
    'ListRegexPropertiesTool',
    'ListCalculatedPropertiesTool',
    'ListQidRecordsTool',
    'GetQidRecordTool',
    'ListDsmEventMappingsTool',
    'ListLowLevelCategoriesTool',
    'ListHighLevelCategoriesTool',
    'GetSecurityDataCountTool',
    'ListTopOffensesTool',
    'ListTopRulesTool',
    'ListQradarMetricsTool',
    'GetQradarMetricTool',
    'ListSystemMetricsTool',
    'GetSystemMetricTool',
    'DiscoverQradarEndpointsTool',
    'ListQradarApiVersionsTool',
    'GetQradarApiVersionTool',
    'GetQradarEndpointTool',
    'ListQradarResourcesTool',
    'GetQradarResourceTool',
    'GeolocateIpTool',
    'DnsLookupTool',
    'GetDnsResultTool',
    'WhoisLookupTool',
    'GetWhoisResultTool',
    'ListAssetPropertiesTool',
    'ListLogSourceTypesTool',
    'ListCasesTool',
    'GetCaseTool',
    'ListCaptureRecoveriesTool',
    'GetCaptureRecoveryTool',
    'ListCaptureRecoveryTasksTool',
    'GetCaptureRecoveryTaskTool',
    'GetCaseCreateTaskTool',
    'ListVulnerabilitiesTool',
    'ListQvmAssetsTool',
    'ListQvmFiltersTool',
    'ListQvmNetworkTool',
    'ListQvmOpenservicesTool',
    'ListQvmSavedSearchGroupsTool',
    'GetQvmSavedSearchGroupTool',
    'ListQvmSavedSearchesTool',
    'GetQvmSavedSearchTool',
    'CreateQvmVulnInstanceSearchTool',
    'GetQvmVulnInstanceSearchStatusTool',
    'ListQvmVulnInstanceResultAssetsTool',
    'ListQvmVulnInstanceResultInstancesTool',
    'ListQvmVulnInstanceResultVulnerabilitiesTool',
    'GetOffenseInvestigationContextTool',
    'InvestigateOffenseEventsTool',
]
