"""List QRadar forensics capture recoveries."""

from qradar_mcp.tools.simple_get_tool import SimpleListTool


class ListCaptureRecoveriesTool(SimpleListTool):
    tool_name = "list_capture_recoveries"
    tool_description = "List QRadar Incident Forensics capture recoveries."
    endpoint = "/forensics/capture/recoveries"
