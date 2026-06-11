"""List QVM open services."""

from qradar_mcp.tools.simple_get_tool import SimpleListTool


class ListQvmOpenservicesTool(SimpleListTool):
    tool_name = "list_qvm_openservices"
    tool_description = "List QVM open services with discovered vulnerabilities."
    endpoint = "/qvm/openservices"
