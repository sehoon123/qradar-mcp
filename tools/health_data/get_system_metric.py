"""Get a QRadar system health metric."""

from qradar_mcp.tools.simple_get_tool import SimpleGetByIdTool


class GetSystemMetricTool(SimpleGetByIdTool):
    tool_name = "get_system_metric"
    tool_description = "Get one QRadar system health metric by metric ID."
    endpoint_template = "/health/metrics/system_metrics/{metric_id}"
    id_argument = "metric_id"
    id_description = "System metric ID"
