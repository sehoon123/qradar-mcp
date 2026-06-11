"""List QRadar component health metrics."""

from qradar_mcp.tools.simple_get_tool import SimpleListTool


class ListQradarMetricsTool(SimpleListTool):
    tool_name = "list_qradar_metrics"
    tool_description = "List QRadar component health metrics from /health/metrics/qradar_metrics."
    endpoint = "/health/metrics/qradar_metrics"
