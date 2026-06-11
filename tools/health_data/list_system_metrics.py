"""List QRadar system health metrics."""

from qradar_mcp.tools.simple_get_tool import SimpleListTool


class ListSystemMetricsTool(SimpleListTool):
    tool_name = "list_system_metrics"
    tool_description = "List QRadar system health metrics from /health/metrics/system_metrics."
    endpoint = "/health/metrics/system_metrics"
