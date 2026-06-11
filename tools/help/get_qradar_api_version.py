"""Get QRadar API version details."""

from qradar_mcp.tools.simple_get_tool import SimpleGetByIdTool


class GetQradarApiVersionTool(SimpleGetByIdTool):
    tool_name = "get_qradar_api_version"
    tool_description = "Get details for a QRadar API version from /help/versions/{version_id}."
    endpoint_template = "/help/versions/{version_id}"
    id_argument = "version_id"
    id_description = "API version ID, for example 27.0"
    id_type = "string"
