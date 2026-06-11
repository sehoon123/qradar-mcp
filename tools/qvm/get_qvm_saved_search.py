"""Get a QVM saved search."""

from qradar_mcp.tools.simple_get_tool import SimpleGetByIdTool


class GetQvmSavedSearchTool(SimpleGetByIdTool):
    tool_name = "get_qvm_saved_search"
    tool_description = "Get one QVM vulnerability instance saved search."
    endpoint_template = "/qvm/saved_searches/{saved_search_id}"
    id_argument = "saved_search_id"
    id_description = "QVM saved search ID"
