"""Get a QVM saved search group."""

from qradar_mcp.tools.simple_get_tool import SimpleGetByIdTool


class GetQvmSavedSearchGroupTool(SimpleGetByIdTool):
    tool_name = "get_qvm_saved_search_group"
    tool_description = "Get one QVM vulnerability saved search group."
    endpoint_template = "/qvm/saved_search_groups/{group_id}"
    id_argument = "group_id"
    id_description = "QVM saved search group ID"
