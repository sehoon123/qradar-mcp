"""Get QRadar forensics capture recovery."""

from qradar_mcp.tools.simple_get_tool import SimpleGetByIdTool


class GetCaptureRecoveryTool(SimpleGetByIdTool):
    tool_name = "get_capture_recovery"
    tool_description = "Get a QRadar Incident Forensics capture recovery by ID."
    endpoint_template = "/forensics/capture/recoveries/{recovery_id}"
    id_argument = "recovery_id"
    id_description = "Capture recovery ID"
