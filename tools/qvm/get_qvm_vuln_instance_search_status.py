"""Get QVM vulnerability instance search status."""

from qradar_mcp.tools.simple_get_tool import SimpleGetByIdTool


class GetQvmVulnInstanceSearchStatusTool(SimpleGetByIdTool):
    tool_name = "get_qvm_vuln_instance_search_status"
    tool_description = "Get status for a QVM vulnerability instance search task."
    endpoint_template = "/qvm/saved_searches/vuln_instances/{task_id}/status"
    id_argument = "task_id"
    id_description = "QVM vulnerability instance task ID"
    id_type = "string"
