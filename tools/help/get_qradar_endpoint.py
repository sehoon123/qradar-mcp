"""Get QRadar API endpoint details."""

from qradar_mcp.tools.simple_get_tool import SimpleGetByIdTool


class GetQradarEndpointTool(SimpleGetByIdTool):
    tool_name = "get_qradar_endpoint"
    tool_description = "Get details for one QRadar API endpoint from /help/endpoints/{endpoint_id}."
    endpoint_template = "/help/endpoints/{endpoint_id}"
    id_argument = "endpoint_id"
    id_description = "Endpoint ID from /help/endpoints"
