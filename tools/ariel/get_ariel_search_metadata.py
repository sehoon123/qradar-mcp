"""Get Ariel search result metadata."""

from qradar_mcp.tools.simple_get_tool import SimpleGetByIdTool


class GetArielSearchMetadataTool(SimpleGetByIdTool):
    tool_name = "get_ariel_search_metadata"
    tool_description = "Get column metadata for a completed Ariel search."
    endpoint_template = "/ariel/searches/{search_id}/metadata"
    id_argument = "search_id"
    id_description = "Ariel search ID"
    id_type = "string"
