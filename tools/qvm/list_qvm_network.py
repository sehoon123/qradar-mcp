"""List QVM vulnerable networks."""

from qradar_mcp.tools.simple_get_tool import SimpleListTool


class ListQvmNetworkTool(SimpleListTool):
    tool_name = "list_qvm_network"
    tool_description = "List QVM networks with discovered vulnerabilities."
    endpoint = "/qvm/network"
