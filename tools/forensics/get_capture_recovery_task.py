"""Get QRadar forensics capture recovery task."""

from qradar_mcp.tools.simple_get_tool import SimpleGetByIdTool


class GetCaptureRecoveryTaskTool(SimpleGetByIdTool):
    tool_name = "get_capture_recovery_task"
    tool_description = "Get a QRadar Incident Forensics capture recovery task by ID."
    endpoint_template = "/forensics/capture/recovery_tasks/{task_id}"
    id_argument = "task_id"
    id_description = "Capture recovery task ID"
