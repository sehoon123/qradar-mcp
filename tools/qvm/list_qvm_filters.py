"""List QVM filters."""

from qradar_mcp.tools.simple_get_tool import SimpleListTool


class ListQvmFiltersTool(SimpleListTool):
    tool_name = "list_qvm_filters"
    tool_description = "List QVM allowable filters."
    endpoint = "/qvm/filters"
