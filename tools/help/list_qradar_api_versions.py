"""List QRadar API versions."""

from qradar_mcp.tools.simple_get_tool import SimpleListTool


class ListQradarApiVersionsTool(SimpleListTool):
    tool_name = "list_qradar_api_versions"
    tool_description = "List API versions exposed by the connected QRadar console."
    endpoint = "/help/versions"
    default_limit = 100
    max_limit = 1000
