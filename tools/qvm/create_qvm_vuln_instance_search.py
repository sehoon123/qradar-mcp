"""Create a QVM vulnerability instance search task."""

from qradar_mcp.tools.simple_get_tool import SimpleGetByIdTool


class CreateQvmVulnInstanceSearchTool(SimpleGetByIdTool):
    tool_name = "create_qvm_vuln_instance_search"
    tool_description = (
        "Start a transient QVM vulnerability instance search from a saved search. "
        "The QRadar API exposes this workflow as a GET endpoint."
    )
    endpoint_template = "/qvm/saved_searches/{saved_search_id}/vuln_instances"
    id_argument = "saved_search_id"
    id_description = "QVM saved search ID"
