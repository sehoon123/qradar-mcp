"""List QVM saved searches."""

from qradar_mcp.tools.simple_get_tool import SimpleListTool


class ListQvmSavedSearchesTool(SimpleListTool):
    tool_name = "list_qvm_saved_searches"
    tool_description = "List QVM vulnerability instance saved searches."
    endpoint = "/qvm/saved_searches"
