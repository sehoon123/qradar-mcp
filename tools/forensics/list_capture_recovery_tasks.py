"""List QRadar forensics capture recovery tasks."""

from qradar_mcp.tools.simple_get_tool import SimpleListTool


class ListCaptureRecoveryTasksTool(SimpleListTool):
    tool_name = "list_capture_recovery_tasks"
    tool_description = "List QRadar Incident Forensics capture recovery tasks."
    endpoint = "/forensics/capture/recovery_tasks"
