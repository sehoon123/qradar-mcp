"""List QVM saved search groups."""

from qradar_mcp.tools.simple_get_tool import SimpleListTool


class ListQvmSavedSearchGroupsTool(SimpleListTool):
    tool_name = "list_qvm_saved_search_groups"
    tool_description = "List QVM vulnerability saved search groups."
    endpoint = "/qvm/saved_search_groups"
