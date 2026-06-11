"""List QRadar API help resources."""

from qradar_mcp.tools.simple_get_tool import SimpleListTool


class ListQradarResourcesTool(SimpleListTool):
    tool_name = "list_qradar_resources"
    tool_description = "List QRadar API resources from /help/resources."
    endpoint = "/help/resources"
    default_limit = 100
    max_limit = 10000
