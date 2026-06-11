"""Get QRadar API help resource details."""

from qradar_mcp.tools.simple_get_tool import SimpleGetByIdTool


class GetQradarResourceTool(SimpleGetByIdTool):
    tool_name = "get_qradar_resource"
    tool_description = "Get details for one QRadar API resource from /help/resources/{resource_id}."
    endpoint_template = "/help/resources/{resource_id}"
    id_argument = "resource_id"
    id_description = "Resource ID from /help/resources"
