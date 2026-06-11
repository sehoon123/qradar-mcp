"""Get a QRadar component health metric."""

from qradar_mcp.tools.simple_get_tool import SimpleGetByIdTool


class GetQradarMetricTool(SimpleGetByIdTool):
    tool_name = "get_qradar_metric"
    tool_description = "Get one QRadar component health metric by metric ID."
    endpoint_template = "/health/metrics/qradar_metrics/{metric_id}"
    id_argument = "metric_id"
    id_description = "QRadar component metric ID"
